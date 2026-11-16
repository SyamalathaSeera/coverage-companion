"""Bounded, per-browser in-memory documents; no PDF bytes are retained."""
import secrets
import time
from threading import RLock
from fastapi import HTTPException

SESSION_SECONDS = 1800


class DocumentStore:
    def __init__(self, ttl=SESSION_SECONDS, capacity=100, clock=time.monotonic):
        self.ttl, self.capacity, self.clock = ttl, capacity, clock
        self.records = {}
        self.lock = RLock()

    def cleanup(self):
        with self.lock:
            now = self.clock()
            for key in list(self.records):
                if self.records[key]['deadline'] <= now:
                    del self.records[key]

    def get(self, key):
        with self.lock:
            self.cleanup()
            return self.records.get(key)

    def put(self, old_key, filename, pages):
        with self.lock:
            self.cleanup()
            if len(self.records) >= self.capacity and old_key not in self.records:
                raise HTTPException(503, 'Demo document capacity reached. Please try later.')
            self.remove(old_key)
            key = secrets.token_urlsafe(32)
            self.records[key] = dict(filename=filename, pages=pages, deadline=self.clock() + self.ttl)
            return key, self.records[key]

    def remove(self, key):
        with self.lock:
            self.records.pop(key, None)
