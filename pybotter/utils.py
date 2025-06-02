from datetime import datetime
from functools import wraps
from time import time,sleep
from collections import defaultdict
import threading

class PerformanceMonitor:
    """Universal performance monitoring system for tracking FPS and execution times."""
    
    def __init__(self, name, sample_size=30, min_interval=0.0001):
        self.name = name
        self.sample_size = sample_size
        self.min_interval = min_interval
        self.samples = []
        self.last_time = time()
        self.fps = 0.0
        self.avg_execution_time = 0.0
        self.total_calls = 0
        self._lock = threading.Lock()
    
    def update(self):
        """Update FPS calculation"""
        with self._lock:
            current_time = time()
            time_delta = max(current_time - self.last_time, self.min_interval)
            new_fps = 1.0 / time_delta
            
            # Sanity check the FPS value
            if 0 < new_fps < 1000:  # Cap at 1000 FPS to filter outliers
                self.samples.append(new_fps)
                if len(self.samples) > self.sample_size:
                    self.samples.pop(0)
                self.fps = sum(self.samples) / len(self.samples)
            
            self.last_time = current_time
            self.total_calls += 1
            return self.fps

    def get_stats(self):
        """Get current performance statistics"""
        with self._lock:
            return {
                'name': self.name,
                'fps': self.fps,
                'avg_execution_time': 1.0 / self.fps if self.fps > 0 else 0,
                'total_calls': self.total_calls,
                'samples': len(self.samples)
            }

class PerformanceTracker:
    """Singleton class to manage multiple performance monitors"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(PerformanceTracker, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.monitors = {}
            self._initialized = True

    def get_monitor(self, name, sample_size=30, min_interval=0.0001):
        """Get or create a performance monitor for a specific component"""
        if name not in self.monitors:
            with self._lock:
                if name not in self.monitors:
                    self.monitors[name] = PerformanceMonitor(name, sample_size, min_interval)
        return self.monitors[name]

    def get_all_stats(self):
        """Get performance statistics for all monitored components"""
        return {name: monitor.get_stats() for name, monitor in self.monitors.items()}

def monitor_performance(name=None):
    """Decorator to monitor performance of a function"""
    def decorator(func):
        monitor_name = name or func.__name__
        monitor = PerformanceTracker().get_monitor(monitor_name)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                monitor.update()
                return result
            except Exception as e:
                log("[ERROR]", f"Error in {monitor_name}: {str(e)}")
                raise
        return wrapper
    return decorator

def print_performance_stats():
    """Print current performance statistics for all monitored components"""
    stats = PerformanceTracker().get_all_stats()
    print("\nPerformance Statistics:")
    print("-" * 50)
    for name, data in stats.items():
        print(f"{data['name']}:")
        print(f"  FPS: {data['fps']:.1f}")
        print(f"  Avg Execution Time: {data['avg_execution_time']*1000:.1f}ms")
        print(f"  Total Calls: {data['total_calls']}")
    print("-" * 50)

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