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
from .utils import *
from .virtual_inputs import *

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
   
    
    def __init__(self, window_name, debug = None, mute = None, mode = None, interval = 1, pause_switch = None, rate_limit = None, on_screenshot = None) -> None:
       
        # MAIN FIELDS
        self.window_name = window_name
        self.soundpath = os.path.join(os.path.dirname(__file__),'sound')
        self.hwnd = None
        self.is_running = True  # Keep running while waiting for window
        self.is_window_ready = False  # New flag to track window state
        
        # Try to find the window first
        self.get_window_handle()
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            log("[WARNING]", f"Window '{window_name}' not found initially. Will keep trying...")
        else:
            self.is_window_ready = True
            
        # Continue with initialization
        self.s = sched.scheduler(time, sleep)
        self.window_handler = WindowHandler(self.window_name)
        self.soundhandler = SoundHandler(self.soundpath)
        self.is_pause = False
        self.on_screenshot = on_screenshot
        
        # Performance monitoring
        self.perf_tracker = PerformanceTracker()
        self.bot_monitor = self.perf_tracker.get_monitor("Bot Logic")
        self.capture_monitor = self.perf_tracker.get_monitor("Screen Capture")
        
        self.haystack = None
        self.debug = debug
        self.needle_handlers = {str:Vision}
        self.interval = interval
        self.target_rate = 1/interval if interval else None
        self.keywait = 0.1
        self.pause_switch = pause_switch
        if self.pause_switch is None:
            log("[WARNING]", "Pause switch is not defined, pausing might not work correctly")
        
        # Rate control parameters
        self.rate_error_sum = 0
        self.last_rate_error = 0
        self.kp = 0.02  # Reduced from 0.1
        self.ki = 0.001  # Reduced from 0.01
        self.kd = 0.005  # Reduced from 0.05
        self._current_interval = interval
        self._interval_lock = threading.Lock()
        self._rate_samples = []
        self._max_samples = 10  # Number of samples for moving average
        
        # SPECIAL MODE INTERCEPTION
        if mode and "in" in mode:
            self.im = InterceptionMouse(hold_duration=0.05)
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
        needle = self.needle_handlers.get(needle_name)
        if (needle.needle_h > self.window_handler.h) or (needle.needle_w > self.window_handler.w) :
            log("[WARNING]",  f"Needle image is bigger than the target window. needle_w = {needle.needle_w} | window_w = {self.window_handler.w} | needle_h = {needle.needle_h} | window_h = {self.window_handler.h}")
        return True

    def add_image(self, name, path):
        if self.needle_handlers.get(name) != None:
            raise Exception("Needle image name already existed")
        if self.check_file_exist(path):
            self.needle_handlers.update({name:Vision(path, name = name)})
            if self.needle_handlers.get(name) == None:
                raise Exception("Needle image returns a NULL value")
            return self.needle_handlers.get(name)

        raise Exception("Unexpected Error")

    def find_image(self, name, threshold, convert = None):
        "convert method = COLOR_BGR2GRAY"
        needle = self.needle_handlers.get(name)
        # typeneedle = type(needle)
        # if typeneedle is not Vision:
        #     raise(Exception("Needle image not found, actual Type:",typeneedle))
        # if self.check_needle_fit_haystack(name): 
        return needle.find(self.haystack, threshold, convert_mode= convert,debug=self.debug)
        raise Exception("UNEXPECTED ERROR")

    def keyboard_press(self, key, duration):
        keycode = self.keymap.get(key.upper())
        win32api.PostMessage(self.hwnd, win32con.WM_KEYDOWN, keycode, 0)
        sleep(duration + 0.1)
        win32api.PostMessage(self.hwnd, win32con.WM_KEYUP, keycode, 0)
        return 0

    def leftclick(self, x=None, y=None, duration=0.1):
        """Perform a left click with window handle validation."""
        # Don't try to click if window isn't ready
        if not self.is_window_ready:
            log("[WARNING]", "Cannot click - waiting for window to be ready")
            return False
            
        if not win32gui.IsWindow(self.hwnd) or self.hwnd == 0:
            log("[WARNING]", "Window handle invalid, attempting to recover...")
            self.get_window_handle()
            if not win32gui.IsWindow(self.hwnd):
                log("[ERROR]", f"Failed to recover window handle for '{self.window_name}'")
                self.is_window_ready = False
                return False

        # If x and y are not provided, click at current cursor position
        if x is None or y is None:
            # Try the click operation
            success = SendInputMouse.click_at_current_to_window(self.hwnd, duration)
            if not success:
                # If click failed, try to recover window handle and retry once
                self.get_window_handle()
                if win32gui.IsWindow(self.hwnd):
                    return SendInputMouse.click_at_current_to_window(self.hwnd, duration)
            return success
        ## NOT DEFINED YET
        # If x and y are provided, click at the specified position
        else:
            #success = SendInputMouse.click_at_to_window(self.hwnd, x, y, duration)
            if not success:
                # If click failed, try to recover window handle and retry once
                self.get_window_handle()
                if win32gui.IsWindow(self.hwnd):
                    return SendInputMouse.click_at_current_to_window(self.hwnd, duration)
            return success

    def flow_handle(self, sleep_time = 0):
        sleep(sleep_time)
        # Pause handling
        if self.pause_switch:
            self.pause_switch.wait()  # Respect global pause
        while self.is_pause:
            sleep(0.05)
        # press 'q' with the output window focused to exit.
        # waits 1 ms every loop to process key presses
        if cv2.waitKey(1) == ord('q'):
            self.exit()
            
        # Update bot logic FPS
        self.bot_monitor.update()



    def resize(self, x, y):
        return self.window_handler.window_resize(x, y)

    def destroyAllWindows(self):
        cv2.destroyAllWindows()
        return 0

##############################
    def pause(self):
        self.is_pause = True
        if self.pause_switch:
            self.pause_switch.clear()
        print("\n⏸️  Program Paused")
        self.soundhandler.sound_pause()

    def unpause(self):
        self.is_pause = False
        if self.pause_switch:
            self.pause_switch.set()
        print("\n⏩  Program Resumed")
        self.soundhandler.sound_unpause()
        pass

    def pause_handle_thread(self):
        thread = threading.Thread(target=self.pause_handle, daemon=True)
        thread.start()

    def pause_handle(self):
        key_combos = [
            lambda: keyboard.is_pressed('control') and keyboard.is_pressed('p'),
            lambda: keyboard.is_pressed('control') and keyboard.is_pressed('caps lock'),
        ]
        last_trigger_time = 0
        debounce_interval = 1  # seconds

        while self.is_running:
            if any(combo() for combo in key_combos):
                now = time()
                if now - last_trigger_time >= debounce_interval:
                    if self.is_pause:
                        self.unpause()
                    else:
                        self.pause()
                    last_trigger_time = now

            sleep(self.keywait)
                    
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
            sleep(self.keywait)

    def exit(self):
        self.is_running = False
        # Unpause program
        self.is_pause = False
        self.pause_switch.set()
        print("\n⛔ Program Stopped")
        self.soundhandler.sound_exit()
        pass

#####################################
    def show_fps_handle_thread(self):
        thread = threading.Thread(target=self.show_fps_handle, args=(), daemon=True) 
        thread.start()

    def show_fps_handle(self):
        last_trigger_time = 0
        debounce_interval = 0.5  # seconds

        while self.is_running:
            if self.pause_switch:
                self.pause_switch.wait()  # Respect global pause
            
            # Check for Ctrl+F
            if keyboard.is_pressed('f') and keyboard.is_pressed('control'):
                current_time = time()
                if current_time - last_trigger_time >= debounce_interval:
                    print("\n📊 Performance Statistics:")
                    print("="*30)
                    print_performance_stats()  # Use the new universal stats printer
                    print("="*30 + "\n")
                    last_trigger_time = current_time
            
            sleep(self.keywait)

#####################################
    def update_screenshot(self, debug = ''):
        self.haystack = self.window_handler.get_screenshot(debug)
        # Update screen capture FPS
        self.capture_monitor.update()
        # Call screenshot callback if exists
        if self.on_screenshot:
            self.on_screenshot()

    def _get_current_interval(self):
        with self._interval_lock:
            return self._current_interval

    def _set_current_interval(self, value):
        with self._interval_lock:
            self._current_interval = value

    def _get_smoothed_rate(self):
        """Get smoothed rate using moving average"""
        current_rate = self.capture_monitor.cycles_per_sec
        self._rate_samples.append(current_rate)
        if len(self._rate_samples) > self._max_samples:
            self._rate_samples.pop(0)
        return sum(self._rate_samples) / len(self._rate_samples)

    def adjust_interval(self):
        """Dynamically adjust interval using PID control"""
        if not self.target_rate:
            return self._get_current_interval()
            
        current_rate = self._get_smoothed_rate()
        error = self.target_rate - current_rate
        
        # PID control with gentler adjustments
        self.rate_error_sum = max(-5, min(5, self.rate_error_sum + error))  # Reduced anti-windup range
        derivative = error - self.last_rate_error
        
        adjustment = (
            self.kp * error +  # Proportional term
            self.ki * self.rate_error_sum +  # Integral term
            self.kd * derivative  # Derivative term
        )
        
        # Limit maximum adjustment per cycle
        adjustment = max(-0.1, min(0.1, adjustment))
        
        # Update for next iteration
        self.last_rate_error = error
        
        # Adjust interval (with limits)
        current = self._get_current_interval()
        new_interval = max(0.001, min(1.0, current * (1 - adjustment)))
        
        # Smooth the transition
        new_interval = current * 0.8 + new_interval * 0.2
        
        self._set_current_interval(new_interval)
        return new_interval

    def rate_control_thread(self):
        """Thread for rate control"""
        while self.is_running:
            if not self.is_pause and self.target_rate:
                self.adjust_interval()
            sleep(0.2)  # Reduced update frequency to every 200ms

    def start_screenshot_updater(self, interval=1.0):
        """Start a background thread to update the screenshot at regular intervals."""
        log(message="Starting screenshot updater thread")
        
        # Start rate control thread
        if self.target_rate:
            threading.Thread(target=self.rate_control_thread, daemon=True).start()
            log(message=f"Started rate control thread with target rate: {self.target_rate:.1f} Hz")

        def screenshot_updater():
            retry_interval = 1.0  # Time between window check attempts
            last_retry = 0
            
            while self.is_running:
                current_time = time()
                
                # If window is not ready, try to find it
                if not self.is_window_ready:
                    if current_time - last_retry >= retry_interval:
                        self.get_window_handle()
                        if self.hwnd and win32gui.IsWindow(self.hwnd):
                            log("[INFO]", f"Found window '{self.window_name}'")
                            self.is_window_ready = True
                        else:
                            log("[INFO]", f"Still waiting for window '{self.window_name}'...")
                        last_retry = current_time
                    sleep(0.1)  # Short sleep while waiting
                    continue
                
                # Check if window is still valid
                if not win32gui.IsWindow(self.hwnd):
                    log("[WARNING]", f"Lost connection to window '{self.window_name}'. Will try to reconnect...")
                    self.is_window_ready = False
                    continue
                
                # Normal screenshot update when window is ready
                if self.pause_switch:
                    self.pause_switch.wait()  # Respect global pause
                self.update_screenshot(self.debug)
                sleep(self._get_current_interval())

        # Start the screenshot updater thread
        threading.Thread(target=screenshot_updater, daemon=True).start()
        return True

    def save_current_screenshot(self, filename=None):
        """
        Saves the current screenshot stored in self.screenshot to a file.
        """
        if self.haystack is None:
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
            success = cv2.imwrite(save_path, self.haystack)
            if success:
                log("[ERROR]", "Screenshot saved to {save_path}")
            else:
                log("[ERROR]", "cv2.imwrite failed to save the file.")
        except Exception as e:
            log("[ERROR]", f"Failed to save screenshot: {e}")


#####################################
    def move_mouse_sendinput(self, target_x, target_y, duration=0):
        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)

        def normalize(x, y):
            return int(x * 65535 / screen_w), int(y * 65535 / screen_h)

        # Convert client (window) coords to screen coords
        point = ctypes.wintypes.POINT(target_x, target_y)
        ctypes.windll.user32.ClientToScreen(self.hwnd, ctypes.byref(point))
        target_x, target_y = point.x, point.y

        # Get current cursor position
        pt = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        start_x, start_y = pt.x, pt.y

        steps = int(duration * 60) if duration > 0 else 1

        for i in range(steps + 1):
            t = i / steps if steps > 0 else 1
            x = int(start_x + (target_x - start_x) * t)
            y = int(start_y + (target_y - start_y) * t)
            nx, ny = normalize(x, y)

            mi = MOUSEINPUT(
                dx=nx,
                dy=ny,
                mouseData=0,
                dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
                time=0,
                dwExtraInfo=None
            )
            inp = INPUT(type=INPUT_MOUSE, mi=mi)
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

            if duration > 0:
                sleep(duration / steps)

    def interception_click(self, x=None, y=None, duration=0):
        """
        If x and y are given: move by (x,y) relative to current cursor.
        Then perform a left-click, holding for `duration` seconds.
        """
        # optional relative move
        self.im.click_at(self.hwnd, x=x,y=y,duration = 0.1)

    # def keep_awake(self):
    #     ES_CONTINUOUS = 0x80000000
    #     ES_SYSTEM_REQUIRED = 0x00000001
    #     ES_DISPLAY_REQUIRED = 0x00000002
    #     ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)

    #     while True:
    #         sleep(30)  # Still needs a loop to hold the execution state

    # def start_keep_awake_thread(self):
    #     t = threading.Thread(target=self.keep_awake, daemon=True)
    #     t.start()

    #############################
    #############################  
    

############################

############################
# @creation_log
# class PropagatingThread(threading.Thread):
#     def run(self):
#         self.exc = None
#         try:
#             if hasattr(self, '_Thread__target'):
#                 # Thread uses name mangling prior to Python 3.
#                 self.ret = self._Thread__target(*self._Thread__args, **self._Thread__kwargs)
#             else:
#                 self.ret = self._target(*self._args, **self._kwargs)
#         except BaseException as e:
#             self.exc = e

#     def join(self, timeout=None):
#         super(PropagatingThread, self).join(timeout)
#         if self.exc:
#             raise self.exc
#         return self.ret

