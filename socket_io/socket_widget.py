import platform
import tkinter as tk
import tkinter.ttk as ttk
from socket_io import SocketError, SocketIO
from ui import ToolTip

POPUP_WAIT = 1000
TOOLTIP_DELAY = 500
SOCKET_EVENT = "<<socket_connected>>"
SERVER_TIP = "Enter server name or IP address of the SXIVE socket server!"
PORT_TIP = "Enter port number of the SXIVE socket server!"
DEVICE_TIP = "Enter I\u00b2C device address of the sensor!\nLeave empty if already defined by SXL definition!\nUse hex notation (0xNN)!"

class SocketPopup:
    def __init__(self, tk_root: tk.Tk, socket: SocketIO):
        self.tk_root = tk_root
        self.tk_status = tk.StringVar()
        # bind server address to tk widget
        self.server = tk.StringVar(tk_root)
        self.server.set(socket.server)
        # bind server port to tk widget
        self.port = tk.StringVar(tk_root)
        self.port.set(socket.port)
        # bind server device to tk widget
        self.device_addr = tk.StringVar(tk_root)
        self.device_addr.set(socket.device_addr)

        self.socket = socket
        self._create_toolbox_window()
    
    def _close_toolbox(self):
        """Close toolbox."""
        self.target_win.destroy()
        self.target_win = None

    def _create_toolbox_window(self):
        """Create toolbox window to adjust target connection parameters."""
        # create toolbox window
        self.target_win = tk.Toplevel()
        self.target_win.title("Connect Target...")
        self.target_win.attributes("-topmost", 1)
        if platform.system() == "Windows":
            # use for window:
            self.target_win.attributes("-toolwindow", True)
        else:
            # use for linux/mac:
            self.target_win.resizable(False, False)
        # place window near mouse pointer
        x, y = self.tk_root.winfo_pointerxy()
        self.target_win.geometry(f"+{x}+{y}")
        self.target_win.protocol("WM_DELETE_WINDOW", self._close_toolbox)

        # create toolbox widgets
        f = ttk.Frame(self.target_win)
        self.tk_status.set("Connect with Target..")
        ttk.Label(f, textvariable=self.tk_status, justify=tk.CENTER).pack(
            side=tk.TOP, padx=2, pady=5
        )
        row1 = ttk.Frame(f)
        row2 = ttk.Frame(f)
        row3 = ttk.Frame(f)
        ttk.Label(row1, text="Server:", width=8, anchor=tk.E).pack(side=tk.LEFT, padx=2)
        e1 = ttk.Entry(row1, textvariable=self.server, width=22)
        e1.pack(side=tk.LEFT, padx=2)
        ttk.Label(row2, text="Port:", width=8, anchor=tk.E).pack(side=tk.LEFT, padx=2)
        e2 = ttk.Entry(row2, textvariable=self.port, width=22)
        e2.pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Label(row3, text="Device:", width=8, anchor=tk.E).pack(side=tk.LEFT, padx=2)
        e3 = ttk.Entry(row3, textvariable=self.device_addr, width=22)
        e3.pack(side=tk.LEFT, padx=2, pady=2)
        row1.pack(side=tk.TOP, padx=4, pady=3)
        row2.pack(side=tk.TOP, padx=4, pady=3)
        row3.pack(side=tk.TOP, padx=4, pady=3)

        # bind the callback_function
        self.cmd_button = ttk.Button(
            f, text="Connect", width=10, command=self._connect_socket
        )
        self.cmd_button.pack(side=tk.TOP, padx=2, pady=5)
        f.pack()
        
        # create Tooltips
        self.tooltip1 = ToolTip(widget=e1, text=SERVER_TIP, delay=TOOLTIP_DELAY)
        self.tooltip2 = ToolTip(widget=e2, text=PORT_TIP, delay=TOOLTIP_DELAY)
        self.tooltip3 = ToolTip(widget=e3, text=DEVICE_TIP, delay=TOOLTIP_DELAY)

    def _connect_socket(self):
        """Call the socket connect function."""
        try:
            self.socket.connect(self.server.get(), self.port.get(), self.device_addr.get())
            self.tk_status.set("Connected.")
            self.target_win.update()
            self.tk_root.event_generate(SOCKET_EVENT)
            self.target_win.after(POPUP_WAIT)
            self._close_toolbox()
        except SocketError as e:
            self.tk_status.set(e)
            self.target_win.update()
