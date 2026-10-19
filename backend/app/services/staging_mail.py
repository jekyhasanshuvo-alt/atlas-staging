"""Bounded, ephemeral synthetic mail; no SMTP, files, logs or verification bypass."""

from threading import Lock
from time import monotonic


class StagingMailbox:
    def __init__(self, *, clock=monotonic):
        self._clock = clock
        self._messages = {}
        self._lock = Lock()

    def _expire(self):
        now = self._clock()
        self._messages = {key: value for key, value in self._messages.items() if value[0] > now}

    def put(self, email, kind, link):
        with self._lock:
            self._expire()
            key = (email, kind)
            if key not in self._messages and len(self._messages) >= 16:
                raise ValueError("Synthetic mailbox capacity reached")
            self._messages[key] = (self._clock() + 600, link)

    def consume(self, email, kind):
        with self._lock:
            self._expire()
            value = self._messages.pop((email, kind), None)
            return value[1] if value else None
