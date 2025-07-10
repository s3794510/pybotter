import threading
from .utils import *
import winsound
from time import sleep
import os
import glob

@creation_log
class SoundHandler:

    def __init__(self, sound_folder) -> None:
        self.soundfolderpath = sound_folder
        self.alarm_lock = threading.Lock()

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

    def sound_warning(self):
        self.play(self.soundfolderpath +'/warning.mp3')
    
    def sound_soft_notice(self):
        self.play(self.soundfolderpath +'/soft notice.mp3')

    def play(self, sound_folder):
            thread = threading.Thread(target=self._playsoundWin, args=(sound_folder,))
            thread.start()

    def play_by_name(self, sound_name):
        """
        Play a sound file by name without requiring the file extension.
        Searches for files with common audio extensions (.mp3, .wav, .ogg, .flac, .m4a).
        
        Args:
            sound_name (str): Name of the sound file without extension (e.g., 'pause', 'start')
            
        Returns:
            bool: True if sound was successfully played, False otherwise
        """
        try:
            # Validate input
            if not sound_name or not isinstance(sound_name, str):
                log("[ERROR]", f"Invalid sound name: {sound_name}. Must be a non-empty string.")
                return False
            
            # Check if sound folder exists
            if not os.path.exists(self.soundfolderpath):
                log("[ERROR]", f"Sound folder does not exist: {self.soundfolderpath}")
                return False
            
            # Common audio file extensions to search for
            extensions = ['*.mp3', '*.wav', '*.ogg', '*.flac', '*.m4a', '*.aac']
            
            # Search for files with the given name and any supported extension
            for ext in extensions:
                pattern = os.path.join(self.soundfolderpath, f"{sound_name}{ext[1:]}")  # Remove * from extension
                if os.path.exists(pattern):
                    try:
                        self.play(pattern)
                        return True
                    except Exception as e:
                        log("[ERROR]", f"Failed to play sound file '{pattern}': {e}")
                        continue
            
            # If no file found, try with glob pattern matching
            for ext in extensions:
                pattern = os.path.join(self.soundfolderpath, f"{sound_name}{ext}")
                try:
                    matches = glob.glob(pattern)
                    if matches:
                        try:
                            self.play(matches[0])  # Play the first match
                            return True
                        except Exception as e:
                            log("[ERROR]", f"Failed to play sound file '{matches[0]}': {e}")
                            continue
                except Exception as e:
                    log("[ERROR]", f"Error searching for pattern '{pattern}': {e}")
                    continue
            
            # If no matching file found, provide detailed error information
            try:
                available_files = [os.path.basename(f) for f in os.listdir(self.soundfolderpath) 
                                 if os.path.isfile(os.path.join(self.soundfolderpath, f))]
                log("[ERROR]", f"Sound file '{sound_name}' not found in {self.soundfolderpath}")
                log("[INFO]", f"Available files: {available_files}")
                
                # Suggest similar file names
                similar_files = [f for f in available_files if sound_name.lower() in f.lower() or f.lower().startswith(sound_name.lower())]
                if similar_files:
                    log("[SUGGESTION]", f"Similar files found: {similar_files}")
                    
            except Exception as e:
                log("[ERROR]", f"Error listing available files: {e}")
            
            return False
            
        except Exception as e:
            log("[ERROR]", f"Unexpected error in play_by_name for '{sound_name}': {e}")
            return False


    def play_alarm(self, mode=0):
        """
        Play different alarm sounds based on mode:
        0: Default - Triple beep sequence
        1: Single beep - Quick notification
        2: Warning - Ascending tone sequence
        3: Alert - High-pitched urgent sequence
        4: Success - Pleasant ascending melody
        5: Error - Descending error tone
        """
        def alarm_sound():
            if not self.alarm_lock.acquire(blocking=False):
                return  # Exit if another alarm is already running
            
            try:
                alarm_sequences = {
                    0: [  # Default triple beep
                        (1000, 50), (1200, 50), (1500, 50),
                        (1000, 50), (1200, 50), (1500, 50)
                    ],
                    1: [  # Single beep
                        (80, 100)
                    ],
                    2: [  # Warning
                        (800, 100), (1000, 100), (1200, 100)
                    ],
                    3: [  # Alert
                        (1500, 50), (1500, 50), (1500, 50),
                        (1500, 200)
                    ],
                    4: [  # Success
                        (800, 100), (1000, 100), (1200, 100),
                        (1500, 200)
                    ],
                    5: [  # Error
                        (1200, 100), (1000, 100), (800, 200)
                    ]
                }
                
                sequence = alarm_sequences.get(mode, alarm_sequences[0])
                for freq, dur in sequence:
                    winsound.Beep(freq, dur)
                    sleep(0.03)
            finally:
                self.alarm_lock.release()  # Ensure lock is released

        threading.Thread(target=alarm_sound, daemon=True).start()