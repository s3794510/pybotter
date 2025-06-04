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
        self.w, self.h = 0, 0
        self.last_window_rect = None
        self.last_check_time = 0
        self.last_window_check = 0
        self.window_check_interval = 0.1  # How often to check window state (seconds)
        
        # Window state tracking
        self.is_valid = False
        self.is_minimized = False
        self.last_error = None
        
        # Initialize window handle
        self._update_window_state()
        
        # MSS setup
        self.mss_instance = mss.mss() if MSS_AVAILABLE else None
        
        # GPU setup with unified memory approach
        self.use_gpu = use_gpu
        self.gpu_backend = None
        self._setup_gpu(preferred_backend)
        
        # Pre-allocate reusable GPU memory if possible
        self.gpu_input_mat = None
        self.gpu_output_mat = None
        

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

    def _update_window_state(self):
        """Centralized window state update."""
        current_time = time()
        
        # Only check window state periodically
        if current_time - self.last_window_check < self.window_check_interval:
            return self.is_valid

        self.last_window_check = current_time
        
        try:
            # Find window if needed
            if not self.hwnd or not win32gui.IsWindow(self.hwnd):
                if self.window_name is None:
                    self.hwnd = win32gui.GetDesktopWindow()
                    log("[INFO]", "Using desktop window")
                else:
                    self.hwnd = win32gui.FindWindow(None, self.window_name)

            # Validate window
            if not self.hwnd or not win32gui.IsWindow(self.hwnd):
                if self.is_valid:  # Only log if state changed
                    log("[WARNING]", f"Lost connection to window '{self.window_name}'")
                self.is_valid = False
                self.hwnd = 0
                return False

            # Check if window is minimized
            placement = win32gui.GetWindowPlacement(self.hwnd)
            was_minimized = self.is_minimized
            self.is_minimized = placement[1] == win32con.SW_SHOWMINIMIZED
            
            if self.is_minimized != was_minimized:
                log("[INFO]", f"Window '{self.window_name}' {'minimized' if self.is_minimized else 'restored'}")

            # Update window size
            rect = win32gui.GetClientRect(self.hwnd)
            new_w = rect[2] - rect[0]
            new_h = rect[3] - rect[1]
            
            if new_w != self.w or new_h != self.h:
                self.w, self.h = new_w, new_h
                if self.w > 0 and self.h > 0:
                    log("[INFO]", f"Window size updated: {self.w}x{self.h}")

            # Update valid state
            was_valid = self.is_valid
            self.is_valid = True
            if not was_valid:  # Only log if state changed
                log("[INFO]", f"Connected to window '{self.window_name}' (handle: {self.hwnd})")

            return True

        except Exception as e:
            if str(e) != self.last_error:  # Only log if error changed
                log("[ERROR]", f"Window state update failed: {e}")
                self.last_error = str(e)
            self.is_valid = False
            self.hwnd = 0
            return False

    def get_screenshot(self, debug=False, method='auto'):
        """
        Capture a screenshot of the window using the specified method.
        Args:
            debug: Enable debug visualization
            method: 'auto', 'mss', or 'gdi'
        Returns: BGR format numpy array
        """
        # Update window state
        if not self._update_window_state():
            return np.zeros((self.h or 1, self.w or 1, 3), dtype=np.uint8)

        if self.is_minimized:
            return np.zeros((self.h, self.w, 3), dtype=np.uint8)

        # Get client area position relative to window
        try:
            # Get client area position relative to window
            client_rect = win32gui.GetClientRect(self.hwnd)  # Gets client area size
            client_pos = win32gui.ClientToScreen(self.hwnd, (0, 0))  # Get client area position in screen coordinates
            window_pos = win32gui.GetWindowRect(self.hwnd)  # Get window position in screen coordinates
            
            # Calculate border offsets
            border_left = client_pos[0] - window_pos[0]
            border_top = client_pos[1] - window_pos[1]

            # Try MSS first if available and not explicitly using GDI
            if MSS_AVAILABLE and method in ('auto', 'mss'):
                try:
                    # Get the window bounds
                    left, top, right, bottom = window_pos
                    
                    # Capture the region
                    monitor = {"top": top, "left": left, "width": right - left, "height": bottom - top}
                    screenshot = self.mss_instance.grab(monitor)
                    
                    # Convert to BGR format with minimal copying
                    img = np.asarray(screenshot)  # Zero-copy operation
                    
                    # Crop to client area
                    if border_top + self.h <= img.shape[0] and border_left + self.w <= img.shape[1]:
                        # Use view instead of copy when possible
                        img = img[border_top:border_top + self.h, border_left:border_left + self.w]
                        return self._convert_to_bgr_gpu(img)
                    
                except Exception as e:
                    if method == 'mss':
                        log("[ERROR]", f"MSS screenshot failed: {str(e)}")
                        return np.zeros((self.h, self.w, 3), dtype=np.uint8)

            # GDI method (fallback)
            try:
                hwndDC = win32gui.GetWindowDC(self.hwnd)
                srcDC = win32ui.CreateDCFromHandle(hwndDC)
                memDC = srcDC.CreateCompatibleDC()
                
                try:
                    win_w = window_pos[2] - window_pos[0]
                    win_h = window_pos[3] - window_pos[1]
                    
                    bmp = win32ui.CreateBitmap()
                    bmp.CreateCompatibleBitmap(srcDC, win_w, win_h)
                    memDC.SelectObject(bmp)

                    result = ctypes.windll.user32.PrintWindow(self.hwnd, memDC.GetSafeHdc(), 0x2)

                    if result == 1:
                        # Get bitmap data with minimal copying
                        bmp_str = bmp.GetBitmapBits(True)
                        img = np.frombuffer(bmp_str, dtype=np.uint8).reshape((win_h, win_w, 4))
                        
                        # Crop to client area
                        if border_top + self.h <= img.shape[0] and border_left + self.w <= img.shape[1]:
                            img = img[border_top:border_top + self.h, border_left:border_left + self.w]
                            return self._convert_to_bgr_gpu(img)
                        else:
                            img = np.zeros((self.h, self.w, 3), dtype=np.uint8)
                    else:
                        img = np.zeros((self.h, self.w, 3), dtype=np.uint8)
                        
                finally:
                    memDC.DeleteDC()
                    srcDC.DeleteDC()
                    win32gui.ReleaseDC(self.hwnd, hwndDC)
                    win32gui.DeleteObject(bmp.GetHandle())

            except Exception as e:
                log("[ERROR]", f"Screenshot capture failed: {str(e)}")
                img = np.zeros((self.h, self.w, 3), dtype=np.uint8)

            if debug:
                cv2.imshow("Captured Window", img)
                cv2.waitKey(1)

            return img

        except Exception as e:
            log("[ERROR]", f"Screenshot capture failed: {str(e)}")
            return np.zeros((self.h or 1, self.w or 1, 3), dtype=np.uint8)

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
    