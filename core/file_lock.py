"""
A small cross-process lock for files that several test processes read, change and write back (report history, visual results).

    with FileLock("report_history"):
        data = load()
        data.append(item)
        save(data)

Parallel runs start one Slim process per test page, so two of them can finish at the same moment. The lock is an exclusive
file in runtime/locks created with O_EXCL, which works the same on Windows and Linux without extra packages.
A lock older than `stale_after` seconds is taken to belong to a crashed process and is removed; waiting longer than `timeout`
carries on without the lock instead of hanging a test run (the report may then miss one record, which is better than a hang).
"""
import os
import random
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_DIR = os.path.join(BASE_DIR, "runtime", "locks")


class FileLock:
    def __init__(self, name: str, timeout: float = 20.0, stale_after: float = 60.0, directory: str = None) -> None:
        folder = directory or LOCK_DIR
        os.makedirs(folder, exist_ok=True)
        self.path = os.path.join(folder, "".join(c if c.isalnum() or c in "-_." else "_" for c in name) + ".lock")
        self.timeout, self.stale_after = timeout, stale_after
        self._held = False

    def acquire(self) -> bool:
        deadline = time.time() + self.timeout
        while True:
            try:
                handle = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(handle, str(os.getpid()).encode("ascii"))
                os.close(handle)
                self._held = True
                return True
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.path) > self.stale_after:
                        os.remove(self.path)              # left behind by a process that died
                        continue
                except OSError:
                    continue                              # it was released between the two calls
                if time.time() >= deadline:
                    return False
                time.sleep(0.02 + random.random() * 0.05)

    def release(self) -> None:
        if self._held:
            self._held = False
            try:
                os.remove(self.path)
            except OSError:
                pass

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        self.release()


def write_atomically(path: str, text: str) -> None:
    """Writes the whole file or nothing: readers never see half of it, and two writers never share a temporary file."""
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    temporary = f"{path}.{os.getpid()}.{int(time.time() * 1000)}.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(temporary, path)
