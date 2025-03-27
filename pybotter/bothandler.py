from typing import Tuple
import  win32gui, win32api, win32con, sched, threading
from time import time, sleep
import keyboard, cv2, os
from .vision import Vision
from .windowhandler import WindowHandler
from .soundhandler import SoundHandler

class BotHandler:
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
   
    
    def __init__(self, window_name, debug = None, mute = None) -> None:
        self.window_name = window_name
        self.soundpath = os.path.join(os.path.dirname(__file__),'sound')
        self.hwnd = None
        self.get_window_handle()
        self.s = sched.scheduler(time, sleep)
        self.window_handler = WindowHandler(self.window_name)
        self.soundhandler = SoundHandler(self.soundpath)
        self.is_running = True
        self.is_pause = False
        self.loop_time = time()
        self.fps = -1
        self.screenshot = None
        self.debug = debug
        self.images = {str:Vision}

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
            msg = """Needle image is bigger than the target window. needle_w = """ + needle.needle_w.__str__() + " | window_w = " + self.window_handler.w.__str__() + " | needle_h = " + needle.needle_h.__str__() + " | window_h = " + self.window_handler.h.__str__()
            raise Exception(msg)
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
        raise Exception("Unexpected Error")

    def keyboard_press(self, key, duration):
        keycode = self.keymap.get(key.upper())
        win32api.PostMessage(self.hwnd, win32con.WM_KEYDOWN, keycode, 0)
        sleep(duration + 0.1)
        win32api.PostMessage(self.hwnd, win32con.WM_KEYUP, keycode, 0)
        return 0

    def leftclick(self, x, y, duration):
        lParam = win32api.MAKELONG(x, y)
        win32gui.SendMessage(self.hwnd, win32con.WM_MOUSEMOVE, 0, lParam)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        sleep(duration)
        win32gui.SendMessage(self.hwnd, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, lParam)


    def flow_handle(self, sleep_time = 0, debug = 'regular'):
        sleep(sleep_time)
        while self.is_pause:
            sleep(0.05)
        # press 'q' with the output window focused to exit.
        # waits 1 ms every loop to process key presses
        if cv2.waitKey(1) == ord('q'):
            self.exit()
        # calcualte times processed each second
        self.fps = 1 / (time() - self.loop_time)
        self.loop_time = time()


    def init(self):
        self.soundhandler.sound_start()
        # init threads
        self.pause_handle_thread()
        self.exit_handle_thread()
        self.show_fps_handle_thread()

        # initialize the Vision class
        #self.area_img = Vision('areasxx.jpg')
        #self.teleport_img = Vision('teleport.jpg')

    def resize(self, x, y):
        return self.window_handler.window_resize(x, y)

    def destroyAllWindows(self):
        cv2.destroyAllWindows()
        return 0
    
    def pause(self):
        self.is_pause = True
        print("Paused.\n")
        self.soundhandler.sound_pause()

    def unpause(self):
        self.is_pause = False
        print("Continued.\n")
        self.soundhandler.sound_unpause()
        pass

    def exit(self):
        self.is_running = False
        self.soundhandler.sound_exit()
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
                    
                

    def exit_handle_thread(self):
        thread = threading.Thread(target=self.exit_handle, args= ())
        thread.start()
    
    def exit_handle(self, sleep_time = 0.05):
        while self.is_running:
            sleep(sleep_time)
            if keyboard.is_pressed('esc') and keyboard.is_pressed('control'):
                self.exit()


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

    def update_screenshot(self, debug = None):
        self.screenshot = self.window_handler.get_screenshot(debug)


    def __actions__(self): # PUT BOT ACTIONS HERE
        points = self.area_img.find(self.screenshot, 0.8, self.debug, cv2.COLOR_BGR2GRAY)
        if not (len(points)):
            self.keyboard_press('v', 0)
            pass
        if (len(points)):
            points = self.teleport_img.find(self.screenshot, 0.95, self.debug, cv2.COLOR_BGR2GRAY)
            if (len(points)):
                x,y = points[0]
                self.leftclick(x,y, 0)
        

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
'490, 294'
'621, 405'

'131, 116'