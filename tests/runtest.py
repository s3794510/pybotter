import time
import unittest
import sys, os, cv2
from pybotter import PyBot
from pybotter.vision import Vision
from tkinter import Tk, Button
from threading import Thread
import win32gui

image_test_path = "./testImages/SampleButton.png"

class MockWindow(Tk):              
    def __init__(self):
        Tk.__init__(self)   
        singleButton = Button(self, text="Sample", padx=200, pady=50)
        singleButton.pack()

    def createWidgets(self):
        self.quitButton = Button(self, text='Quit',
            command=self.quit) # exits background (gui) thread
        self.quitButton.grid(row=1,column=0)    
        self.printButton = Button(self, text='Print',command=lambda: self.printHello())         
        self.printButton.grid(row=1,column=1) 

def runtk(window_title):  # runs in background thread
    app = MockWindow()                        
    app.title(window_title)     
    app.mainloop()

def start_tkinter_thread(window_title):
    thd = Thread(target=runtk, args= (window_title,))   # gui thread
    thd.daemon = True  # background thread will exit if main thread exits
    thd.start()  # start tk loop
    return thd

def find_window(name):
    whnd = win32gui.FindWindowEx(None, None, None, name)
    if not (whnd == 0):
        return True

def check_window_created(window_title):
    start_time = time.time()
    while not find_window(window_title):
        if time.time() > start_time + 5:
            raise Exception("Mock window was not properly created.") 

class disableConsolePrint():
    def __enter__(self):
        sys.stdout = open(os.devnull, 'w',encoding="utf-8")

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        
class TestPybotter(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.current_dir = os.getcwd()
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        cls.window_title ="Test window pybotter for unit test"
        cls.thd = start_tkinter_thread(cls.window_title)
        check_window_created(cls.window_title)
        cls.needle_name = "SampleButton"
        cls.needle_path = image_test_path
        with disableConsolePrint():
            cls.pybotter = PyBot(cls.window_title)
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        os.chdir(cls.current_dir)
        pass

    def test_targetwindow(self):
        with disableConsolePrint():
            self.assertEqual(self.pybotter.window_name, self.window_title)

    def test_add_image_fail(self):
        with disableConsolePrint():
            self.assertRaises(Exception, self.pybotter.add_image,self.needle_name, "Wrong path")

    def test_add_image(self):
        self.assertIsInstance(self.pybotter.add_image(self.needle_name, self.needle_path), Vision)
        self.assertRaises(Exception,self.pybotter.add_image,(self.needle_name, self.needle_path))
        self.assertIsInstance(self.pybotter.bothandler.needle_handlers.get(self.needle_name), Vision)

    def test_needle_bigger_than_image_when_find(self):
        self.assertRaises(Exception, self.pybotter.find_image,(self.needle_name, 0.5))

    def test_find_image(self):
        self.pybotter.resize(640,480)
        start_time = time.time()
        while start_time + 1 > time.time():
            self.pybotter.bothandler.update_screenshot()
            cor = self.pybotter.find_image(self.needle_name, 0.5)
            if cor.__len__()>0:
                break
        self.assertNotEqual(cor.__len__(),0)


if __name__ == '__main__':
    unittest.main()

