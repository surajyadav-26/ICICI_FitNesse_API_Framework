"""
Live Debug: "run the next test with a visible browser".

The profile menu sets a flag with a time limit; every browser started while the flag is active is headed, so all rows of a
column table (each row starts its own browser) are visible, not just the first. A normal Run clears the flag.
"""
import json
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAG_FILE = os.path.join(BASE_DIR, "runtime", "live-debug.txt")
DEFAULT_TTL_SECONDS = 900


def activate(ttl_seconds: int = DEFAULT_TTL_SECONDS, path: str = None, now: float = None) -> float:
    """Turns Live Debug on for ttl_seconds; returns the moment it expires."""
    path = path or FLAG_FILE
    expires = (now if now is not None else time.time()) + ttl_seconds
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as flag:
        json.dump({"until": expires}, flag)
    return expires


def clear(path: str = None) -> None:
    try:
        os.remove(path or FLAG_FILE)
    except OSError:
        pass


def is_active(path: str = None, now: float = None) -> bool:
    """True while the flag exists and has not expired. An expired flag is removed."""
    path = path or FLAG_FILE
    now = now if now is not None else time.time()
    try:
        with open(path, "r", encoding="utf-8") as flag:
            text = flag.read().strip()
        try:
            expires = float(json.loads(text)["until"])
        except (ValueError, KeyError, TypeError):
            # older flag files just contain "true": valid for the default time after they were written
            expires = os.path.getmtime(path) + DEFAULT_TTL_SECONDS if text == "true" else 0
    except OSError:
        return False
    if now >= expires:
        clear(path)
        return False
    return True
