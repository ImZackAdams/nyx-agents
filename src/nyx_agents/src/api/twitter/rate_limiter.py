from typing import List
import time

class RateLimitTracker:
    """Tracks and manages rate limit occurrences."""
    
    def __init__(self, window_minutes: int = 15, threshold: int = 3, backoff_hours: int = 3):
        self.rate_limits: List[float] = []
        self.window_minutes = window_minutes
        self.threshold = threshold
        self.backoff_hours = backoff_hours

    def add_rate_limit(self) -> None:
        """Record a new rate limit hit and clean old ones."""
        current_time = time.time()
        self.rate_limits.append(current_time)
        window_start = current_time - (self.window_minutes * 60)
        self.rate_limits = [t for t in self.rate_limits if t > window_start]

    def should_extended_sleep(self) -> bool:
        """Determine if we need an extended sleep period."""
        return len(self.rate_limits) >= self.threshold

    def get_sleep_time(self, reset_time: int) -> int:
        """Calculate appropriate sleep time based on rate limit history."""
        if self.should_extended_sleep():
            self.rate_limits.clear()
            return self.backoff_hours * 60 * 60
        return max(0, reset_time - int(time.time()))