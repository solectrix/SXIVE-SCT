#!/usr/bin/python
"""
    dasTool - (d)irect (a)ccess to (s)ensor Tool
    Copyright: 2024, Solectrix GmbH
"""

import os
import sys
import re
import json
import time
import platform
import fnmatch
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
try:
    from ttkthemes import ThemedStyle
    USE_THEMES = True
except ImportError:
    USE_THEMES = False
from ui import Icons
from ui import TreeviewToolTip
from socket_io import SocketIO, SocketPopup
from sxl import Sxl, SxlRoot

class DasTool(tk.Tk):
    """TKinter representation of DasTool."""
    name = os.path.splitext(os.path.split(__file__)[1])[0].replace("_", " ")
    version = "0.1"
    config_file = os.path.splitext(os.path.split(__file__)[1])[0] + ".json"

    def __init__(self) -> None:
        super().__init__()
        self.tree = None            # main treeview widget
        self.icons = Icons()        # icon class
        self.gui = dict()           # collection of gui widgets
        self.menu = dict()          # menu structure
        self.sock = SocketIO()      # socket
        self.sxl = SxlRoot()        # SXL definitions
        self.sxl_file = None        # SXL file path
        self.sxl_obj_dict = None    # SXL object -> treeview node dict
        self.sxl_node_dict = None   # treeview node -> SXL object dict
        self.cfg_menu = dict(show_filter=tk.StringVar(master=self, value="1"),
                             show_reset_column=tk.StringVar(master=self, value="0"))
        self.cfg_filter_types = [i.capitalize() for i in [Sxl.Sig, Sxl.Reg, "tag"]]
        self.cfg_filter = dict(type=tk.StringVar(master=self, value=self.cfg_filter_types[0]),
                               str=tk.StringVar(master=self, value=""))
        self.ui_theme = None
        if USE_THEMES:
            self.ui_theme = ThemedStyle(self)
            self.ui_theme_sel = tk.StringVar(master=self, 
                              value="vista" if platform.system() == "Windows" else "alt")
            self.ui_themes = ["arc", "clam", "classic", "clearlooks", "default",
                             "elegance", "equilux", "keramic", "plastic", 
                             "scidblue", "scidgreen", "scidgrey", "scidmint", 
                             "scidpink", "scidpurple", "scidsand", "ubuntu",
                             "vista", "winnative", "winxpblue", "xpnative", "yaru"]
        self.colors = dict(
            bright={Sxl.Block:"#c0f0c0", Sxl.Reg:"#c0c0f0", Sxl.Sig:"#f0f0c0", 
                    Sxl.Enum:"#f0c080", Sxl.Flag:"#e0a0d0"},
            dark  ={Sxl.Block:"#336633", Sxl.Reg:"#444466", Sxl.Sig:"#666622", 
                    Sxl.Enum:"#664433", Sxl.Flag:"#664455"})
        # initialize tool
        self.ui_create()
        self.ui_init()
        self.ui_load_config()
        self.ui_title_update()
        self.request_busy = False
        self.tooltip = TreeviewToolTip(das_tool=self, tree=self.tree, delay=1000)
        self.bind_all(sequence="<<socket_connected>>",func=self.socket_event_connected)
        self.about_win = None

    # menu actions
    def menu_create(self):
        """Create menu structure"""
        frame = ttk.Frame(master=self)
        menubar = tk.Menu(master=frame)
        # add File menu
        file_menu = tk.Menu(master=menubar, tearoff=False)
        file_menu.add_command(
            label="Open", accelerator="Ctrl+O", command=self.menu_open,
            )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        # add Target menu
        target_menu = tk.Menu(master=menubar, tearoff=False)
        target_menu.add_command(
            label="Open Target..", command=self.socket_connect)
        target_menu.add_command(
            label="Close Target..", command=self.socket_disconnect, state=tk.DISABLED)
        # add View menu
        view_menu = tk.Menu(master=menubar, tearoff=False)
        view_menu.add_command(
            label="Expand Level1", command=lambda:self.menu_expand_view(1))
        view_menu.add_command(
            label="Expand Level2", command=lambda:self.menu_expand_view(2))
        view_menu.add_command(
            label="Expand Level3", command=lambda:self.menu_expand_view(3))
        view_menu.add_command(
            label="Collapse All", command=self.menu_collapse_view)
        # theme selector
        if self.ui_theme:
            view_menu.add_separator()
            themes_sub = tk.Menu(master=view_menu, tearoff=False)
            themes = self.ui_theme.get_themes()
            for theme in sorted(self.ui_themes):
                if theme in themes:
                    themes_sub.add_radiobutton(label=theme, variable=self.ui_theme_sel, value=theme, command=self.menu_change_theme)
            view_menu.add_cascade(label="Theme", menu=themes_sub)
        # options
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Filter", variable=self.cfg_menu["show_filter"], command=self.toggle_menu_show_filter)
        view_menu.add_checkbutton(label="Show Reset Column", variable=self.cfg_menu["show_reset_column"], command=self.toggle_menu_show_reset_column)
        # add Help menu
        help_menu = tk.Menu(master=menubar, tearoff=False)
        help_menu.add_command(
            label="About..", command=self.menu_about)
        # compile menu structure
        menubar.add_cascade(menu=file_menu, label="File")
        menubar.add_cascade(menu=target_menu, label="Target")
        menubar.add_cascade(menu=view_menu, label="View")
        menubar.add_cascade(menu=help_menu, label="Help")
        self.config(menu=menubar)
        self.menu["."] = menubar
        self.menu["File"] = file_menu
        self.menu["Target"] = target_menu
        self.menu["View"] = view_menu
        self.menu["Help"] = help_menu
        # bind events
        self.bind_all(sequence="<Control-o>", func=self.menu_open)
        self.bind_all(sequence="<F1>", func=self.treeview_update_node)
        self.bind_all(sequence="<F2>", func=self.treeview_modify_node)
        self.bind_all(sequence="<Double-1>", func=self.treeview_modify_node)

    def menu_open(self, event=None):
        """File selection request"""
        initial_directory = "."
        if self.sxl_file and os.path.isfile(path=self.sxl_file):
            initial_directory = os.path.split(p=self.sxl_file)[0]
        
        result = filedialog.askopenfilename(title="Open SXL file...",
                                            initialdir=initial_directory,
                                            filetypes=[("SXL Files", "*.sxl")])
        if not os.path.isfile(path=result):
            # no file selected, aborted
            return
        if os.path.splitext(p=result)[1] != ".sxl":
            # no SXL file selected, aborting
            messagebox.showerror("Error", result + "\nFile is not a proper SXL format!")
            return
        # initialize and load SXL file
        self.ui_init()

        ret = self.sxl.load(file=result)
        if ret:
            messagebox.showerror(title="Error", message=result + "\n" + ret)
            return
        self.sxl_file = result
        self.treeview_gen()
        self.ui_title_update()

    def menu_about(self):
        """Open about menu."""
        if self.about_win:
            return
        about_text1 = f"{self.name} v{self.version}"
        about_text2 = "SXIVE Sensor Configuration Tool\n\n"\
                     "Control Summary:\n"\
                     "    [F1] - Read from target\n"\
                     "    [F2] - Modify target values\n\n"\
                     "\u00A9 Solectrix GmbH, 2024"
        # create toolbox window
        self.about_win = tk.Toplevel()
        self.about_win.title(string="About")
        self.about_win.attributes("-topmost",1)
        if platform.system() == "Windows":
            # use for window:
            self.about_win.attributes("-toolwindow", True)
        else:
            # use for linux/mac:
            self.about_win.resizable(width=False, height=False)
        # place window near mouse pointer
        x, y = self.winfo_pointerxy()
        self.about_win.geometry(newGeometry=f"+{x}+{y}")
        self.about_win.protocol(name="WM_DELETE_WINDOW", func=self.menu_about_close)
        top = ttk.Frame(master=self.about_win)
        top.pack()
        # create toolbox widgets
        f1 = ttk.Frame(master=top)
        ttk.Label(master=f1, image=self.icons.iconSX96)\
            .pack(side=tk.LEFT, padx=5, expand=True, fill=tk.Y)
        aboutField = ttk.Frame(f1, relief="groove", borderwidth=2)
        ttk.Label(master=aboutField, text=about_text1, font=("Arial", 14))\
            .pack(padx=5, pady=2)
        ttk.Label(master=aboutField, text=about_text2)\
            .pack(padx=5, pady=2)
        aboutField.pack(side=tk.LEFT, padx=5, pady=2)
        f2 = ttk.Frame(master=top)
        ttk.Button(master=f2, text="Ok", width=16, command=self.menu_about_close)\
            .pack(side=tk.TOP, padx=5, pady=2)
        f1.pack(side=tk.TOP, padx=4, pady=8)
        f2.pack(side=tk.TOP, padx=4, pady=8)

    def menu_about_close(self):
        """Close about menu."""
        self.about_win.destroy()
        self.about_win = None

    def menu_expand_view(self, level=1):
        """Expand treeview hierarchies according to level."""
        for l1item in self.tree.get_children():
            self.tree.item(item=l1item, open=True)
            for l2item in self.tree.get_children(item=l1item):
                if level >= 2:
                    self.tree.item(item=l2item, open=True)
                    for l3item in self.tree.get_children(item=l2item):
                        if level >= 3:
                            self.tree.item(item=l3item, open=True)

    def menu_collapse_view(self):
        """Collapse all expanded views."""
        for l1item in self.tree.get_children():
            self.tree.item(item=l1item, open=False)
            for l2item in self.tree.get_children(item=l1item):
                self.tree.item(item=l2item, open=False)
                for l3item in self.tree.get_children(item=l2item):
                    self.tree.item(item=l3item, open=False)

    def toggle_menu_show_filter(self):
        """Shows or hides the filter accordingly."""
        if self.cfg_menu["show_filter"].get() == "1":
            # pack_forget lower frame
            self.gui["grid"].pack_forget()
            # pack again in proper order: filter + treeview grid
            self.gui["filter"].pack(side=tk.TOP)
            self.gui["grid"].pack(expand=1, fill="both")
        else:
            self.gui["filter"].pack_forget()

    def toggle_menu_show_reset_column(self):
        """Shows or hides reset column."""
        if self.cfg_menu["show_reset_column"].get() == "1":
            # when being enabled
            self.tree.column(column="reset", stretch=1, width=100)
            # visualize all available reset values in reset column
            for node in self.tree.tag_has(tagname=Sxl.Sig):
                sxl_obj = self.sxl_obj_dict[node]
                sig_reset = sxl_obj.get_attr("reset")
                if sig_reset != "":
                    self.tree.set(item=node, column="reset", value=sig_reset)
                    self.treeview_decode_signal(sig=sxl_obj, column="reset", sig_value=int(sig_reset, 0))
        else:
            # when being disabled
            self.tree.column(column="reset", stretch=0, width=0)
            # clear all available reset values
            for node in self.tree.tag_has(tagname=Sxl.Sig):
                self.tree.set(item=node, column="reset", value="")

    def menu_change_theme(self):
        """Shows the menu to change the theme."""
        if self.ui_theme:
            self.ui_theme.set_theme(theme_name=self.ui_theme_sel.get())
            palette = "dark" if self.ui_theme.current_theme in ["equilux","black"] else "bright"
            for i in self.colors[palette]:
                self.tree.tag_configure(tagname=i, background=self.colors[palette][i])
        else:
            palette = "dark"
            for i in self.colors[palette]:
                self.tree.tag_configure(tagname=i, background=self.colors[palette][i])

    ##################### I/O functions #####################

    def socket_connect(self):
        """Actions on menu->connect-target event"""
        # try to connect target via underlying socket communication layer
        SocketPopup(tk_root=self, socket=self.sock)
        # update ui title
        self.ui_title_update()

    def socket_disconnect(self):
        """Actions on menu->disconnect-target event"""
        # disconnect from target
        self.sock.disconnect()
        # disable/enable menu items
        self.menu["Target"].entryconfig("Open Target..", state=tk.NORMAL)
        self.menu["Target"].entryconfig("Close Target..", state=tk.DISABLED)
        # remap treeview addresses if necessary
        if self.sock.device_addr_int >= 0:
            self.treeview_gen()
        # update ui title
        self.ui_title_update()

    def socket_event_connected(self, event=None):
        """Callback function to be executed when <<socket_connected>> event was raised"""
        # disable/enable menu items
        self.menu["Target"].entryconfig("Open Target..", state=tk.DISABLED)
        self.menu["Target"].entryconfig("Close Target..", state=tk.NORMAL)
        # remap treeview addresses if necessary
        if self.sock.connected and self.sock.device_addr_int >= 0:
            self.treeview_gen()
        # update ui title
        self.ui_title_update()

    def socket_event_connection_lost(self, event=None):
        """Show error that the connection is lost."""
        self.socket_disconnect()
        messagebox.showerror(title="Error", message="Connection to server was lost!")

    ##################### Filter functions #####################
    def filter_update(self, event=None):
        """Actions on Filter modification events"""
        # re-generate treeview content to apply filter
        # filtering is considered there
        self.treeview_gen()
        # expand all elements of <filter type> for visualization
        if self.cfg_filter["str"].get() != "":
            # expand level 1 by default
            self.menu_expand_view(level=1)
            filter_type = self.cfg_filter["type"].get().lower()
            open_list = list()
            if filter_type == Sxl.Reg:
                # registers
                for reg in self.sxl.get_objects_of_type(type=Sxl.Reg):
                    item = reg.parent
                    if item not in open_list:
                        open_list.append(item)
            elif filter_type == Sxl.Sig:
                # signals
                for sig in self.sxl.get_objects_of_type(type=Sxl.Sig):
                    item = sig.parent
                    if item not in open_list:
                        open_list.append(item)
            # open all relevant items
            for item in open_list:
                if item in self.sxl_node_dict:
                    self.tree.item(item=self.sxl_node_dict[item], open=True)
            # remove all elements containing no subelement
            if filter_type == Sxl.Reg or filter_type == Sxl.Sig:
                for item in self.tree.tag_has(tagname="register"):
                    if len(self.tree.get_children(item=item)) == 0:
                        self.tree.delete(item)
            # remove empty blocks
            for block in self.tree.get_children():
                if len(self.tree.get_children(item=block)) == 0:
                    self.tree.delete(block)

    def filter_clear(self):
        """Actions on Filter "Clear" button event"""
        # reset filter entry string
        self.cfg_filter["str"].set(value="")
        # update filter
        self.filter_update()
        # collapse treeview content
        self.menu_collapse_view()

    # treeview actions
    def treeview_add(self, node: str, item, addr: int, tag_ok: bool=False):
        """Recursive creation of SXL hierarchy in treeview widget"""
        node_copy = None
        filter_type = self.cfg_filter["type"].get().lower()
        filter_str = self.cfg_filter["str"].get().lower()
        ok = True
        if item.type == Sxl.Block:
            # apply tag filter
            if filter_type == "tag" and filter_str != "":
                tag_ok |= True in [fnmatch.fnmatchcase(name=i.lower(),pat=filter_str) for i in item.get_attr("tags").split(" ")]
            node_copy = self.tree.insert(parent="", index=tk.END, text=item.name, values="")
            if addr < 0:
                # headless SXL Block, no start address defined
                self.tree.set(item=node_copy, column="info", value="N/A")
                addr = 0
            else:
                self.tree.set(item=node_copy, column="info", value=f"0x{addr:08X}")
            self.tree.item(item=node_copy, tags=Sxl.Block)
        elif item.type == Sxl.Reg:
            # apply register & tag filter
            if not tag_ok:
                if filter_type == Sxl.Reg and filter_str != "":
                    ok = fnmatch.fnmatchcase(name=item.name.lower(),pat=f"*{filter_str}*")
                elif filter_type == "tag" and filter_str != "":
                    ok = True in [fnmatch.fnmatchcase(name=i.lower(),pat=filter_str) for i in item.get_attr("tags").split(" ")]
                    tag_ok |= ok
            if ok or tag_ok:
                node_copy = self.tree.insert(parent=node, index=tk.END, text=item.name, values="")
                addr += int(item.get_attr("addr"), 0)
                self.tree.set(item=node_copy, column="info", value=f"0x{addr:08X}")
                self.tree.item(item=node_copy, tags=Sxl.Reg)
        elif item.type == Sxl.Sig:
            # apply signal & tag filter
            if not tag_ok:
                if filter_type == Sxl.Sig and filter_str != "":
                    ok = fnmatch.fnmatchcase(name=item.name.lower(), pat=f"*{filter_str}*")
                elif filter_type == "tag" and filter_str != "":
                    ok = True in [fnmatch.fnmatchcase(name=i.lower(), pat=filter_str) for i in item.get_attr("tags").split(" ")]
                    tag_ok |= ok
                elif filter_type == Sxl.Reg and filter_str != "" and \
                    item.parent.type == Sxl.Block:
                    ok = False
            if ok or tag_ok:
                if item.get_attr("mode").lower() == "ro":
                    image=self.icons.iconModeRO
                elif item.get_attr("mode").lower() == "wo":
                    image=self.icons.iconModeWO
                elif item.get_attr("mode").lower() == "t":
                    image=self.icons.iconModeT
                else:
                    image=self.icons.iconModeRW
                node_copy = self.tree.insert(parent=node, index=tk.END, text=item.name, values="", image=image)
                if item.parent.type == Sxl.Block and item.has_attr("addr"):
                    addr += int(item.get_attr("addr"), 0)
                    pos = f"0x{addr:08X} [{item.get_attr('pos')}]"
                else:
                    pos = item.get_attr("pos")
                self.tree.set(item=node_copy, column="info", value=pos)
                self.tree.item(item=node_copy, tags=Sxl.Sig)
        elif item.type == Sxl.Enum:
            node_copy = self.tree.insert(parent=node, index=tk.END, text=item.name, values="")
            value = item.get_attr("value")
            self.tree.set(item=node_copy, column="info", value=value)
            self.tree.item(item=node_copy, tags=Sxl.Enum)
        elif item.type == Sxl.Flag:
            node_copy = self.tree.insert(parent=node, index=tk.END, text=item.name, values="")
            pos = item.get_attr("pos")
            self.tree.set(item=node_copy, column="info", value=pos)
            self.tree.item(item=node_copy, tags=Sxl.Flag)
        else:
            # unknown item
            return
        # node dict of items
        self.sxl_obj_dict[node_copy] = item
        # item dict of nodes
        self.sxl_node_dict[item] = node_copy
        # handle all children
        if ok or tag_ok:
            for item_ in item.objects:
                self.treeview_add(node=node_copy, item=item_, addr=addr, tag_ok=tag_ok)

    def treeview_gen(self):
        """Generate a treeview."""
        if not self.tree:
            return
        # clear treeview widget
        if self.tree:
            self.tree.delete(*self.tree.get_children())
        # clean-up, hide dump column
        self.tree.column(column="dump", stretch=0, width=0)
        # parse SXL hierarchy
        top = self.sxl.findIconTop()
        if top is None:
            # no toplevel interconnect tree found, just iterate through all blocks
            for block in self.sxl.get_objects_of_type(type=Sxl.Block):
                self.treeview_add(node=None, item=block, addr=-1, tag_ok=False)
        else:
            # iterate through SXL hierarchy
            for blockItem in self.sxl.listIconSlaves(top=top, addr_base=0, sizeBase=0x100000000, 
                                                     mask_base=0xFFFFFFFF, loc="top", block_list=[]):
                block, block_addr, _, _ = blockItem
                if self.sock.connected and self.sock.device_addr_int >= 0:
                    block_addr = (self.sock.device_addr_int << 24) | (block_addr & 0xFFFFFF)
                self.treeview_add(node=None, item=block, addr=block_addr, tag_ok=False)
        # update reset column
        self.toggle_menu_show_reset_column()

    def treeview_update_node(self, event=None):
        """Update treeview contents."""
        if not self.tree or not self.sock.connected:
            return
        # get selected treeview node
        node = self.tree.selection()
        if not node:
            return
        # get selected SXL object
        sxl_obj = self.sxl_obj_dict[node[0]]
        # SXL object type depending actions
        if sxl_obj.type == Sxl.Block:
            # Block
            for child in sxl_obj.objects:
                if child.type == Sxl.Reg:
                    # for all registers of a Block
                    self.treeview_refresh(sxl_obj=child)
                elif child.type == Sxl.Sig:
                    # for all signals of a Block
                    self.treeview_refresh(sxl_obj=child, block_sig=True)
        elif sxl_obj.type == Sxl.Reg:
            # Register
            self.treeview_refresh(sxl_obj=sxl_obj)
        elif sxl_obj.type == Sxl.Sig and sxl_obj.parent.type == Sxl.Reg:
            # Signal of a register
            self.treeview_refresh(sxl_obj=sxl_obj.parent)
        elif sxl_obj.type == Sxl.Sig and sxl_obj.parent.type == Sxl.Block:
            # Signal of a block
            self.treeview_refresh(sxl_obj=sxl_obj, block_sig=True)
        elif (sxl_obj.type == Sxl.Enum or sxl_obj.type == Sxl.Flag) and \
              sxl_obj.parent.parent.type == Sxl.Block:
            # Enum/Flag of a block signal
            self.treeview_refresh(sxl_obj=sxl_obj.parent, block_sig=True)
        elif (sxl_obj.type == Sxl.Enum or sxl_obj.type == Sxl.Flag) and \
              sxl_obj.parent.parent.type == Sxl.Reg:
            # Enum/Flag of a register signal
            self.treeview_refresh(sxl_obj=sxl_obj.parent.parent)

    def treeview_modify_node(self, event=None):
        """Modify treeview contents."""
        # leave here when not target connected or update poll already in progress
        if not self.sock.connected or self.request_busy:
            return
        # leave here when event was triggert under wrong conditions
        if event.type._name_ == "ButtonPress" and event.widget != self.tree:
            return
        # get selected treeview node
        node = self.tree.selection()
        if not node:
            return
        if isinstance(node, tuple):
            node = node[0]
        # set request busy flag to avoid double call
        self.request_busy = True
        sxl_obj = self.sxl_obj_dict[node]
        if sxl_obj.type == Sxl.Sig:
            sig_mode = sxl_obj.get_attr("mode")
            sig_pos  = sxl_obj.get_attr("pos").split(":")
            sig_msb = int(sig_pos[0],0)
            sig_lsb = sig_msb if len(sig_pos) == 1 else int(sig_pos[1], 0)
            sig_max = 0 if sig_lsb > sig_msb else (1 << (1+sig_msb-sig_lsb)) - 1
            sig_data = self.tree.set(item=node, column="data").split(" ")[0]
            if len(sig_pos) == 1:
                if sig_mode in ["rw", ""]:
                    if sig_data == "0":
                        self.treeview_modify_signal(sxl_obj=sxl_obj, value=1)
                    elif sig_data == "1":
                        self.treeview_modify_signal(sxl_obj=sxl_obj, value=0)
                elif sig_mode == "wo":
                    # get value from Tk toolbox and update here
                    new = self.ui_value_toolbox(sxl_obj=sxl_obj, new=sig_data, max=sig_max)
                    if new is not None:
                        self.treeview_modify_signal(sxl_obj=sxl_obj, value=int(new))
                elif sig_mode == "t":
                    self.treeview_modify_signal(sxl_obj=sxl_obj)
            else:
                if sig_mode in ["rw", "wo", ""]:
                    # get value from Tk toolbox and update here
                    new = self.ui_value_toolbox(sxl_obj=sxl_obj, new=sig_data, max=sig_max)
                    if new is not None:
                        self.treeview_modify_signal(sxl_obj=sxl_obj, value=int(new))
        elif sxl_obj.type == Sxl.Enum:
            sig_mode = sxl_obj.parent.get_attr("mode")
            if sig_mode in ["rw", "wo", ""]:
                value = int(self.tree.set(node, "info"))
                self.treeview_modify_signal(sxl_obj=sxl_obj.parent, value=value)
        elif sxl_obj.type == Sxl.Flag:
            sig_mode = sxl_obj.parent.get_attr("mode")
            if sig_mode in ["rw", "wo", ""]:
                pos = int(self.tree.set(node, "info"))
                sig_data = self.tree.set(item=self.sxl_node_dict[sxl_obj.parent], 
                                         column="data").split(" ")[0]
                value = int(sig_data) ^ (1 << pos)
                self.treeview_modify_signal(sxl_obj=sxl_obj.parent, value=value)
        # Update done, reset busy flag
        self.request_busy = False

    def treeview_modify_signal(self, sxl_obj, value=None):
        """Modify signal."""
        if sxl_obj.type == Sxl.Sig:
            # Signals only supported for registers
            reg_obj = sxl_obj.parent
            block_sig = reg_obj.type == Sxl.Block
            sig_pos = sxl_obj.get_attr("pos").split(":")
            sig_msb = int(sig_pos[0],0)
            sig_lsb = sig_msb if len(sig_pos) == 1 else int(sig_pos[1], 0)
            sig_mode = sxl_obj.get_attr("mode")
            if block_sig:
                reg_addr = int(self.tree.set(self.sxl_node_dict[sxl_obj], "info").split(" ")[0], 0)
                reg_size = sig_msb//8 + 1
                if reg_size == 3:
                    reg_size += 1
            else:
                reg_addr = int(self.tree.set(self.sxl_node_dict[reg_obj], "info").split(" ")[0], 0)
                reg_type = reg_obj.get_attr("type")
                reg_size = 1 if reg_type == "byte" else 2 if reg_type == "word" else 4

            if sig_mode == "t":
                # send trigger
                w_mask = (1 << (sig_msb+1)) - (1 << sig_lsb)
                status, r_data = self.sock.modify_bytes(reg_addr, w_mask, w_mask, reg_size)
            else:
                # toggle single bit flags
                w_mask = (1 << (sig_msb+1)) - (1 << sig_lsb)
                w_data = value << sig_lsb
                status, r_data = self.sock.modify_bytes(reg_addr, w_data, w_mask, reg_size)
            # update children (signals)
            if block_sig:
                self.treeview_decode_signal(sig=sxl_obj, column="data", reg_value=r_data, status=status)
            else:
                reg_obj = sxl_obj.parent
                self.tree.set(self.sxl_node_dict[reg_obj], column="data", value="N/A" if not status else f"0x{r_data:0{reg_size<<1}X}")
                for child in reg_obj.get_objects_of_type(Sxl.Sig):
                    self.treeview_decode_signal(sig=child, column="data", reg_value=r_data, status=status)

    def treeview_refresh(self, sxl_obj, block_sig: bool = False):
        """Refresh the treeview."""
        node = self.sxl_node_dict[sxl_obj]
        if node is None:
            # filter suppression active, node does not exist
            return
        # get combined address from info column and convert to integer
        reg_addr = int(self.tree.set(item=node, column="info").split(" ")[0], 0)
        if block_sig:
            # block signal type
            # check consistency of addr and bit range
            sig_pos = sxl_obj.get_attr("pos").split(":")
            sig_msb = int(sig_pos[0], 0)
            bytes = sig_msb//8 + 1
            # correct read size for 3 bytes signals
            if bytes == 3:
                bytes += 1
            # simple sanity check, abort when byte/word/dword does not
            # align into memory granularity
            if (bytes == 4 and reg_addr & 3 != 0) or \
               (bytes == 2 and reg_addr & 1 != 0) or \
               (bytes > 4):
                return
        else:
            # register type
            reg_type = sxl_obj.get_attr("type")
            if reg_type == "dword" or reg_type == "":
                bytes = 4
            elif reg_type == "word":
                bytes = 2
            elif reg_type == "byte":
                bytes = 1
            else:
                return # unknown register type
        # try to read data from server
        try:
            status, r_data = self.sock.read_bytes(reg_addr, bytes)
        except ConnectionResetError:
            self.socket_event_connection_lost()
            return
        # visualize result
        self.tree.set(item=node, column="data", value="N/A" if not status else f"0x{r_data:0{bytes<<1}X}")
        # update children (signals)
        if block_sig:
            self.treeview_decode_signal(sig=sxl_obj, column="data", reg_value=r_data, status=status)
        else:
            for child in sxl_obj.get_objects_of_type(Sxl.Sig):
                self.treeview_decode_signal(sig=child, column="data", reg_value=r_data, status=status)

    def treeview_decode_signal(self, sig, column: str, sig_value=None, reg_value=None, status=1):
        """Signal value decoder for visualization purposes in treeview columns."""
        # retrieve relevant signal attributes
        node = self.sxl_node_dict[sig]
        # get signal attributes
        sig_type = sig.get_attr("type")
        sig_mode = sig.get_attr("mode")
        sig_pos = sig.get_attr("pos").split(":")
        sig_msb = int(sig_pos[0], 0)
        sig_lsb = sig_msb if len(sig_pos) == 1 else int(sig_pos[1], 0)
        # signal decoder
        if sig_mode == "t":
            self.tree.set(item=node, column=column, value="T")
            return
        if not status or sig_mode == "wo":
            # on read error
            self.tree.set(item=node, column=column, value="")
            return
        if sig_value is None and reg_value is not None:
            # mask out register value to new signal value
            sig_mask = (1 << (sig_msb+1)) - (1 << sig_lsb)
            sig_value = (reg_value & sig_mask) >> sig_lsb
        if sig_type == "enum":
            # decode enum types, show current selection indicator
            found = False
            for enum in sig.get_objects_of_type(Sxl.Enum):
                if sig_value == int(enum.get_attr("value"), 0):
                    found = True
                    self.tree.set(item=node, column=column, value=f"{sig_value} ({enum.name})")
                    self.tree.set(item=self.sxl_node_dict[enum], column=column, value="<<<")
                else:
                    self.tree.set(item=self.sxl_node_dict[enum], column=column, value="")
            if not found:
                self.tree.set(item=node, column=column, value=f"{sig_value}")
            return
        if sig_type == "flag":
            for flag in sig.get_objects_of_type(Sxl.Flag):
                flag_pos = flag.get_attr("pos").split(":")
                if len(flag_pos) == 1:
                    flag_value = (sig_value >> int(flag_pos[0])) & 1
                    self.tree.set(self.sxl_node_dict[flag], column, value=str(flag_value))
        elif sig_type == "flag":
            # add flag support here
            pass
        # try to decode fixed point notations
        match = re.findall(r"^(s|u)([0-9.]+)$", sig_type.lower())
        if len(match) == 1 and len(match[0]) == 2:
            sign, num = match[0]
            num = num.split(".")
            if len(num) > 2:
                # bad fixed point notation
                return
            type_int, type_frac = int(num[0], 0), 0
            if len(num) == 2:
                type_frac = int(num[1], 0)
            val = sig_value
            if sign == "u" and type_frac == 0:
                # fixedpoint notation claims integer value, no conversion required
                self.tree.set(node, column, value=f"{sig_value}")
                return
            if sign == "s" and val >= (1 << (type_int+type_frac-1)):
                val -= (1 << (type_int+type_frac))
            if type_frac > 0:
                ffrac = 6 if (type_frac > 6) else type_frac
                val = f"{val / (1<<type_frac):.{ffrac}f}"
            if sign == 's' and type_frac == 0 and val >= 0:
                # fixedpoint notation claims positive integer value, no conversion required
                self.tree.set(node, column, value=f"{sig_value}")
                return

            self.tree.set(node, column, value=f"{sig_value} ({val})")
            return
        # default value visualization
        self.tree.set(item=node, column=column, value=f"{sig_value}")

    ##################### user interface functions #####################
    def ui_init(self):
        """Initialize the user interface."""
        # clear SXL definitions
        self.sxl.init()
        self.sxl_file = None
        self.sxl_obj_dict = dict()
        self.sxl_node_dict = dict()
        # reset filter
        self.cfg_filter["str"].set("")

    def ui_create(self):
        """Create the user interface."""
        if self.ui_theme and self.ui_theme_sel.get() in self.ui_theme.theme_names():
                self.ui_theme.set_theme(theme_name=self.ui_theme_sel.get())
        self.wm_geometry(newGeometry="640x800")
        self.wm_protocol(name="WM_DELETE_WINDOW", func=self.ui_exit)
        self.wm_iconname(newName=self.name)
        self.wm_iconphoto(True, self.icons.iconSX96, self.icons.iconSX48, self.icons.iconSX32, self.icons.iconSX24, self.icons.iconSX16)
        self.menu_create()
        mainFrame = ttk.Frame(master=self, borderwidth=2)
        mainFrame.pack(expand=True, fill="both")
        # Filter entry row
        filter = ttk.Frame(master=mainFrame)
        self.gui["filter"] = filter
        ttk.Label(master=filter, text="Filter:").pack(side=tk.LEFT, padx=1)
        c = ttk.Combobox(master=filter, textvariable=self.cfg_filter["type"], values=self.cfg_filter_types, width=8, state="readonly")
        c.pack(side=tk.LEFT, padx=1)
        e = ttk.Entry(master=filter, textvariable=self.cfg_filter["str"])
        e.pack(side=tk.LEFT, padx=1)
        ttk.Button(master=filter, text="Clear", command=self.filter_clear)\
            .pack(side=tk.LEFT, padx=1)
        c.bind(sequence="<<ComboboxSelected>>", func=self.filter_update)
        e.bind(sequence="<KeyRelease>", func=self.filter_update)
        # Tree Browser (the main thing!)
        grid = ttk.Frame(master=mainFrame)
        self.gui["grid"] = grid
        treeColumns = ["info", "reset", "data", "dump"]
        tree = ttk.Treeview(master=grid, columns=treeColumns, \
                            displaycolumns=treeColumns, selectmode="browse")
        vsb = ttk.Scrollbar(master=grid, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(master=grid, orient="horizontal", command=tree.xview)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.configure(yscrollcommand=vsb.set)
        tree.configure(xscrollcommand=hsb.set)
        tree.heading(column="#0",   text="Configuration")
        tree.heading(column="info", text="Info")
        tree.heading(column="reset",text="Reset")
        tree.heading(column="data", text="Data")
        tree.heading(column="dump", text="Dump")
        tree.column(column="#0",    stretch=1, minwidth=160, width=220)
        tree.column(column="info",  stretch=1, minwidth=80, width=120)
        tree.column(column="reset", stretch=0, width=0)
        tree.column(column="data",  stretch=1, minwidth=80, width=120)
        tree.column(column="dump",  stretch=0, width=0)
        # pack
        tree.pack(expand=1, fill="both")
        grid.pack(expand=1, fill="both")
        # assign type specific background colors
        palette = "bright"
        for i in self.colors[palette]:
            tree.tag_configure(tagname=i, background=self.colors[palette][i])
        self.tree = tree

        # update default ui states
        self.ui_title_update()

    def ui_title_update(self):
        """Update the title of the user interface."""
        title = f"{self.name} v{self.version}"
        if self.sxl_file:
            title += f" - {os.path.split(self.sxl_file)[1]}"
        if self.sock.connected:
            title += f" - [{self.sock.server}:{self.sock.port}]"
        self.wm_title(string=title)

    def ui_exit(self, event=None) -> None:
        """Exit the application and save the config before."""
        self.ui_save_config()
        sys.exit(0)

    def ui_load_config(self):
        """Load the config."""
        cfg = None
        try:
            with open(self.config_file, "r") as f:
                cfg = json.load(f)
        except:
            return
        if cfg:
            self.ui_init()
            if "sxl_file" in cfg and \
               cfg["sxl_file"] is not None and \
               os.path.isfile(cfg["sxl_file"]):
                self.sxl_file = cfg["sxl_file"]
            else:
                self.sxl_file = None
            if "geometry" in cfg:
                self.wm_geometry(newGeometry=cfg["geometry"])
            if "socket" in cfg and self.sock is not None:
                self.sock.set_config(cfg=cfg["socket"])
            if "gui" in cfg:
                if self.ui_theme and "theme" in cfg["gui"]:
                    self.ui_theme_sel.set(value=cfg["gui"]["theme"])
                    self.menu_change_theme()
                if "show_filter" in cfg["gui"]:
                    self.cfg_menu["show_filter"].set(value=cfg["gui"]["show_filter"])
                    self.toggle_menu_show_filter()
                if "show_reset_column" in cfg["gui"]:
                    self.cfg_menu["show_reset_column"].set(value=cfg["gui"]["show_reset_column"])
                    self.toggle_menu_show_reset_column()
            # initialize and load SXL file
            if self.sxl_file:
                self.sxl.load(file=self.sxl_file)
            self.treeview_gen()

    def ui_save_config(self):
        """Save the config."""
        cfg = dict()
        cfg["geometry"] = self.winfo_geometry()
        if self.sxl_file:
            cfg["sxl_file"] = self.sxl_file
        cfg["socket"] = self.sock.get_config()
        cfg_gui = dict()
        if self.ui_theme:
            cfg_gui["theme"] = self.ui_theme_sel.get()
        cfg_gui["show_filter"] = self.cfg_menu["show_filter"].get()
        cfg_gui["show_reset_column"] = self.cfg_menu["show_reset_column"].get()
        cfg["gui"] = cfg_gui
        try:
            with open(self.config_file, "w") as f:
                json.dump(cfg, f)
        except:
            print(f"Error writing config file '{self.config_file}'")

    def ui_value_toolbox(self, sxl_obj, new: str, max: str):
        """Create the values toolbox."""
        self.com_values_open = 2
        self.com_value = tk.StringVar(value=new)
        self.com_values = tk.Toplevel()
        self.com_values.wm_title(sxl_obj.name)
        self.com_values.attributes("-topmost", 1)
        if platform.system() == "Windows":
            # use for window:
            self.com_values.attributes("-toolwindow", True)
        else:
            # use for linux/mac:
            self.com_values.resizable(width=False, height=False)
        posx, posy = self.com_values.winfo_pointerxy()
        self.com_values.wm_geometry(newGeometry=f"+{posx}+{posy}")

        def post_command(event=None, stat: int=0):
            self.com_values_open = stat
            self.com_values.destroy()
        self.com_values.protocol(name="WM_DELETE_WINDOW", func=post_command)
        f = ttk.Frame(master=self.com_values)
        e = ttk.Entry(master=f, width=32, justify=tk.CENTER, textvariable=self.com_value)
        e.pack(side=tk.TOP, padx=5, pady=6)
        self.com_values_b = b = ttk.Button(master=f, text="Ok", command=lambda:post_command(stat=1))
        b.pack(side=tk.TOP, padx=5, pady=6)
        f.pack()
        # focus and preselect value for faster changes
        e.focus()
        e.selection_range(start=0, end=tk.END)

        def get_value(value: str):
            """Get integer value from entry field textvariable, return None if invalid."""
            if value.isdecimal():
                val = int(value, 0)
                if val >= 0 and val <= max:
                    return val
            else:
                # hex match, binary match
                x_match = re.findall(r"^0x([0-9a-fA-F]+)$", value)
                b_match = re.findall(r"^0b([01]+)$", value)
                if len(x_match) == 1:
                    val = int(x_match[0], 16)
                    if val >= 0 and val <= max:
                        return val
                if len(b_match) == 1:
                    val = int(b_match[0], 2)
                    if val >= 0 and val <= max:
                        return val
            return None

        def set_widget_state(event=None):
            """Set the widget state."""
            # disable ok button per default
            # enable it again after input checks are successful
            value = get_value(value=self.com_value.get())
            if value is None:
                self.com_values_b.configure(state=tk.DISABLED)
            else:
                self.com_values_b.configure(state=tk.NORMAL)

        def accept_widget_state(event=None):
            """Set the widget state to accept if value is not None."""
            value = get_value(value=self.com_value.get())
            if value is not None:
                self.com_values_open = 1
                self.com_values.destroy()


        set_widget_state()
        # bind events
        self.com_values.bind(sequence="<Escape>", func=post_command)
        e.bind(sequence="<KeyRelease>", func=set_widget_state)
        e.bind(sequence="<Return>", func=accept_widget_state)
        e.bind(sequence="<KP_Enter>", func=accept_widget_state)
        e.bind(sequence="<Extended-Return>", func=accept_widget_state)
        while self.com_values_open == 2:
            # FSM wait loop: wait for user response
            time.sleep(0.1)
            self.update()
        if self.com_values_open == 0:
            # aborted
            return None
        # get and return new value
        new = get_value(value=self.com_value.get())
        if new is None:
            # sanity check, should never happen!
            messagebox.showerror(title="Error", message=f"Invalid number '{new}'!")
            return None
        return new

if __name__ == "__main__":
    dt = DasTool()
    dt.mainloop()
