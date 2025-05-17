from typing import Tuple
import  win32gui, win32api, win32con, sched, threading
from time import time, sleep
import keyboard, cv2, os
from .vision import Vision
from .windowhandler import WindowHandler
from .soundhandler import SoundHandler
import ctypes
from datetime import datetime
import ctypes
import time
from .utils import *

@creation_log
class BotHandler:
    
    #################################################
    #################################################
    # http://www.kbdedit.com/manual/low_level_vk_list.html
    keymap = {
    '0': 0x30,
    '1': 0x31,
    '2': 0x32,
    '3': 0x33,
    '''
    VK_KEY_4	0x34 ('4')	4
    VK_KEY_5	0x35 ('5')	5
    VK_KEY_6	0x36 ('6')	6
    VK_KEY_7	0x37 ('7')	7
    VK_KEY_8	0x38 ('8')	8
    VK_KEY_9	0x39 ('9')	9
    VK_KEY_A	0x41 ('A')	A
    VK_KEY_B	0x42 ('B')	B
    VK_KEY_C	0x43 ('C')	C
    VK_KEY_D	0x44 ('D')	D
    VK_KEY_E	0x45 ('E')	E
    VK_KEY_F	0x46 ('F')	F
    VK_KEY_G	0x47 ('G')	G
    VK_KEY_H	0x48 ('H')	H
    VK_KEY_I	0x49 ('I')	I
    VK_KEY_J	0x4A ('J')	J
    VK_KEY_K	0x4B ('K')	K
    VK_KEY_L	0x4C ('L')	L
    VK_KEY_M	0x4D ('M')	M
    VK_KEY_N	0x4E ('N')	N
    VK_KEY_O	0x4F ('O')	O
    VK_KEY_P	0x50 ('P')	P
    VK_KEY_Q	0x51 ('Q')	Q
    VK_KEY_R	0x52 ('R')	R
    VK_KEY_S	0x53 ('S')	S
    VK_KEY_T	0x54 ('T')	T
    VK_KEY_U	0x55 ('U')	U
    ''':0,
    'U': 0x57,
    'V': 0x56,
    'W': 0x57,
    'X': 0x58,
    'Y': 0x59,
    'Z': 0x5A 
    }
   
    
    def __init__(self, window_name, debug = None, mute = None, mode = None) -> None:
       
        # MAIN FIELDS
        self.window_name = window_name
        self.soundpath = os.path.join(os.path.dirname(__file__),'sound')
        self.hwnd = None
        self.get_window_handle()
        self.s = sched.scheduler(time, sleep)
        self.window_handler = WindowHandler(self.window_name)
        self.soundhandler = SoundHandler(self.soundpath)
        self.is_running = True
        self.is_pause = False
        self.loop_time = time.time()
        self.fps = -1
        self.screenshot = None
        self.debug = debug
        self.images = {str:Vision}
        
        # SPECIAL MODE INTERCEPTION
        if mode and "in" in mode:
            self.im = self.InterceptionMouse(hold_duration=0.05)
            self._exit_key_combos = [['esc', 'control'], ['ctrl', 'space']]
        else:
            self._exit_key_combos = [['esc', 'control']]

        # INIT THREADS
        self.pause_handle_thread()
        self.exit_handle_thread(self._exit_key_combos)
        self.show_fps_handle_thread()

        self.soundhandler.sound_start()

    def get_window_handle(self):
        if self.window_name is None:
            self.hwnd = win32gui.GetDesktopWindow()
        else:
            self.hwnd = win32gui.FindWindow(None, self.window_name)
            # if not self.hwnd:
            #     raise Exception('Window not found: {}'.format(self.window_name))

    @staticmethod
    def check_file_exist(path):
        if not os.path.isfile(path):
            raise Exception("Path or file not found")
        return True

    def check_needle_fit_haystack(self, needle_name):
        needle = self.images.get(needle_name)
        if (needle.needle_h > self.window_handler.h) or (needle.needle_w > self.window_handler.w) :
            log("[WARNING]",  f"Needle image is bigger than the target window. needle_w = {needle.needle_w} | window_w = {self.window_handler.w} | needle_h = {needle.needle_h} | window_h = {self.window_handler.h}")
        return True

    def add_image(self, name, path):
        if self.images.get(name) != None:
            raise Exception("Needle image name already existed")
        if self.check_file_exist(path):
            self.images.update({name:Vision(path)})
            if self.images.get(name) == None:
                raise Exception("Needle image returns a NULL value")
            return self.images.get(name)

        raise Exception("Unexpected Error")

    def find_image(self, name, threshold, convert = None):
        "convert method = COLOR_BGR2GRAY"
        needle = self.images.get(name)
        typeneedle = type(needle)
        if typeneedle is not Vision:
            raise(Exception("Needle image not found, actual Type:",typeneedle))
        if self.check_needle_fit_haystack(name): 
            return needle.find(self.screenshot, threshold, convert_mode= convert,debug_mode=self.debug)
        raise Exception("UNEXPECTED ERROR")

    def keyboard_press(self, key, duration):
        keycode = self.keymap.get(key.upper())
        win32api.PostMessage(self.hwnd, win32con.WM_KEYDOWN, keycode, 0)
        sleep(duration + 0.1)
        win32api.PostMessage(self.hwnd, win32con.WM_KEYUP, keycode, 0)
        return 0

    def leftclick(self, x, y, duration=0.1):
        pass


    def flow_handle(self, sleep_time = 0, debug = 'regular'):
        sleep(sleep_time)
        while self.is_pause:
            sleep(0.05)
        # press 'q' with the output window focused to exit.
        # waits 1 ms every loop to process key presses
        if cv2.waitKey(1) == ord('q'):
            self.exit()
        # calcualte times processed each second
        self.fps = 1 / (time.time() - self.loop_time)
        self.loop_time = time.time()


    # def init(self):
    #     self.soundhandler.sound_start()
    #     # init threads
    #     self.pause_handle_thread()
    #     self._exit_key_combos = [['esc', 'control'], ['ctrl', 'space']]
    #     self.exit_handle_thread(self._exit_key_combos)
    #     self.show_fps_handle_thread()

        # initialize the Vision class
        #self.area_img = Vision('areasxx.jpg')
        #self.teleport_img = Vision('teleport.jpg')

    def resize(self, x, y):
        return self.window_handler.window_resize(x, y)

    def destroyAllWindows(self):
        cv2.destroyAllWindows()
        return 0

##############################
    def pause(self):
        self.is_pause = True
        print("Paused.\n")
        self.soundhandler.sound_pause()

    def unpause(self):
        self.is_pause = False
        print("Continued.\n")
        self.soundhandler.sound_unpause()
        pass

    def pause_handle_thread(self):
        thread = threading.Thread(target=self.pause_handle, args=())
        thread.start()

    def pause_handle(self, sleep_time = 0.05):
        done = True
        while self.is_running:
            sleep(sleep_time)
            if done:
                if not self.is_pause and keyboard.is_pressed('p') and keyboard.is_pressed('control'):
                    done = False
                    self.pause()
                    sleep(0.5)
                    done = True
                    
            if done:
                if self.is_pause and keyboard.is_pressed('p') and keyboard.is_pressed('control'):   
                    done = False   
                    self.unpause()
                    sleep(0.5)
                    done = True
                    
##############################
    def exit_handle_thread(self, key_combinations):
        """
        Starts a thread to watch for any of the key combinations.
        """
        self._exit_key_combos = [set(combo) for combo in key_combinations]
        self.is_running = True
        thread = threading.Thread(target=self.exit_handle, daemon=True)
        thread.start()

    def exit_handle(self):
        """
        Monitors key combinations and exits when any of them is detected.
        """
        while self.is_running:
            for combo in self._exit_key_combos:
                if all(keyboard.is_pressed(key) for key in combo):
                    self.exit()

    def exit(self):
        self.is_running = False
        self.soundhandler.sound_exit()
        pass

#####################################
    def show_fps_handle_thread(self):
        thread = threading.Thread(target=self.show_fps_handle, args= ()) 
        thread.start()

    def show_fps_handle(self, sleep_time = 0.1):
        while self.is_running:
            sleep(sleep_time)
            if keyboard.is_pressed('f') and keyboard.is_pressed('control'):
                print(f"FPS: {self.fps}")
                print("Threads: ", threading.active_count())
                sleep(1)

#####################################
    def update_screenshot(self, debug = None):
        self.screenshot = self.window_handler.get_screenshot(debug)
        
    def save_current_screenshot(self, filename=None):
        """
        Saves the current screenshot stored in self.screenshot to a file.
        """
        if self.screenshot is None:
            log("[ERROR]", "No screenshot to save.")
            return

        # Ensure a proper filename
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'screenshot_{timestamp}.png'
        elif not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            filename += '.png'

        # Save path in 'screenshots' folder next to script
        save_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, filename)

        try:
            success = cv2.imwrite(save_path, self.screenshot)
            if success:
                log("[ERROR]", "Screenshot saved to {save_path}")
            else:
                log("[ERROR]", "cv2.imwrite failed to save the file.")
        except Exception as e:
            log("[ERROR]", f"Failed to save screenshot: {e}")

    def interception_click(self, x=None, y=None, duration=0):
        """
        If x and y are given: move by (x,y) relative to current cursor.
        Then perform a left-click, holding for `duration` seconds.
        """
        # optional relative move
        self.im.click_at(self.hwnd, x=x,y=y,duration = 0.1)

    def keep_awake(self):
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)

        while True:
            time.sleep(30)  # Still needs a loop to hold the execution state

    def start_keep_awake_thread(self):
        t = threading.Thread(target=self.keep_awake, daemon=True)
        t.start()

    #############################
    #############################  
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

        def click_at(self, hwnd, x, y, duration: float = None):
            cx, cy = win32gui.ScreenToClient(hwnd, (x, y))
            lparam = win32api.MAKELONG(cx, cy)
            win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
            win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
            time.sleep(duration if duration is not None else self.hold_duration)
            win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

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

############################
@creation_log
class PropagatingThread(threading.Thread):
    def run(self):
        self.exc = None
        try:
            if hasattr(self, '_Thread__target'):
                # Thread uses name mangling prior to Python 3.
                self.ret = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)
            else:
                self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self, timeout=None):
        super(PropagatingThread, self).join(timeout)
        if self.exc:
            raise self.exc
        return self.ret