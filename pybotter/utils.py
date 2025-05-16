from datetime import datetime
from functools import wraps


def log(level, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if level.startswith('[') and level.endswith(']'):
        level_str = level
    else:
        level_str = f'[{level}]'
    print(f"[{timestamp}] {level_str} {message}")

def creation_log(cls):
    original_init = cls.__init__

    @wraps(original_init)
    def new_init(self, *args, **kwargs):
        log("INFO", f"Creating instance of {cls.__name__} ...")
        original_init(self, *args, **kwargs)
        log("INFO", f"Instance of {cls.__name__} created")

    cls.__init__ = new_init
    return cls
