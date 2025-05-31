from .bothandler import BotHandler
from .windowhandler import WindowHandler
import winsound, time, threading
from .utils import *
from ctypes import windll

@creation_log
class PyBot:
    
    def __init__(self, window_name, sleeptime = 0, mode = None, debug = None, interval = 1):
        '''
        window_name (str): name of the target window
        sleeptime (int): amount of seconds wait after each cycle
        debug: debug mode
        '''
        if not debug:
            self.debug = ''
        else:
            self.debug = debug
        self.mode = mode
        self.window_name = window_name
        self.sleeptime = sleeptime
        self.interval = interval

        # Central pause switch
        self.pause_switch = threading.Event()
        self.pause_switch.set()  # Start unpaused

        # Create handlers
        self.bothandler = BotHandler(window_name, self.debug, mode = mode, interval = interval, pause_switch = self.pause_switch)
        self.alarm_lock = threading.Lock()
        
        log("INFO", f"Object PyBot created, Window name: {self.window_name}")
        log("INFO", f"RUNNING MODE: {self.mode}, SLEEP TIME: {self.sleeptime}s, INTERVAL: {self.interval}, DEBUG MODE: {self.debug}")

    def mainloop(self, func):
        def run():
            # Before Main Loop
            self._before_mainloop()

            # Run the bot (Main Loop)
            return_code = self._runmainloop(func)

            # After Main Loop, End Task
            log("INFO", "Program is closed.")
            return return_code
        return run
    
    def _keep_awake(self):
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)

    def _before_mainloop(self):
        # Start updating screenshots of target window
        self.bothandler.start_screenshot_updater(self.interval)
        start_time = time.time()
        while self.bothandler.haystack is None:
            if time.time() - start_time > 5:
                log("ERROR", "Timeout: self.bothandler.haystack did not update within 5 seconds")
                #raise TimeoutError("Timeout: self.bothandler.haystack did not update within 5 seconds.")
            time.sleep(0.1)  # Avoid CPU overuse

        # Set the cimputer to sleep
        if self.mode:
            if 'awake' in self.mode:
                self._keep_awake()
                log("INFO", "Keeping the PC awake.")

        # Start program text
        print("""Hold Ctrl + ESC to stop
        Hold Ctrl + P to pause/unpause.
        Hold Ctrl + F to show FPS
        Program is running.
        """)

    def _runmainloop(self, actions):
        while(self.bothandler.is_running):   

            # Pause handling
            if not self.bothandler.is_pause:
                # Put the actions (mouse/keyboard) inside function actions in this class
                actions()

            # hanlding after each cycle
            self.bothandler.flow_handle(sleep_time = self.sleeptime, debug = self.debug)
        log(message="Closing the program")
        self.bothandler.destroyAllWindows()
        return 0

    def variables(self, func):
        def run(*args, **kwargs):
            #self.bothandler.init()
            return_code = func(*args, **kwargs)
            return return_code
        return run

##############################################
# WINDOW HANDLING
##############################################
    def list_windows():
        return WindowHandler.list_window_titles()

    def add_image(self, name, path):
        return self.bothandler.add_image(name, path)

    def find_image(self, name, threshold = 0.5, convert=None):
        "convert method = COLOR_BGR2GRAY"
        return self.bothandler.find_image(name, threshold,convert=convert)

    def show_window(self):
        self.bothandler.show_screenshot()
    
    def update_screenshot(self, debug = ''):
        self.bothandler.update_screenshot(debug = '')
###############################################
# INPUT HANDLING
###############################################
    def left_click(self, x = None, y = None, duration = 0, mode= "default"):
        if mode == "interception" or mode == "i":
            self.bothandler.interception_click(x, y, duration)
        else:
            self.bothandler.leftclick(duration=duration)

    def key_press(self, key, duration):
        return self.bothandler.keyboard_press(key, duration)
    
    def mouse_move(self, x, y, duration, mode= "default"):
        if mode == "":
            pass
        else:
            self.bothandler.move_mouse_sendinput(x, y, duration)


###############################################
# UTILITIES
###############################################
    def resize(self, x, y):
        return self.bothandler.resize(x, y)
    
    def play_alarm(self, mode = 0):
        def alarm_sound():
            if not self.alarm_lock.acquire(blocking=False):
                return  # Exit if another alarm is already running
            
            try:
                if mode == 1:
                    alarm_sequence =[(1000, 50)]
                else:
                    alarm_sequence = [
                        (1000, 50),
                        (1200, 50),
                        (1500, 50),
                        (1000, 50),
                        (1200, 50),
                        (1500, 50)
                    ]
                for freq, dur in alarm_sequence:
                    winsound.Beep(freq, dur)
                    time.sleep(0.1)
            finally:
                self.alarm_lock.release()  # Ensure lock is released

        threading.Thread(target=alarm_sound, daemon=True).start()
    
    def wait(self, duration):
        time.sleep(duration)

    def save_current_screenshot_PNG(self, filename=None):
        self.bothandler.save_current_screenshot(filename)