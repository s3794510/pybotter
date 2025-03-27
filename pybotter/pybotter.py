from .bothandler import BotHandler
from .windowhandler import WindowHandler
import winsound, time, threading

class PyBot:
    
    def __init__(self, window_name, sleeptime = 0, debug = None):
        '''
        window_name (str): name of the target window
        sleeptime (int): amount of seconds wait after each cycle
        debug: debug mode
        '''
        if not debug:
            self.debug = ''
        else:
            self.debug = debug
        self.window_name = window_name
        self.sleeptime = sleeptime
        self.bothandler = BotHandler(window_name, self.debug)
        print("Object PyBot created, Window name: ", self.window_name)

    def mainloop(self, func):
        def run():
            # Start program text
            print("""Hold Ctrl + ESC to stop
            Hold Ctrl + P to pause/unpause.
            Hold Ctrl + F to show FPS
            Program is running.
            """)

            # Run the bot
            return_code = self.runmainloop(func)

            # After done running
            print('Program is closed.')
            return return_code
        return run

    def runmainloop(self, actions):
        while(self.bothandler.is_running):
    
            # get an updated image of the game
            self.bothandler.update_screenshot(self.debug)

            # Put the actions (mouse/keyboard) inside function actions in this class
            actions()

            # hanlding after each cycle
            self.bothandler.flow_handle(sleep_time = self.sleeptime, debug = self.debug)
        self.bothandler.destroyAllWindows()
        return 0

    def variables(self, func):
        def run(*args, **kwargs):
            self.bothandler.init()
            return_code = func(*args, **kwargs)
            return return_code
        return run

    def list_windows():
        return WindowHandler.list_window_titles()

    def add_image(self, name, path):
        return self.bothandler.add_image(name, path)

    def find_image(self, name, threshold = 0.5, convert=None):
        "convert method = COLOR_BGR2GRAY"
        return self.bothandler.find_image(name, threshold,convert=convert)

    def show_window(self):
        self.bothandler.show_screenshot()


    def left_click(self, x, y, duration):
        self.bothandler.leftclick(x, y, duration)

    def key_press(self, key, duration):
        return self.bothandler.keyboard_press(key, duration)

    def resize(self, x, y):
        return self.bothandler.resize(x, y)
    
    def play_alarm(self):
        def alarm_sound():
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
                time.sleep(0.5)

        threading.Thread(target=alarm_sound, daemon=True).start()
    
    def wait(self, duration):
        time.sleep(duration)