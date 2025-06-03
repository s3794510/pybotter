from .bothandler import BotHandler
from .windowhandler import WindowHandler
import winsound, threading
from .utils import *
from ctypes import windll
from time import sleep, time

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
        self.sleep_time = sleep_time
        self.interval = interval

        # Central pause switch
        self.pause_switch = threading.Event()
        self.pause_switch.set()  # Start unpaused

        # Create handlers
        self.bothandler = BotHandler(window_name, self.debug, mode = mode, interval = interval, pause_switch = self.pause_switch)
        self.alarm_lock = threading.Lock()
        
        log("INFO", f"Object PyBot created, Window name: {self.window_name}")
        log("INFO", f"RUNNING MODE: {self.mode}, SLEEP TIME: {self.sleep_time}s, INTERVAL: {self.interval}, DEBUG MODE: {self.debug}")

    def mainloop(self, function_configs):
        """
        Run multiple functions in separate threads.
        
        Args:
            function_configs: list of tuples (function, thread_count)
            Example: [(function1, 2), (function2, 1)] - runs function1 in 2 threads and function2 in 1 thread
        """
        # Before Main Loop
        self._before_mainloop()

        # Create and start threads
        threads = []
        thread_functions = {}  # Keep track of which function each thread is running

        for func, thread_count in function_configs:
            func_name = func.__name__  # Get the function name
            for thread_num in range(thread_count):
                # Create thread name: function_name_N (where N is the thread number if there are multiple)
                thread_name = f"{func_name}" if thread_count == 1 else f"{func_name}_{thread_num + 1}"
                thread = threading.Thread(
                    target=self._thread_loop,
                    args=(func,),
                    daemon=True,
                    name=thread_name
                )
                threads.append(thread)
                thread_functions[thread] = (func, thread_count)
                thread.start()
                log("INFO", f"Started thread: {thread_name}")

        # Wait for threads to complete or program to exit
        try:
            while self.bothandler.is_running:
                # Check if any thread has died unexpectedly
                alive_threads = [t for t in threads if t.is_alive()]
                if len(alive_threads) < len(threads):
                    log("WARNING", "Some bot threads have died unexpectedly")
                    # Restart dead threads with their original functions
                    dead_threads = set(threads) - set(alive_threads)
                    for dead_thread in dead_threads:
                        func, thread_count = thread_functions[dead_thread]
                        # Recreate thread with same name
                        new_thread = threading.Thread(
                            target=self._thread_loop,
                            args=(func,),
                            daemon=True,
                            name=dead_thread.name
                        )
                        alive_threads.append(new_thread)
                        thread_functions[new_thread] = thread_functions[dead_thread]
                        new_thread.start()
                        log("INFO", f"Restarted thread: {new_thread.name}")
                    threads = alive_threads
                sleep(1)  # Check thread status every second
        except KeyboardInterrupt:
            log("INFO", "Received keyboard interrupt, stopping threads...")
            self.bothandler.is_running = False

        # After Main Loop, End Task
        self._after_mainloop()
        return 0

    def _thread_loop(self, actions):
        """Individual thread loop that runs the bot actions"""
        while self.bothandler.is_running:
            try:
                # Pause handling
                if not self.bothandler.is_pause:
                    # Put the actions (mouse/keyboard) inside function actions in this class
                    actions()

                # handling after each cycle
                self.bothandler.flow_handle(sleep_time=self.sleep_time)
            except Exception as e:
                log("ERROR", f"Thread error: {str(e)}")
                sleep(1)  # Prevent rapid error loops

    def _keep_awake(self):
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)

    def _before_mainloop(self):
        # Start updating screenshots of target window
        self.bothandler.start_screenshot_updater(self.interval)
        # Wait for first screenshot to be captured
        start_time = time()
        while self.bothandler.haystack is None:
            if time() - start_time > 5:
                log("[WARNING]", "Timeout: Failed to capture initial screenshot within 5 seconds")
                break
            sleep(0.1)  # Avoid CPU overuse

        # Set the computer to keep being awake
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
        """
        Running the main loop
        """
        while(self.bothandler.is_running):   

            # Pause handling
            if not self.bothandler.is_pause:
                # Put the actions (mouse/keyboard) inside function actions in this class
                actions()

            # hanlding after each cycle
            self.bothandler.flow_handle(sleep_time = self.sleep_time, debug = self.debug)
        self._after_mainloop()
        return 0
    
    def _after_mainloop(self):
        """
        Closing the program
        """
        log(message="Closing the program")
        self.bothandler.destroyAllWindows()
        sleep(1)
        return 0

    def variables(self, func):
        """
        Decorator to add variables to the bot
        """
        def run(*args, **kwargs):
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
    
    def update_screenshot(self):
        self.bothandler.update_screenshot()
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
    
    def play_alarm(self, mode=0):
        """
        Play an alarm sound with different modes:
        0: Default - Triple beep sequence
        1: Single beep - Quick notification
        2: Warning - Ascending tone sequence
        3: Alert - High-pitched urgent sequence
        4: Success - Pleasant ascending melody
        5: Error - Descending error tone
        """
        self.bothandler.soundhandler.play_alarm(mode)
    
    def wait(self, duration):
        sleep(duration)

    def save_current_screenshot_PNG(self, filename=None):
        self.bothandler.save_current_screenshot(filename)