from datetime import datetime
from functools import wraps
from time import time,sleep
from collections import defaultdict
 


def rate_limit(min_interval):
    """
    Rate-limit calls per unique set of arguments (args + kwargs).
    """
    last_called_map = defaultdict(lambda: 0)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use (args, frozenset(kwargs)) as a hashable key
            key = (args, frozenset(kwargs.items()))
            now = time()
            if now - last_called_map[key] >= min_interval:
                last_called_map[key] = now
                return func(*args, **kwargs)
            # else:
            #     wait = round(min_interval - (now - last_called_map[key]), 2)
                #print(f"[{key}] Blocked. Try again in {wait}s.")
        return wrapper
    return decorator

@rate_limit(5)
def log(level = "INFO", message = "Unexpected issue occurred"):
    """
    Log a message with a timestamp and level.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if level.startswith('[') and level.endswith(']'):
        level_str = level
    else:
        level_str = f'[{level}]'
    print(f"[{timestamp}] {level_str} {message}")


def creation_log(cls):
    """
    Decorator to log the creation of a class instance.
    """
    original_init = cls.__init__

    @wraps(original_init)
    def new_init(self, *args, **kwargs):
        log("INFO", f"Creating instance of {cls.__name__} ...")
        original_init(self, *args, **kwargs)
        log("INFO", f"Instance of {cls.__name__} created")

    cls.__init__ = new_init
    return cls