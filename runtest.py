import time
import unittest
import sys
from pybot import PyBot
from tkinter import Tk, Button, Frame
from threading import Thread
import win32gui

class Application(Frame):              
    def __init__(self, master=None):
        Frame.__init__(self, master)   
        self.grid()                       
        self.createWidgets()

    def createWidgets(self):
        self.quitButton = Button(self, text='Quit',
            command=self.quit) # exits background (gui) thread
        self.quitButton.grid(row=1,column=0)    
        self.printButton = Button(self, text='Print',command=lambda: self.printHello())         
        self.printButton.grid(row=1,column=1) 

def runtk(window_title):  # runs in background thread
    app = Application()                        
    app.master.title(window_title)     
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


class TestPybotter(unittest.TestCase):
    def run_mock_window_in_thread(self, window_name, root):
        thread_=Thread(target=self.create_window,args=(self,window_name,root,))
        thread_.daemon = True
        thread_.start()
        return thread_


    def create_window(self, window_name, root):
        singleButton = Button(root, text="Sample", padx=500, pady=100)
        singleButton.pack()
        root.title(window_name)
        root.mainloop()

    
    @classmethod
    def setUpClass(cls) -> None:
        cls.window_title ="Test window pybotter fro unit test"
        cls.thd = start_tkinter_thread(cls.window_title)
        check_window_created(cls.window_title)
        cls.pybotter = PyBot(cls.window_title)
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def test_list_windows(self):
        with open('trash', 'w', encoding="utf-8") as w:
            save_stdout = sys.stdout
            sys.stdout = w
            self.assertEqual(PyBot.list_windows(), 0)
            sys.stdout = save_stdout

    def test_targetwindow(self):
        self.assertEqual(self.pybotter.window_name, self.window_title)
        

if __name__ == '__main__':
    unittest.main()
