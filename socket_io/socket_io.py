"""
    Socket I/O communication client to use the (s)imple data e(x)change protocol
    Version: 01
"""

import re
import socket

RESPONSE_FLAG_SIZE = 1
RESPONSE_DATA_SIZE = 4
NO_DEVICE = ""
NO_DEVICE_ADDR = -1

MAX_PORT_NUMBER = 65535
MIN_PORT_NUMBER = 1023
SOCKET_TIMEOUT_SEC = 3.0

class SocketError(Exception):
    pass

class ErrorMessages:
    CONNECTION_FAILED = "Connection Failed!"
    INVALID_PORT_NUMBER = "Invalid Port number!"
    INVALID_DEVICE_ADDRESS = "Invalid device address!"
    DEVICE_ADDRESS_TOO_LARGE = "Device address too large!"
    PORT_NUMBER_OUT_OF_RANGE = f"Port number is not in range {MIN_PORT_NUMBER} - {MAX_PORT_NUMBER}"

class SocketIO:
    def __init__(self) -> None:
        self.sock = None
        self.connected = False
        self.server_version = 0
        self.retries = 5
        self.server = "localhost"
        self.port = 1234
        self.device_addr = "0x36"
        # ui
        self.target_win = None
        self.device_addr_int = NO_DEVICE_ADDR

    def set_config(self, cfg):
        if "server" in cfg:
            self.server = str(cfg["server"])
        if "port" in cfg:
            self.port = int(cfg["port"])
        if "device" in cfg:
            self.device_addr = str(cfg["device"])

    def get_config(self):
        cfg = dict()
        cfg["server"] = self.server
        cfg["port"] = self.port
        cfg["device"] = self.device_addr
        return cfg

    def connect(self, server: str, port: str, device_addr: str=NO_DEVICE):
        """Connect to target.
        Returns error code."""
        self.server = server
        device_addr_int = NO_DEVICE_ADDR
        # validate port
        try:
            port = int(port)
        except:
            raise SocketError(ErrorMessages.INVALID_PORT_NUMBER)
        if not port <= MAX_PORT_NUMBER or not port > MIN_PORT_NUMBER:
            raise SocketError(ErrorMessages.PORT_NUMBER_OUT_OF_RANGE)
        self.port = port
        # convert device addr and validate it
        if device_addr == NO_DEVICE:
            device_addr_int = NO_DEVICE_ADDR
        else:
            hex_match = re.findall(r"^0x([0-9a-fA-F]+)$", device_addr)
            if len(hex_match) == 1:
                device_addr_int = int(hex_match[0], 16)
            else:
                raise SocketError(ErrorMessages.INVALID_DEVICE_ADDRESS)
            if device_addr_int >= 256:
                raise SocketError(ErrorMessages.DEVICE_ADDRESS_TOO_LARGE)
        # no errors on configuration
        self.device_addr = device_addr
        self.device_addr_int = device_addr_int
        # try to connect to target
        if not self._connect(server, int(port)):
            raise SocketError(ErrorMessages.CONNECTION_FAILED)

    def _connect(self, server, port) -> bool:
        """Connect to socket server."""
        if self.connected:
            # bad UI binding: try to connect even though
            # socket server is already connected!
            return False
        # create an instance of the socket connector
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # set general timeout for any I/O request
        self.sock.settimeout(SOCKET_TIMEOUT_SEC)
        try:
            # try to connect
            self.sock.connect((server, port))
        except socket.error:
            # something went wrong, connection not established
            self.sock.close()
            self.sock = None
            return False
        # send version command (not implemented yet) and see what happens
        packet = bytearray()
        packet.extend(b"v")  # future version cmd 
        success, version = 0, 0
        try:
            self.sock.send(packet)
            data = self.sock.recv(5)  # expected zero-response of 5 num_bytes
        except TimeoutError:
            pass
        else:
            if len(data) == RESPONSE_FLAG_SIZE + RESPONSE_DATA_SIZE:
                success, version = data[0], int.from_bytes(data[1:], "little")
                if success:
                    self.server_version = version

        # almost done
        # consider connected and ready for action
        self.connected = True
        return True

    def disconnect(self) -> None:
        """disconnect from socket server"""
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.sock.close()
        self.connected = False
        self.sock = None

    # I/O base functions
    def write_bytes(self, addr: int, data: int, num_bytes: int):
        """generic size write command"""
        if self.sock is None:
            return None
        bits = num_bytes << 3
        device = self.device_addr_int
        assert addr >= 0 and addr < 1 << 32, "Address out of 32bit range: " + addr
        assert data >= 0 and data < 1 << 32, "Data out of range: " + data
        assert bits >= 0 and bits < 256, "Invalid write size: " + bits + " bits"
        assert device == NO_DEVICE_ADDR or (device >= 0 and device < 256), \
                    "Device address out of range: " + device
        if device != NO_DEVICE_ADDR:
            # override device address of sxl definition
            addr = (device << 24) | (addr & 0xFFFFFF)
        # create packet
        packet = bytearray()
        packet.extend(b"w")  # cmd
        packet.extend(bits.to_bytes(length=1, byteorder="little"))  # size
        packet.extend(addr.to_bytes(length=4, byteorder="little"))  # addr
        packet.extend(data.to_bytes(length=num_bytes, byteorder="little"))  # data
        success, r_data = 0, 0
        for _ in range(self.retries):
            try:
                self.sock.send(packet)
            except BrokenPipeError or ConnectionAbortedError:
                self.tkinter.socket_event_connection_lost()
                break
            # expected echo reply: success flag + data num_bytes
            try:
                data = self.sock.recv(RESPONSE_FLAG_SIZE + RESPONSE_DATA_SIZE)
            except BrokenPipeError or ConnectionAbortedError:
                self.tkinter.socket_event_connection_lost()
                break
            if len(data) == RESPONSE_FLAG_SIZE + RESPONSE_DATA_SIZE:
                success, r_data = data[0], int.from_bytes(data[1:], "little")
                if success:
                    break
        return success, r_data

    def read_bytes(self, addr: int, num_bytes: int):
        """generic size read command"""
        if self.sock is None:
            return None
        bits = num_bytes << 3
        device = self.device_addr_int
        assert addr >= 0 and addr < 1 << 32, "Address out of 32bit range: " + addr
        assert bits >= 0 and bits < 256, "Invalid read size: " + bits + " bits"
        assert device == NO_DEVICE_ADDR or (device >= 0 and device < 256), \
                    "Device address out of range: " + device
        if device != NO_DEVICE_ADDR:
            # override device address of sxl definition
            addr = (device << 24) | (addr & 0xFFFFFF)
        # create packet
        packet = bytearray()
        packet.extend(b"r")  # cmd
        packet.extend(bits.to_bytes(length=1, byteorder="little"))  # size
        packet.extend(addr.to_bytes(length=4, byteorder="little"))  # addr
        success, r_data = 0, 0
        for _ in range(self.retries):
            try:
                self.sock.send(packet)
            except BrokenPipeError or ConnectionAbortedError:
                self.tkinter.socket_event_connection_lost()
                break
            # expected reply: success flag + data num_bytes
            try:
                data = self.sock.recv(RESPONSE_FLAG_SIZE + RESPONSE_DATA_SIZE)
            except BrokenPipeError or ConnectionAbortedError:
                self.tkinter.socket_event_connection_lost()
                break
            if len(data) == RESPONSE_FLAG_SIZE + RESPONSE_DATA_SIZE:
                success, r_data = data[0], int.from_bytes(data[1:], "little")
                if success:
                    break
        return success, r_data

    def modify_bytes(self, addr: int, data: int, mask: int, num_bytes: int):
        """generic size read-modify-write command"""
        if self.sock is None:
            return None
        bits = num_bytes << 3
        assert addr >= 0 and addr < 1 << 32, "Address out of 32bit range: " + addr
        assert data >= 0 and data < 1 << 32, "Data out of range: " + data
        assert mask >= 0 and mask < 1 << 32, "Mask out of range: " + mask
        assert bits >= 0 and bits < 256, "Invalid write size: " + bits + " bits"
        success, r_data = self.read_bytes(addr, num_bytes)
        if success:
            rMask = mask ^ ((1 << bits) - 1)
            w_data = (r_data & rMask) | (data & mask)
            success, r_data = self.write_bytes(addr, w_data, num_bytes)
        return success, r_data
