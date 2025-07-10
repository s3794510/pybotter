import ctypes
from time import sleep, time
from .utils import *
import threading
import os
import win32api, win32gui, win32con

# Constants
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

# Structs
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("mi", MOUSEINPUT)
    ]

@creation_log
class SendInputMouse:
    @staticmethod
    def click_at_current(duration=0.05):
        """Click at the current mouse position using SendInput."""
        down = INPUT()
        down.type = INPUT_MOUSE
        down.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)

        up = INPUT()
        up.type = INPUT_MOUSE
        up.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)

        ctypes.windll.user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(down))
        sleep(duration)
        ctypes.windll.user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(up))

    @staticmethod
    def move_to_window_point(hwnd, x, y):
        """Move cursor to a point inside a window (client to screen coords)."""
        point = ctypes.wintypes.POINT(x, y)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
        ctypes.windll.user32.SetCursorPos(point.x, point.y)

    @staticmethod
    def click_on_window(hwnd, x, y, duration=0.05):
        """Move to point in window and click using SendInput."""
        SendInputMouse.move_to_window_point(hwnd, x, y)
        SendInputMouse.click_at_current(duration)

    @staticmethod
    def click_with_sendmessage(hwnd, x, y, duration=0.05):
        """Click inside a window directly using Win32 messages (only works for GUI apps)."""
        lparam = win32api.MAKELONG(x, y)
        win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        sleep(duration)
        win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    @staticmethod
    def click_at_current_to_window(hwnd, duration=0.05):
        """Send a real click at the current position to the foreground window using SendInput."""
        try:
            # Validate window handle
            if not win32gui.IsWindow(hwnd):
                log("[ERROR]", f"Invalid window handle: {hwnd}")
                return False

            # Check if window is already in the foreground
            foreground_hwnd = win32gui.GetForegroundWindow()
            if foreground_hwnd == hwnd:
                # Window is already in foreground, skip activation logic
                down = INPUT()
                down.type = INPUT_MOUSE
                down.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)

                up = INPUT()
                up.type = INPUT_MOUSE
                up.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)

                ctypes.windll.user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(down))
                sleep(duration)
                ctypes.windll.user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(up))
                return True

            # Try to show and activate window
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            except Exception as e:
                log("[WARNING]", f"Failed to show window: {e}")

            # Enhanced foreground window handling
            max_attempts = 3
            window_activated = False
            
            for attempt in range(max_attempts):
                try:
                    # Try to set foreground window
                    win32gui.SetForegroundWindow(hwnd)
                    sleep(0.1)  # Give Windows time to process
                    
                    # Verify if window is actually in foreground
                    foreground_hwnd = win32gui.GetForegroundWindow()
                    if foreground_hwnd == hwnd:
                        window_activated = True
                        log("[INFO]", f"Window successfully brought to foreground on attempt {attempt + 1}")
                        break
                    else:
                        foreground_title = win32gui.GetWindowText(foreground_hwnd)
                        target_title = win32gui.GetWindowText(hwnd)
                        log("[WARNING]", f"Window not in foreground. Current: '{foreground_title}', Target: '{target_title}' (attempt {attempt + 1})")
                        
                        # Additional methods to force foreground
                        if attempt < max_attempts - 1:
                            # Try alternative methods
                            try:
                                # Method 1: Use AttachThreadInput
                                win32gui.AttachThreadInput(win32api.GetCurrentThreadId(), 
                                                         win32api.GetWindowThreadProcessId(foreground_hwnd)[0], True)
                                win32gui.SetForegroundWindow(hwnd)
                                win32gui.AttachThreadInput(win32api.GetCurrentThreadId(), 
                                                         win32api.GetWindowThreadProcessId(foreground_hwnd)[0], False)
                            except:
                                pass
                            
                            try:
                                # Method 2: Use ShowWindow with SW_SHOW
                                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                                win32gui.SetForegroundWindow(hwnd)
                            except:
                                pass
                            
                            sleep(0.2)  # Longer delay between attempts
                        
                except Exception as e:
                    if attempt == max_attempts - 1:
                        log("[ERROR]", f"Failed to set foreground window after {max_attempts} attempts: {e}")
                    else:
                        log("[WARNING]", f"Foreground attempt {attempt + 1} failed: {e}")
                        sleep(0.2)
            
            if not window_activated:
                log("[WARNING]", f"Window could not be brought to foreground after {max_attempts} attempts. Proceeding with click anyway.")
                log("[ERROR]", f"Window could not be brought to foreground after {max_attempts} attempts. Aborting click.")
                return False

            # Perform the click
            down = INPUT()
            down.type = INPUT_MOUSE
            down.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)

            up = INPUT()
            up.type = INPUT_MOUSE
            up.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)

            ctypes.windll.user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(down))
            sleep(duration)
            ctypes.windll.user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(up))
                
            return True

        except Exception as e:
            log("[ERROR]", f"Failed to perform click operation: {e}")
            return False

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
        sleep(d)
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
    #     sleep(duration if duration is not None else self.hold_duration)
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