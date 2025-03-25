from typing import Tuple
import numpy as np
#from numpy.testing._private.nosetester import NoseTester
import win32gui, win32ui, win32con
import cv2
import ctypes

class WindowHandler:
    
    # constructor
    def __init__(self, window_name=None):
        self.window_name = window_name
        self.hwnd = None
        self.find_window()
        if not self.hwnd:
            raise Exception(f"[ERROR] Cannot find window: {window_name}")
        self.w, self.h = self.get_window_size()

    def get_window_size(self):
        # Get the client area size (exclude borders, title bar)
        rect = win32gui.GetClientRect(self.hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        return w, h
    
    def get_client_area_offset(self):
        # Get the top-left corner of the client area in screen coordinates
        point = win32gui.ClientToScreen(self.hwnd, (0, 0))
        return point  # (x, y)
        
    def find_window(self):
        if self.window_name is None:
            self.hwnd = win32gui.GetDesktopWindow()
        else:
            self.hwnd = win32gui.FindWindow(None, self.window_name)
            if not self.hwnd:
                raise Exception('Window not found: {}'.format(self.window_name))




    def get_screenshot(self, debug=False):
        w, h = self.w, self.h

        # Validate window handle
        if not win32gui.IsWindow(self.hwnd):
            print("[INFO] Window handle invalid. Trying to find the window again...")
            self.hwnd = self.find_window()
            if not self.hwnd or not win32gui.IsWindow(self.hwnd):
                print("[ERROR] Window not found. Returning black screen.")
                return np.zeros((h, w, 3), dtype=np.uint8)

        hwnd = self.hwnd

        try:
            # Get the window device context
            hwndDC = win32gui.GetWindowDC(hwnd)
            srcDC = win32ui.CreateDCFromHandle(hwndDC)
            memDC = srcDC.CreateCompatibleDC()

            # Create a compatible bitmap
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcDC, w, h)
            memDC.SelectObject(bmp)

            # Use ctypes to call PrintWindow
            result = ctypes.windll.user32.PrintWindow(hwnd, memDC.GetSafeHdc(), 0x2)

            if result != 1:
                print("[WARNING] PrintWindow failed. Returning black screen.")
                img = np.zeros((h, w, 3), dtype=np.uint8)
            else:
                # Convert the bitmap to numpy array
                bmp_info = bmp.GetInfo()
                bmp_str = bmp.GetBitmapBits(True)
                img = np.frombuffer(bmp_str, dtype=np.uint8).reshape((h, w, 4))
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # Cleanup GDI resources
            memDC.DeleteDC()
            srcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            win32gui.DeleteObject(bmp.GetHandle())

        except Exception as e:
            print(f"[ERROR] Screenshot capture failed: {e}")
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

    # translate a pixel position on a screenshot image to a pixel position on the screen.
    # pos = (x, y)
    # WARNING: if you move the window being captured after execution is started, this will
    # return incorrect coordinates, because the window position is only calculated in
    # the __init__ constructor.

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