import threading
from .utils import *

@creation_log
class SoundHandler:

    def __init__(self, sound_folder) -> None:
        self.soundfolderpath = sound_folder

    def _playsoundWin(self, sound, block = True):
        """
        This function is a replica from playsound 1.2.2, kudos to TaylorSMarks.
        See their GitHub on https://github.com/TaylorSMarks/
        """
        '''
        Utilizes windll.winmm. Tested and known to work with MP3 and WAVE on
        Windows 7 with Python 2.7. Probably works with more file formats.
        Probably works on Windows XP thru Windows 10. Probably works with all
        versions of Python.

        Inspired by (but not copied from) Michael Gundlach <gundlach@gmail.com>'s mp3play:
        https://github.com/michaelgundlach/mp3play

        I never would have tried using windll.winmm without seeing his code.
        '''
        from ctypes import c_buffer, windll
        from random import random
        from time   import sleep
        from sys    import getfilesystemencoding

        def winCommand(*command):
            buf = c_buffer(255)
            command = ' '.join(command).encode(getfilesystemencoding())
            errorCode = int(windll.winmm.mciSendStringA(command, buf, 254, 0))
            if errorCode:
                errorBuffer = c_buffer(255)
                windll.winmm.mciGetErrorStringA(errorCode, errorBuffer, 254)
                exceptionMessage = ('\n    Error ' + str(errorCode) + ' for command:'
                                    '\n        ' + command.decode() +
                                    '\n    ' + errorBuffer.value.decode())
                raise Exception(exceptionMessage)
            return buf.value

        alias = 'playsound_' + str(random())
        winCommand('open "' + sound + '" alias', alias)
        winCommand('set', alias, 'time format milliseconds')
        durationInMS = winCommand('status', alias, 'length')
        winCommand('play', alias, 'from 0 to', durationInMS.decode())

        if block:
            sleep(float(durationInMS) / 1000.0)
        
    def sound_pause(self):
        self.play(self.soundfolderpath +'/pause.mp3')

    def sound_unpause(self):
        self.play(self.soundfolderpath +'/unpause.mp3')

    def sound_start(self):
        self.play(self.soundfolderpath +'/start.mp3')

    def sound_exit(self):
        self.play(self.soundfolderpath +'/exit.mp3')

    def play(self, sound_folder):
            thread = threading.Thread(target=self._playsoundWin, args=(sound_folder,))
            thread.start()