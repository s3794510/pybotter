from datetime import datetime
from functools import wraps
from time import time,sleep
from collections import defaultdict
import threading

class PerformanceMonitor:
    """Universal performance monitoring system for tracking execution cycles and times."""
    
    def __init__(self, name, sample_size=30, min_interval=0.0001):
        self.name = name
        self.sample_size = sample_size
        self.min_interval = min_interval
        self.samples = []
        self.last_time = time()
        self.cycles_per_sec = 0.0
        self.total_calls = 0
        self._lock = threading.Lock()
    
    def update(self):
        """Update cycle rate calculation"""
        with self._lock:
            current_time = time()
            time_delta = max(current_time - self.last_time, self.min_interval)
            new_rate = 1.0 / time_delta
            
            # Sanity check the rate value
            if 0 < new_rate < 1000:  # Cap at 1000 cycles/sec to filter outliers
                self.samples.append(new_rate)
                if len(self.samples) > self.sample_size:
                    self.samples.pop(0)
                self.cycles_per_sec = sum(self.samples) / len(self.samples)
            
            self.last_time = current_time
            self.total_calls += 1
            return self.cycles_per_sec

    @property
    def average_cycle_time(self):
        """Get average cycle time in seconds"""
        return 1.0 / self.cycles_per_sec if self.cycles_per_sec > 0 else 0

    def get_stats(self):
        """Get current performance statistics"""
        with self._lock:
            return {
                'name': self.name,
                'cycles_per_sec': self.cycles_per_sec,
                'avg_execution_time': self.average_cycle_time,
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

    @classmethod
    def get_all_monitors(cls):
        """Get all registered performance monitors"""
        instance = cls()
        return list(instance.monitors.values())

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
    """Print performance statistics for all registered monitors."""
    monitors = PerformanceTracker.get_all_monitors()
    if not monitors:
        print("No performance data available")
        return

    # Find the longest name for alignment
    max_name_length = max(len(monitor.name) for monitor in monitors)
    
    # Print each monitor's stats on its own line with aligned columns
    for monitor in monitors:
        fps = monitor.cycles_per_sec
        avg_time = monitor.average_cycle_time * 1000  # Convert to ms
        name_padded = monitor.name.ljust(max_name_length)
        print(f"🔹 {name_padded} | Rate: {fps:6.1f} Hz | Avg Time: {avg_time:6.1f} ms")

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
    If the instance has a 'name' attribute, it will be included in the log.
    """
    original_init = cls.__init__

    @wraps(original_init)
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        # Check if instance has a name attribute
        instance_name = getattr(self, 'name', None)
        if instance_name:
            log("INFO", f"Instance of {cls.__name__} created: {instance_name}")
        else:
            log("INFO", f"Instance of {cls.__name__} created")

    cls.__init__ = new_init
    return cls