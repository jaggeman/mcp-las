"""Bounded, process-local storage for short-lived bearer downloads.

Tokens must be generated using secrets.token_urlsafe(32). Possession grants
download access; never log or share them. Restart/eviction invalidates links.
"""
import time
from collections import OrderedDict
from collections.abc import MutableMapping
from threading import RLock, Timer


class DownloadStore(MutableMapping):
    def __init__(self, max_files=32, max_bytes=32 * 1024 * 1024,
                 max_file_bytes=2 * 1024 * 1024, ttl=600):
        self.max_files = max_files
        self.max_bytes = max_bytes
        self.max_file_bytes = max_file_bytes
        self.ttl = ttl
        self._items = OrderedDict()
        self._bytes = 0
        self._lock = RLock()

    def _remove(self, key):
        value, _, timer = self._items.pop(key)
        self._bytes -= len(value['bytes'])
        timer.cancel()

    def _expire(self):
        now = time.perf_counter()
        for key, (_, deadline, _) in list(self._items.items()):
            if deadline <= now:
                self._remove(key)

    def _expire_in_background(self):
        with self._lock:
            self._expire()

    def __setitem__(self, key, value):
        size = len(value['bytes'])
        if size > min(self.max_file_bytes, self.max_bytes):
            raise ValueError('Excel file exceeds download size limit')
        with self._lock:
            self._expire()
            if key in self._items:
                self._remove(key)
            while self._items and (len(self._items) >= self.max_files or self._bytes + size > self.max_bytes):
                self._remove(next(iter(self._items)))
            timer = Timer(self.ttl, self._expire_in_background)
            timer.daemon = True
            self._items[key] = (dict(value), time.perf_counter() + self.ttl, timer)
            self._bytes += size
            timer.start()

    def __getitem__(self, key):
        with self._lock:
            self._expire()
            return dict(self._items[key][0])

    def __delitem__(self, key):
        with self._lock:
            self._remove(key)

    def __iter__(self):
        with self._lock:
            self._expire()
            return iter(list(self._items))

    def __len__(self):
        with self._lock:
            self._expire()
            return len(self._items)
