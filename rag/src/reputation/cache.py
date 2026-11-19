"""Bounded process-local cache with opaque keys; no disk persistence."""

import hashlib
import hmac
import secrets
import time
from collections import OrderedDict


class TTLCache:
    def __init__(self, max_entries=1024, clock=time.monotonic):
        self.max_entries = max_entries
        self.clock = clock
        self._secret = secrets.token_bytes(32)
        self._items = OrderedDict()

    def key(self, provider, kind, value):
        return hmac.new(
            self._secret, f"{provider}\0{kind}\0{value}".encode(), hashlib.sha256
        ).hexdigest()

    def get(self, key):
        item = self._items.get(key)
        if item is None:
            return None
        expiry, value = item
        if expiry <= self.clock():
            del self._items[key]
            return None
        self._items.move_to_end(key)
        return value

    def put(self, key, value, ttl):
        self._items[key] = (self.clock() + ttl, value)
        self._items.move_to_end(key)
        while len(self._items) > self.max_entries:
            self._items.popitem(last=False)
