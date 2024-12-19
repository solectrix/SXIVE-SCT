import tkinter as tk
import tkinter.ttk as ttk

class ToolTip(object):
    """Create a tooltip for a given widget."""
    def __init__(self, widget: tk.Widget, text: str="widget info", delay: int=0):
        self.wait_time = delay     #milliseconds
        self.wrap_length = 320   #pixels
        self.pos_offset = (4, 12) #(x,y)
        self.widget = widget
        self.text = text
        self.x = None
        self.y = None
        self.id = None
        self.tw = None
        self.label = None
        # create TK event bindings
        self.widget.bind(sequence="<Enter>", func=self.enter)
        self.widget.bind(sequence="<Leave>", func=self.leave)
        self.widget.bind(sequence="<Motion>", func=self.motion)

    def enter(self, event: tk.Event):
        """Entry event, start scheduler for wait time."""
        self.x = event.x_root
        self.y = event.y_root
        self.schedule()

    def leave(self, event: tk.Event):
        """Leave event, hide Tooltip."""
        self.unschedule()
        self.hidetip()

    def motion(self, event: tk.Event):
        """Motion event, update ToolTip position to prevent some event conflicts 
            with Widget item and ToolTip itself (keep distance!)."""
        self.x = event.x_root
        self.y = event.y_root
        if self.tw:
            # update ToolTip position once when shown
            x = self.x + self.pos_offset[0]
            y = self.y + self.pos_offset[1]
            self.tw.wm_geometry(newGeometry="+%d+%d" % (x, y))

    def schedule(self):
        """Reset timer and prepare for rise of ToolTip message."""
        self.unschedule()
        self.id = self.widget.after(ms=self.wait_time, func=self.showtip)

    def unschedule(self):
        """Drop scheduler."""
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id=id)

    def showtip(self):
        """Create ToolTip message."""
        # set position relative to entry point
        x = self.x + self.pos_offset[0]
        y = self.y + self.pos_offset[1]
        # creates a toplevel window
        self.tw = tk.Toplevel(master=self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_attributes("-topmost", 1)
        self.tw.wm_overrideredirect(boolean=True)
        self.tw.wm_geometry(newGeometry="+%d+%d" % (x, y))
        self.label = tk.Label(master=self.tw, text=self.text, justify="left",
            background="#ffffcc", relief="solid", borderwidth=1,
            wraplength= self.wrap_length)
        self.label.pack(ipadx=2)

    def hidetip(self):
        """Kill ToolTip message."""
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

class CanvasToolTip(object):
    """Create a tooltip for a given widget."""

    def __init__(self, canvas: tk.Canvas, widget: tk.Widget, text: str="widget info", delay: int=0, justify: str="left"):
        self.wait_time = delay     #milliseconds
        self.wrap_length = 320   #pixels
        self.pos_offset = (4, 12) #(x,y)
        self.canvas = canvas
        self.widget = widget
        self.text = text
        self.x = None
        self.y = None
        self.id = None
        self.tw = None
        self.visible = False
        self.label = None
        self.justify = justify

        # create TK event bindings
        self.canvas.tag_bind(tagOrId=self.widget, func="<Enter>", add=self.enter)
        self.canvas.tag_bind(tagOrId=self.widget, func="<Leave>", add=self.leave)
        self.canvas.tag_bind(tagOrId=self.widget, func="<Motion>", add=self.motion)

    def enter(self, event: tk.Event):
        """Entry event, start scheduler for wait time."""
        if not self.visible:
            self.x = event.x_root
            self.y = event.y_root
            self.schedule()
            self.visible = True

    def leave(self, event: tk.Event):
        """Leave event, hide Tooltip."""
        self.unschedule()
        self.hidetip()
        self.visible = False

    def motion(self, event):
        """Motion event, update ToolTip position to prevent some event conflicts 
            with Widget item and ToolTip itself (keep distance!)."""
        self.x = event.x_root
        self.y = event.y_root
        if self.tw:
            # update ToolTip position once when shown
            x = self.x + self.pos_offset[0]
            y = self.y + self.pos_offset[1]
            self.tw.wm_geometry(newGeometry="+%d+%d" % (x, y))

    def schedule(self):
        """Reset timer and prepare for rise of ToolTip message."""
        self.unschedule()
        self.id = self.canvas.after(ms=self.wait_time, func=self.showtip)

    def unschedule(self):
        """Drop scheduler."""
        id = self.id
        self.id = None
        if id:
            self.canvas.after_cancel(id=id)

    def updateTip(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        try:
            self.label.configure(text=text)
        except:
            pass
        # create TK event bindings
        self.canvas.tag_bind(tagOrId=self.widget, func="<Enter>", add=self.enter)
        self.canvas.tag_bind(tagOrId=self.widget, func="<Leave>", add=self.leave)
        self.canvas.tag_bind(tagOrId=self.widget, func="<Motion>", add=self.motion)

    def showtip(self):
        """Create ToolTip message."""
        # set position relative to entry point
        x = self.x + self.pos_offset[0]
        y = self.y + self.pos_offset[1]
        # creates a toplevel window
        self.tw = tk.Toplevel(master=self.canvas)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(boolean=True)
        self.tw.wm_geometry(newGeometry="+%d+%d" % (x, y))
        self.label = tk.Label(master=self.tw, text=self.text, justify=self.justify,
            background="#ffffcc", relief="solid", borderwidth=1,
            wrap_length = self.wrap_length)
        self.label.pack(ipadx=2)

    def hidetip(self):
        """Kill ToolTip message."""
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()
    
    def kill(self):
        """"Close tooltip."""
        self.unschedule()
        self.hidetip()
        del self

class TreeviewToolTip(object):
    """Create a tooltip for a given treeview widget."""
    def __init__(self, das_tool: tk.Widget, tree: ttk.Treeview, text: str="", delay: int=0):
        self.wait_time = delay     #milliseconds
        self.wrap_length = 320   #pixels
        self.pos_offset = (4, 12) #(x,y)
        self.das_tool = das_tool
        self.tree = tree
        self.text = tk.StringVar(value=text)
        self.x = None
        self.y = None
        self.id = None
        self.tw = None
        self.label = None
        self.lastIid = ""
        # create TK event bindings
        self.das_tool.bind_all(sequence="<<RowEnter>>", func=self.enter)
        self.das_tool.bind_all(sequence="<<RowLeave>>", func=self.leave)
        self.tree.bind("<Leave>", self.leave)
        self.tree.bind("<Motion>", self.motion)

    def enter(self, event: tk.Event):
        """Entry event, start scheduler for wait time."""
        self.x = event.x_root
        self.y = event.y_root
        self.schedule()

    def leave(self, event: tk.Event=None):
        """Leave event, hide Tooltip."""
        self.unschedule()
        self.hidetip()

    def motion(self, event: tk.Event):
        """Motion event, update ToolTip position to prevent some event conflicts 
            with Widget item and ToolTip itself (keep distance!)."""
        self.x = event.x_root
        self.y = event.y_root
        _iid = self.tree.identify_row(event.y)
        if _iid:
            # set tooltip text according to current treeview element
            desc = self.das_tool.sxl_obj_dict[_iid].get_attr("desc")
            if desc != "":
                self.text.set(desc)
                if self.tw:
                    # update ToolTip position once when shown
                    x = self.x + self.pos_offset[0]
                    y = self.y + self.pos_offset[1]
                    self.tw.wm_geometry("+%d+%d" % (x, y))
            else:
                self.leave()
        if _iid != self.lastIid:
            if self.lastIid != "":
                self.das_tool.event_generate(sequence="<<RowLeave>>",
                                            data=self.lastIid,
                                            x=event.x,
                                            y=event.y,
                                            rootx=event.x_root,
                                            rooty=event.y_root)
            if _iid != "":
                self.das_tool.event_generate(sequence="<<RowEnter>>", 
                                            data=self.lastIid,
                                            x=event.x,
                                            y=event.y,
                                            rootx=event.x_root,
                                            rooty=event.y_root)
        self.lastIid = _iid

    def schedule(self):
        """Reset timer and prepare for rise of ToolTip message."""
        self.unschedule()
        self.id = self.tree.after(self.wait_time, self.showtip)

    def unschedule(self):
        """Drop scheduler."""
        id = self.id
        self.id = None
        if id:
            self.tree.after_cancel(id)

    def showtip(self):
        """Create ToolTip message."""
        # set position relative to entry point
        x = self.x + self.pos_offset[0]
        y = self.y + self.pos_offset[1]
        # creates a toplevel window
        self.tw = tk.Toplevel(self.tree)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        self.label = tk.Label(master=self.tw, textvariable=self.text, justify="left",
            background="#ffffcc", relief="solid", borderwidth=1,
            wraplength = self.wrap_length)
        self.label.pack(ipadx=4, ipady=2)

    def hidetip(self):
        """Kill ToolTip message."""
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()
