import ctypes
import time
from .utils import *
import threading
import os

# Constants
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000

# Structs (must be global if reused)
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("mi", MOUSEINPUT)
    ]

@creation_log
class InterceptionMouse:
    FILTER_MOUSE_ALL = 0xFFFF
    MOUSE_LEFT_BUTTON_DOWN = 0x0002
    MOUSE_LEFT_BUTTON_UP = 0x0004

    _dll_name = "interception.dll"
    _dll_path = os.path.join(os.path.dirname(__file__), _dll_name)
    if not os.path.exists(_dll_path):
        raise FileNotFoundError(f"Could not find {_dll_name} at {_dll_path}")
    _lib = ctypes.WinDLL(_dll_path)

    _Context = ctypes.c_void_p
    _Device = ctypes.c_int

    @creation_log
    class MouseStroke(ctypes.Structure):
        _fields_ = [
            ("state", ctypes.c_ushort),
            ("flags", ctypes.c_ushort),
            ("rolling", ctypes.c_uint),
            ("x", ctypes.c_int),
            ("y", ctypes.c_int),
        ]

    _lib.interception_create_context.restype = _Context
    _lib.interception_destroy_context.argtypes = (_Context,)
    _lib.interception_destroy_context.restype = None

    _PredFn = ctypes.CFUNCTYPE(ctypes.c_int, _Device)
    _interception_is_mouse = _PredFn(("interception_is_mouse", _lib))

    _lib.interception_set_filter.argtypes = (_Context, _PredFn, ctypes.c_uint)
    _lib.interception_set_filter.restype = None

    _lib.interception_wait.argtypes = (_Context,)
    _lib.interception_wait.restype = _Device

    _lib.interception_receive.argtypes = (_Context, _Device, ctypes.c_void_p, ctypes.c_int)
    _lib.interception_receive.restype = ctypes.c_int

    _lib.interception_send.argtypes = (_Context, _Device, ctypes.c_void_p, ctypes.c_int)
    _lib.interception_send.restype = ctypes.c_int

    def __init__(self, hold_duration: float = 0.05, forward_mouse: bool = False):
        self._send_ctx = self._lib.interception_create_context()
        self.hold_duration = hold_duration
        self._dev = None
        self._forward_mouse = forward_mouse

        if forward_mouse:
            self._hook_ctx = self._lib.interception_create_context()
            self._lib.interception_set_filter(
                self._hook_ctx,
                self._interception_is_mouse,
                self.FILTER_MOUSE_ALL
            )
            self._dev = self._lib.interception_wait(self._hook_ctx)
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._forward_loop, daemon=True)
            self._thread.start()
        else:
            # Use dummy device ID (0) or configure as needed for send-only use
            self._dev = 0
            self._hook_ctx = None
            self._thread = None
            self._stop_event = None

    def _forward_loop(self):
        stroke = self.MouseStroke()
        size = ctypes.sizeof(stroke)
        while not self._stop_event.is_set():
            dev = self._lib.interception_wait(self._hook_ctx)
            if dev is None:
                continue
            if self._lib.interception_receive(self._hook_ctx, dev, ctypes.byref(stroke), size) > 0:
                self._lib.interception_send(self._hook_ctx, dev, ctypes.byref(stroke), size)

    def click(self, duration: float = None):
        d = duration if duration is not None else self.hold_duration
        down = self.MouseStroke(state=self.MOUSE_LEFT_BUTTON_DOWN, flags=0, rolling=0, x=0, y=0)
        up   = self.MouseStroke(state=self.MOUSE_LEFT_BUTTON_UP,   flags=0, rolling=0, x=0, y=0)

        self._lib.interception_send(self._send_ctx, self._dev, ctypes.byref(down), ctypes.sizeof(down))
        time.sleep(d)
        self._lib.interception_send(self._send_ctx, self._dev, ctypes.byref(up), ctypes.sizeof(up))

    def move(self, dx: int, dy: int):
        mv = self.MouseStroke(state=0, flags=0, rolling=0, x=dx, y=dy)
        self._lib.interception_send(self._send_ctx, self._dev, ctypes.byref(mv), ctypes.sizeof(mv))

    def click_and_move(self, dx: int, dy: int, duration: float = None):
        self.move(dx, dy)
        self.click(duration)

    # def click_at(self, hwnd, x, y, duration: float = None):
    #     if not win32gui.IsWindow(hwnd):
    #         print("[ERROR] Invalid hwnd")
    #         return

    #     window_title = win32gui.GetWindowText(hwnd)
    #     print(f"[INFO] Clicking in window: {window_title}")

    #     # Get the client area size (excluding borders and title bar)
    #     client_rect = win32gui.GetClientRect(hwnd)
    #     client_width = client_rect[2] - client_rect[0]
    #     client_height = client_rect[3] - client_rect[1]

    #     print(f"[DEBUG] Client area: (0, 0) to ({client_width}, {client_height})")
    #     print(f"[DEBUG] Target click at client coords: ({x}, {y})")

    #     lparam = win32api.MAKELONG(x, y)

    #     win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
    #     win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    #     time.sleep(duration if duration is not None else self.hold_duration)
    #     win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    #     print("[INFO] Click sent.")


    #################################
    def __del__(self):
        try:
            if self._forward_mouse:
                self._stop_event.set()
                if self._thread and self._thread.is_alive():
                    self._thread.join(timeout=0.1)
                self._lib.interception_destroy_context(self._hook_ctx)

            if self._send_ctx:
                self._lib.interception_destroy_context(self._send_ctx)
        except Exception:
            pass