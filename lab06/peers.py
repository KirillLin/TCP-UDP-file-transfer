import time
import threading

class Peers:
    def __init__(self, timeout):
        self.timeout = timeout
        self._seen = {}
        self._ignored = set()
        self._lock = threading.Lock()

    def touch(self, ip):
        with self._lock:
            new = ip not in self._seen
            self._seen[ip] = time.monotonic()
            return new

    def _remove_stale(self):
        now = time.monotonic()
        for ip in list(self._seen):
            if now - self._seen[ip] >= self.timeout:
                del self._seen[ip]

    def list_all(self):
        with self._lock:
            self._remove_stale()
            return list(self._seen)

    def ignore(self, ip):
        with self._lock:
            self._ignored.add(ip)

    def is_ignored(self, ip):
        with self._lock:
            return ip in self._ignored

    def unignore(self, ip):
        with self._lock:
            self._ignored.discard(ip)

    def forget(self, ip):
        with self._lock:
            self._seen.pop(ip, None)
