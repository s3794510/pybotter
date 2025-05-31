from typing import Tuple
import numpy as np
#from numpy.testing._private.nosetester import NoseTester
import win32gui, win32ui, win32con
import cv2
import ctypes
from datetime import datetime
from .utils import *

@creation_log
class WindowHandler:

    # constructor
    def __init__(self, window_name=None):
        self.window_name = window_name
        self.hwnd = None
        self.find_window()
        self.w, self.h = -1, -1
        self.get_window_size()
        log("[INFO]", f"Window size is: {self.w}, {self.h}")

    def get_window_size(self):
        # Get the client area size (exclude borders, title bar)
        if (self.hwnd is None or self.hwnd == 0):
            self.hwnd = win32gui.GetDesktopWindow()
        rect = win32gui.GetClientRect(self.hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w != self.w or h != self.h:
            log("[INFO]", f"Window size is changed to: {w}, {h}")
        self.w, self.h = w, h

    def find_window(self):
        if self.window_name is None:
            self.hwnd = win32gui.GetDesktopWindow()
        else:
            self.hwnd = win32gui.FindWindow(None, self.window_name)
            # if not self.hwnd:
            #     raise Exception('Window not found: {}'.format(self.window_name))

    def get_screenshot(self, debug=False):
        w, h = self.w, self.h

        # Validate window handle
        if not win32gui.IsWindow(self.hwnd) or self.hwnd == win32gui.GetDesktopWindow():
            log("[INFO]", "Window handle invalid. Trying to find the window again...")
            self.find_window()
            if not self.hwnd or not win32gui.IsWindow(self.hwnd):
                self.get_window_size()
                log("[ERROR]", "Window not found. Returning black screen.")
                return np.zeros((h, w, 3), dtype=np.uint8)
        self.get_window_size()
        if w == 0 or h == 0:
            log("[WARNING]", "The target window is not present.")
            return None
        hwnd = self.hwnd

        try:
            # Get window rect (includes border and title bar)
            window_rect = win32gui.GetWindowRect(hwnd)
            win_w = window_rect[2] - window_rect[0]
            win_h = window_rect[3] - window_rect[1]

            # Get the window device context
            hwndDC = win32gui.GetWindowDC(hwnd)
            srcDC = win32ui.CreateDCFromHandle(hwndDC)
            memDC = srcDC.CreateCompatibleDC()

            # Create a compatible bitmap for the whole window
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcDC, win_w, win_h)
            memDC.SelectObject(bmp)

            # Use PrintWindow to capture the full window (with borders)
            result = ctypes.windll.user32.PrintWindow(hwnd, memDC.GetSafeHdc(), 0x2)

            if result != 1:
                log("[WARNING]", "PrintWindow failed. Returning black screen.")
                img = np.zeros((h, w, 3), dtype=np.uint8)
            else:
                # Convert the bitmap to numpy array
                bmp_info = bmp.GetInfo()
                bmp_str = bmp.GetBitmapBits(True)
                full_img = np.frombuffer(bmp_str, dtype=np.uint8).reshape((win_h, win_w, 4))

                # Get the client area position relative to the window
                client_rect = win32gui.GetClientRect(hwnd)
                client_pos = win32gui.ClientToScreen(hwnd, (0, 0))
                border_left = client_pos[0] - window_rect[0]
                border_top = client_pos[1] - window_rect[1]

                # Crop the client area from the full image
                img = full_img[border_top:border_top + h, border_left:border_left + w]
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # Cleanup GDI resources
            memDC.DeleteDC()
            srcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            win32gui.DeleteObject(bmp.GetHandle())

        except Exception as e:
            log("[ERROR]", f"Screenshot capture failed: {e}")
            img = np.zeros((h, w, 3), dtype=np.uint8)

        if 'capture' in debug:
            cv2.imshow("Captured Window", img)
            cv2.waitKey(1)

        return img



    ######################################################

    # find the name of the window you're interested in.
    # once you have it, update window_capture()
    # https://stackoverflow.com/questions/55547940/how-to-get-a-list-of-the-name-of-every-open-window
    @staticmethod
    def list_window_titles():
        def winEnumHandler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                print(hex(hwnd), win32gui.GetWindowText(hwnd))
        win32gui.EnumWindows(winEnumHandler, None)
        return 0

    def get_screen_position(self, pos):
        return (pos[0] + self.offset_x, pos[1] + self.offset_y)

    @staticmethod
    def get_windowsize(self) -> Tuple:
        return win32gui.GetWindowRect(self.hwnd)

    # def get_winhandler(self, window_name):
    #     if window_name is None:
    #         hwnd = win32gui.GetDesktopWindow()
    #     else:
    #         hwnd = win32gui.FindWindow(None, window_name)
    #         if not hwnd:
    #             raise Exception('Window not found: {}'.format(window_name))
    #     return hwnd
    
    def window_resize(self, w, h) -> None:
        win32gui.MoveWindow(self.hwnd, 0, 0, w, h, True)
        self.w = w
        self.h = h
        return 0
    