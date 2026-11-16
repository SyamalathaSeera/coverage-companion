"""Process-wide request allowances for the supported single-worker deployment."""
import os
import time
from threading import Lock


class WindowLimiter:
    def __init__(self, clock=time.time):
        self.clock = clock
        self.windows = {}
        self.lock = Lock()

    def allow(self, key, limit, seconds):
        now = self.clock()
        bucket = int(now // seconds)
        with self.lock:
            previous, count = self.windows.get(key, (bucket, 0))
            if previous != bucket:
                count = 0
            if count >= limit:
                return False, max(1, int((bucket + 1) * seconds - now))
            self.windows[key] = (bucket, count + 1)
        return True, 0


def configured_limit(name, default):
    try:
        value = int(os.getenv(name, str(default)))
        return max(0, value)
    except ValueError:
        return default


class ProviderAllowanceExceeded(Exception):
    pass


provider_allowance = WindowLimiter()


def reserve_provider_call():
    allowed, _ = provider_allowance.allow('openai', configured_limit('OPENAI_DAILY_CALL_LIMIT', 100), 86400)
    if not allowed:
        raise ProviderAllowanceExceeded('Daily provider allowance reached.')
