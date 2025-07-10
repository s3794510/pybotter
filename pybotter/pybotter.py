from .bothandler import BotHandler
from .windowhandler import WindowHandler
import threading
from .utils import *
from ctypes import windll
from time import sleep, time
import cv2

@creation_log
class PyBot:
    
    def __init__(self, window_name, sleep_time = 0, mode = None, debug = None, interval = 1, rate_limit = None):
        '''
        window_name (str): name of the target window
        sleeptime (int): amount of seconds wait after each cycle
        debug: debug mode
        interval: interval between screenshot captures (deprecated, use rate_limit instead)
        rate_limit: maximum number of operations per second (e.g. 30 for 30 fps)
        '''
        self.debug = debug
        self.mode = mode
        self.window_name = window_name
        self.sleep_time = sleep_time
        self.interval = 1/rate_limit if rate_limit else interval
        self.rate_limit = rate_limit
        self.screenshot_synced_functions = []
        self._sync_functions_running = {}
        self._sync_lock = threading.Lock()

        # Central pause switch
        self.pause_switch = threading.Event()
        self.pause_switch.set()  # Start unpaused

        # Create handlers
        self.bothandler = BotHandler(window_name, self.debug, mode = mode, interval = self.interval, 
                                   pause_switch = self.pause_switch, rate_limit = self.rate_limit,
                                   on_screenshot=self._run_synced_functions)
        self.alarm_lock = threading.Lock()
        
        log("INFO", f"Object PyBot created, Window name: {self.window_name}")
        log("INFO", f"RUNNING MODE: '{self.mode}', DEBUG MODE: {self.debug}")
        log("INFO", f"TARGET RATE: {self.rate_limit if self.rate_limit else 1/self.interval:.1f}Hz, SLEEP TIME: {self.sleep_time}s")

    def _run_synced_functions(self):
        """Run all screenshot-synced functions if they're not already running"""
        # Reset all running states at the start of each screenshot cycle
        with self._sync_lock:
            self._sync_functions_running = {}

        for func in self.screenshot_synced_functions:
            def wrapped_func():
                try:
                    # Run the function
                    func()
                except Exception as e:
                    log("ERROR", f"Error in synced function {func.__name__}: {str(e)}")

            # Create and start a new thread for this function
            thread = threading.Thread(
                target=wrapped_func,
                daemon=True,
                name=f"ScreenSync_{func.__name__}"
            )
            thread.start()

        # Optional: Wait for all threads to complete if you want synchronous execution
        # Remove this if you want async execution
        for thread in threading.enumerate():
            if thread.name.startswith("ScreenSync_"):
                thread.join(timeout=1.0)  # Wait up to 1 second for each thread

    def _before_mainloop(self):
        """Initialize the bot before starting the main loop."""
        # Start screenshot updater
        self.bothandler.start_screenshot_updater(self.interval)
        
        # Wait for window to be ready
        log("INFO", f"Waiting for window '{self.bothandler.window_name}'...")
        
        while not self.bothandler.is_window_ready:
            sleep(0.1)
            
        log("INFO", f"Window '{self.bothandler.window_name}' is ready!")
        
        # Wait for first screenshot
        while self.bothandler.haystack is None:
            sleep(0.1)
            
        log("INFO", "First screenshot captured successfully!")

        # Configure system settings
        if self.mode and 'awake' in self.mode:
            self._keep_awake()
            log("INFO", "Keeping the PC awake")

    def _print_control_instructions(self):
        """Display available hotkeys and controls."""
        print("\n" + "="*50)
        print("CONTROL INSTRUCTIONS:")
        print("="*50)
        print("  ⏯  Ctrl + CapsLock       ")
        print("  ⏯  Ctrl + P        Pause/Unpause")
        print("  ⌕  Ctrl + F        Show performance stats")
        print("  ◼  Ctrl + ESC      ")
        print("  ◼  Ctrl + Space    Exit program")
        print("="*50 + "\n")

    def _mainloop(self):
        """Main loop that initializes and monitors threads."""
        if not self.bothandler.is_window_ready:
            log("WARNING", "Starting main loop without window. Bot functions will wait for window to be ready.")
        self._initialize_threads(self.function_configs)
        self._monitor_threads()

    def run(self, function_configs):
        """
        Run multiple functions in separate threads or handle config dict.
        Args:
            function_configs: list of tuples (old style) or config dict (new style)
        """
        # If config is a dict, handle keep_window_size and extract functions
        if isinstance(function_configs, dict):
            kws = function_configs.get('keep_window_size', {})
            if kws.get('enabled') and kws.get('window_size'):
                self.bothandler.set_window_size_enforcement(
                    enabled=True,
                    window_size=kws['window_size'],
                    mode=kws.get('window_size_mode', 'window')
                )
            function_configs = function_configs.get('functions', [])

        try:
            self.function_configs = function_configs
            self._before_mainloop()
            self._mainloop()
        except Exception as e:
            log("ERROR", f"Bot error: {str(e)}")
            self.bothandler.is_running = False
            raise
        finally:
            self._after_mainloop()
        return 0

    def _initialize_threads(self, function_configs):
        """Initialize and start all threads based on configuration."""
        # Process configurations
        normal_configs = []
        sync_functions = []
        
        # Parse configurations
        log("INFO", "Initializing thread configuration...")
        for config in function_configs:
            if len(config) == 3 and config[2] == "screenshot_sync":
                func, count = config[:2]
                sync_functions.append((func, count))
                for _ in range(count):
                    self.screenshot_synced_functions.append(func)
            else:
                normal_configs.append(config[:2])

        # Initialize bot systems
        self.threads = []
        self.thread_functions = {}

        # Log and start screenshot-sync functions
        if sync_functions:
            log("INFO", "Screenshot-sync functions:")
            for func, count in sync_functions:
                thread_name = f"ScreenSync_{func.__name__}"
                log("INFO", f"- {func.__name__} (Threads: {count}, Name: {thread_name})")

        # Log and start normal threaded functions
        if normal_configs:
            log("INFO", "Normal threaded functions:")
            for func, thread_count in normal_configs:
                func_name = func.__name__
                thread_names = [f"{func_name}" if thread_count == 1 else f"{func_name}_{i+1}" 
                              for i in range(thread_count)]
                log("INFO", f"- {func_name} (Threads: {thread_count}, Name: {', '.join(thread_names)})")
                
                for thread_num in range(thread_count):
                    thread = threading.Thread(
                        target=self._thread_loop,
                        args=(func,),
                        daemon=True,
                        name=thread_names[thread_num]
                    )
                    self.threads.append(thread)
                    self.thread_functions[thread] = (func, thread_count)
                    thread.start()

        # Log final summary
        total_threads = len(self.threads) + sum(count for _, count in sync_functions)
        log("INFO", f"Thread initialization complete. Total threads: {total_threads}")

        # Print initial status
        print("\n🔄 Program is Running")

        # Print control instructions after all initialization is done
        self._print_control_instructions()

    def _monitor_threads(self):
        """Monitor and maintain running threads."""
        try:
            while self.bothandler.is_running:
                alive_threads = [t for t in self.threads if t.is_alive()]
                dead_threads = set(self.threads) - set(alive_threads)
                
                if dead_threads:
                    self._restart_dead_threads(dead_threads, alive_threads)
                sleep(1)
        except KeyboardInterrupt:
            log("INFO", "Received keyboard interrupt, stopping threads...")
            self.bothandler.is_running = False

    def _restart_dead_threads(self, dead_threads, alive_threads):
        """Restart any dead threads."""
        log("WARNING", f"Found {len(dead_threads)} dead threads, restarting them...")
        for dead_thread in dead_threads:
            func, thread_count = self.thread_functions[dead_thread]
            log("INFO", f"Thread {dead_thread.name} died, restarting...")
            
            new_thread = threading.Thread(
                target=self._thread_loop,
                args=(func,),
                daemon=True,
                name=dead_thread.name
            )
            alive_threads.append(new_thread)
            self.thread_functions[new_thread] = self.thread_functions[dead_thread]
            new_thread.start()
            log("INFO", f"Restarted thread: {new_thread.name}")
        
        self.threads = alive_threads

    def _after_mainloop(self):
        """Clean up after main loop ends."""
        log("INFO", "Shutting down bot...")
        cv2.destroyAllWindows()
        sleep(1)

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

        
    def is_window_ready(self):
        """Check if the target window is ready for interaction."""
        return self.bothandler.is_window_ready

    def wait_for_window(self, timeout=None):
        """
        Wait for the window to become ready.
        
        Args:
            timeout (float, optional): Maximum seconds to wait. None means wait forever.
            
        Returns:
            bool: True if window is ready, False if timeout occurred
        """
        start_time = time()
        while not self.bothandler.is_window_ready:
            if timeout and time() - start_time > timeout:
                return False
            sleep(0.1)
        return True

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
    def resize(self, x, y, mode='window'):
        return self.bothandler.resize(x, y, mode)
    
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

    def play_sound(self, sound_name):
        self.bothandler.soundhandler.play_by_name(sound_name)
