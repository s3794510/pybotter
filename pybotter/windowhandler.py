from typing import Tuple
import numpy as np
#from numpy.testing._private.nosetester import NoseTester
import win32gui, win32ui, win32con
import cv2
import ctypes
from datetime import datetime
from .utils import *
try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

@creation_log
class WindowHandler:

    # constructor
    def __init__(self, window_name=None, use_gpu=True, preferred_backend='auto'):
        """
        Initialize WindowHandler with optional GPU acceleration
        Args:
            window_name: Name of the window to capture
            use_gpu: Whether to use GPU acceleration
            preferred_backend: 'auto', 'opencl', or 'cuda'
        """
        self.window_name = window_name
        self.hwnd = None
        self.find_window()
        self.w, self.h = -1, -1
        self.get_window_size()
        self.mss_instance = mss.mss() if MSS_AVAILABLE else None
        self.last_window_rect = None
        self.last_check_time = 0
        
        # GPU setup with unified memory approach
        self.use_gpu = use_gpu
        self.gpu_backend = None
        self._setup_gpu(preferred_backend)
        
        # Pre-allocate reusable GPU memory if possible
        self.gpu_input_mat = None
        self.gpu_output_mat = None
        
        log("[INFO]", f"Window size is: {self.w}, {self.h}")

    def _setup_gpu(self, preferred_backend='auto'):
        """
        Setup GPU acceleration with unified approach for both OpenCL and CUDA
        """
        if not self.use_gpu:
            return

        try:
            if preferred_backend == 'auto' or preferred_backend == 'opencl':
                # Try OpenCL first - it's more universally supported
                if cv2.ocl.haveOpenCL():
                    cv2.ocl.setUseOpenCL(True)
                    if cv2.ocl.useOpenCL():
                        self.gpu_backend = 'opencl'
                        device = cv2.ocl.Device.getDefault()
                        device_name = device.name()
                        log("[INFO]", f"GPU acceleration enabled using OpenCL device: {device_name}")
                        return

            if preferred_backend == 'auto' or preferred_backend == 'cuda':
                # Try CUDA if OpenCL isn't available or CUDA is preferred
                if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                    self.gpu_backend = 'cuda'
                    # Initialize CUDA stream and memory pool
                    cv2.cuda.setBufferPoolUsage(True)
                    cv2.cuda.setBufferPoolConfig(1024 * 1024 * 64, 2)  # 64MB pool, 2 streams
                    self.gpu_stream = cv2.cuda.Stream()
                    log("[INFO]", "GPU acceleration enabled using CUDA")
                    return

            self.use_gpu = False
            log("[WARNING]", "No GPU acceleration available")

        except Exception as e:
            self.use_gpu = False
            log("[WARNING]", f"Failed to initialize GPU acceleration: {str(e)}")

    def _ensure_gpu_mats(self, shape):
        """Ensure GPU matrices are allocated with correct size"""
        if not self.use_gpu:
            return

        h, w = shape[:2]
        
        if self.gpu_backend == 'cuda':
            # For CUDA, check if we need to reallocate
            if (self.gpu_input_mat is None or 
                self.gpu_input_mat.size() != (h, w)):
                # Free existing memory if any
                if self.gpu_input_mat is not None:
                    self.gpu_input_mat.release()
                    self.gpu_output_mat.release()
                # Allocate new memory
                self.gpu_input_mat = cv2.cuda_GpuMat(h, w, cv2.CV_8UC4)
                self.gpu_output_mat = cv2.cuda_GpuMat(h, w, cv2.CV_8UC3)
        elif self.gpu_backend == 'opencl':
            # For OpenCL, we create UMats on demand in _convert_to_bgr_gpu
            # No pre-allocation needed as UMat handles memory management
            pass

    def _convert_to_bgr_gpu(self, img_bgra):
        """
        Convert BGRA to BGR using GPU with unified memory management
        """
        if not self.use_gpu:
            return cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2BGR)

        try:
            # Ensure GPU matrices are allocated
            self._ensure_gpu_mats(img_bgra.shape)

            if self.gpu_backend == 'cuda':
                # Upload with minimal copying
                self.gpu_input_mat.upload(img_bgra, self.gpu_stream)
                # Convert color space
                cv2.cuda.cvtColor(self.gpu_input_mat, cv2.COLOR_BGRA2BGR, 
                                self.gpu_output_mat, stream=self.gpu_stream)
                # Download result
                return self.gpu_output_mat.download(stream=self.gpu_stream)

            elif self.gpu_backend == 'opencl':
                # OpenCL processing with minimal copying
                # Convert numpy array to UMat
                gpu_input = cv2.UMat(img_bgra)
                gpu_output = cv2.UMat(img_bgra.shape[0], img_bgra.shape[1], cv2.CV_8UC3)
                # Convert color space
                cv2.cvtColor(gpu_input, cv2.COLOR_BGRA2BGR, gpu_output)
                return gpu_output.get()

        except Exception as e:
            log("[WARNING]", f"GPU conversion failed, falling back to CPU: {str(e)}")
            return cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2BGR)

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

    def get_screenshot(self, debug=False, method='auto'):
        """
        Capture a screenshot of the window using the specified method.
        Args:
            debug: Enable debug visualization
            method: 'auto', 'mss', or 'gdi'
        Returns: BGR format numpy array
        """
        w, h = self.w, self.h

        # Validate window handle
        if not win32gui.IsWindow(self.hwnd) or self.hwnd == win32gui.GetDesktopWindow():
            log("[INFO]", f"Window handle invalid (hwnd={self.hwnd}). Trying to find the window again...")
            self.find_window()
            if not self.hwnd or not win32gui.IsWindow(self.hwnd):
                self.get_window_size()
                log("[ERROR]", f"Window '{self.window_name}' not found or not accessible.")
                return np.zeros((h, w, 3), dtype=np.uint8)

        # Update window size and position (throttled)
        current_time = datetime.now().timestamp()
        if self.last_window_rect is None or current_time - self.last_check_time > 0.1:
            self.get_window_size()
            self.last_window_rect = win32gui.GetWindowRect(self.hwnd)
            self.last_check_time = current_time

        if w == 0 or h == 0:
            log("[WARNING]", f"The target window '{self.window_name}' has invalid dimensions (w={w}, h={h}).")
            return None

        # Try MSS first if available and not explicitly using GDI
        if MSS_AVAILABLE and method in ('auto', 'mss'):
            try:
                # Get the window bounds
                left, top, right, bottom = self.last_window_rect
                
                # Capture the region
                monitor = {"top": top, "left": left, "width": right - left, "height": bottom - top}
                screenshot = self.mss_instance.grab(monitor)
                
                # Convert to BGR format with minimal copying
                img = np.asarray(screenshot)  # Zero-copy operation
                
                # Crop to client area if needed
                client_rect = win32gui.GetClientRect(self.hwnd)
                client_pos = win32gui.ClientToScreen(self.hwnd, (0, 0))
                border_left = client_pos[0] - left
                border_top = client_pos[1] - top
                
                if border_top + h <= img.shape[0] and border_left + w <= img.shape[1]:
                    # Use view instead of copy when possible
                    img = img[border_top:border_top + h, border_left:border_left + w]
                    return self._convert_to_bgr_gpu(img)
                
            except Exception as e:
                if method == 'mss':
                    log("[ERROR]", f"MSS screenshot failed: {str(e)}")
                    return np.zeros((h, w, 3), dtype=np.uint8)

        # GDI method (fallback)
        try:
            hwndDC = win32gui.GetWindowDC(self.hwnd)
            srcDC = win32ui.CreateDCFromHandle(hwndDC)
            memDC = srcDC.CreateCompatibleDC()
            
            try:
                win_w = self.last_window_rect[2] - self.last_window_rect[0]
                win_h = self.last_window_rect[3] - self.last_window_rect[1]
                
                bmp = win32ui.CreateBitmap()
                bmp.CreateCompatibleBitmap(srcDC, win_w, win_h)
                memDC.SelectObject(bmp)

                result = ctypes.windll.user32.PrintWindow(self.hwnd, memDC.GetSafeHdc(), 0x2)

                if result == 1:
                    # Get bitmap data with minimal copying
                    bmp_str = bmp.GetBitmapBits(True)
                    img = np.frombuffer(bmp_str, dtype=np.uint8).reshape((win_h, win_w, 4))
                    
                    border_left = win32gui.GetClientRect(self.hwnd)[0]
                    border_top = win32gui.GetClientRect(self.hwnd)[1]
                    
                    if border_top + h <= img.shape[0] and border_left + w <= img.shape[1]:
                        img = img[border_top:border_top + h, border_left:border_left + w]
                        return self._convert_to_bgr_gpu(img)
                    else:
                        img = np.zeros((h, w, 3), dtype=np.uint8)
                else:
                    img = np.zeros((h, w, 3), dtype=np.uint8)
                    
            finally:
                memDC.DeleteDC()
                srcDC.DeleteDC()
                win32gui.ReleaseDC(self.hwnd, hwndDC)
                win32gui.DeleteObject(bmp.GetHandle())

        except Exception as e:
            log("[ERROR]", f"Screenshot capture failed: {str(e)}")
            img = np.zeros((h, w, 3), dtype=np.uint8)

        if debug and 'capture' in debug:
            cv2.imshow("Captured Window", img)
            cv2.waitKey(1)

        return img

    def __del__(self):
        """Cleanup GPU resources"""
        if hasattr(self, 'gpu_input_mat') and self.gpu_input_mat is not None:
            if self.gpu_backend == 'cuda':
                self.gpu_input_mat.release()
                self.gpu_output_mat.release()
                cv2.cuda.setBufferPoolUsage(False)

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
    