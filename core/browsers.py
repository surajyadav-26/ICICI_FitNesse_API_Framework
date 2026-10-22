"""
Which browsers a test can use, including the Chrome and Edge that are already installed on the machine.

    chromium   Playwright's own Chromium (downloaded with `python -m playwright install chromium`)
    firefox    Playwright's Firefox   (python -m playwright install firefox)
    webkit     Playwright's WebKit    (python -m playwright install webkit)
    chrome     Google Chrome installed on this machine        (nothing to download)
    msedge     Microsoft Edge installed on this machine       (nothing to download)

Playwright can drive an installed Chrome or Edge, so those two work without any download. It cannot drive the ordinary
Firefox or Safari of the machine (it needs its own patched builds), so there is no "system Firefox".

If the Playwright Chromium is not installed and the test did not ask for a specific system browser, the first installed
Chrome or Edge is used instead (UI_BROWSER_FALLBACK=true, the default), and the report says so.
"""
import glob
import os
import shutil
import sys

CHOICES = ("chromium", "chrome", "msedge", "firefox", "webkit")

_ALIASES = {
    "": "chromium", "chromium": "chromium", "chromium (chrome)": "chromium", "playwright": "chromium",
    "chrome": "chrome", "google chrome": "chrome", "google-chrome": "chrome", "system chrome": "chrome",
    "msedge": "msedge", "edge": "msedge", "microsoft edge": "msedge", "microsoft-edge": "msedge", "system edge": "msedge",
    "firefox": "firefox", "webkit": "webkit", "safari": "webkit",
}
_LABELS = {"chromium": "Chromium (Playwright)", "chrome": "Google Chrome (installed on this PC)",
           "msedge": "Microsoft Edge (installed on this PC)", "firefox": "Firefox (Playwright)",
           "webkit": "WebKit (Playwright)"}
_ENGINE = {"chromium": "chromium", "chrome": "chromium", "msedge": "chromium", "firefox": "firefox", "webkit": "webkit"}
_CHANNEL = {"chrome": "chrome", "msedge": "msedge"}
_SYSTEM_COMMANDS = {"chrome": ("google-chrome", "google-chrome-stable", "chrome"),
                    "msedge": ("microsoft-edge", "microsoft-edge-stable", "msedge")}
_PLAYWRIGHT_FOLDERS = {"chromium": ("chromium-", "chromium_headless_shell-"), "firefox": ("firefox-",), "webkit": ("webkit-",)}


def normalize(name: str) -> str:
    """The browser id for any spelling a tester might type; an unknown name falls back to chromium."""
    return _ALIASES.get(str(name or "").strip().lower(), "chromium")


def resolve(name: str) -> dict:
    """{"id", "engine" (Playwright engine), "channel" (None, "chrome" or "msedge"), "label"}."""
    browser_id = normalize(name)
    return {"id": browser_id, "engine": _ENGINE[browser_id], "channel": _CHANNEL.get(browser_id), "label": _LABELS[browser_id]}


def system_path(browser_id: str) -> str:
    """Path of the installed Chrome / Edge, or an empty string when it is not installed."""
    if browser_id not in _CHANNEL:
        return ""
    candidates = []
    if sys.platform.startswith("win"):
        roots = [os.environ.get(key, "") for key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        relative = {"chrome": r"Google\Chrome\Application\chrome.exe", "msedge": r"Microsoft\Edge\Application\msedge.exe"}[browser_id]
        candidates = [os.path.join(root, relative) for root in roots if root]
    elif sys.platform == "darwin":
        candidates = {"chrome": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
                      "msedge": ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]}[browser_id]
    else:
        candidates = [path for path in (shutil.which(command) for command in _SYSTEM_COMMANDS[browser_id]) if path]
    return next((path for path in candidates if os.path.isfile(path)), "")


def _playwright_folder() -> str:
    configured = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if configured and configured != "0":
        return configured
    if sys.platform.startswith("win"):
        return os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Caches/ms-playwright")
    return os.path.expanduser("~/.cache/ms-playwright")


def playwright_installed(engine: str) -> bool:
    """True when Playwright's own build of the engine has been downloaded (looked for on disk, nothing is started)."""
    folder = _playwright_folder()
    if not folder or not os.path.isdir(folder):
        return False
    return any(glob.glob(os.path.join(folder, prefix + "*")) for prefix in _PLAYWRIGHT_FOLDERS.get(engine, ()))


def available() -> list:
    """Every choice with whether it can be used on this machine, in the order they are offered."""
    items = []
    for browser_id in CHOICES:
        if browser_id in _CHANNEL:
            path = system_path(browser_id)
            items.append({"id": browser_id, "label": _LABELS[browser_id], "kind": "system", "installed": bool(path), "path": path,
                          "hint": "" if path else f"{_LABELS[browser_id].split(' (')[0]} was not found on this machine"})
        else:
            installed = playwright_installed(_ENGINE[browser_id])
            items.append({"id": browser_id, "label": _LABELS[browser_id], "kind": "playwright", "installed": installed, "path": "",
                          "hint": "" if installed else f"Not downloaded: python -m playwright install {browser_id}"})
    return items


def is_missing_browser_error(error: Exception) -> bool:
    """Playwright's message when its own browser has not been downloaded."""
    text = str(error)
    return "Executable doesn't exist" in text or "playwright install" in text.lower()


def fallback_for(browser_id: str, error: Exception) -> str:
    """The installed system browser to use instead, when Playwright's Chromium is missing; "" when there is none to use."""
    if browser_id != "chromium" or not is_missing_browser_error(error):
        return ""
    return next((candidate for candidate in ("chrome", "msedge") if system_path(candidate)), "")


def missing_message(browser_id: str) -> str:
    """What to tell the tester when the chosen browser cannot start."""
    if browser_id in _CHANNEL:
        return (f"{_LABELS[browser_id].split(' (')[0]} is not installed on this machine. Install it, or choose "
                f"{'msedge' if browser_id == 'chrome' else 'chrome'} or chromium.")
    if browser_id == "chromium":
        if system_path("chrome") or system_path("msedge"):
            return ("Playwright's Chromium is not installed. Choose chrome or msedge (installed on this machine), set "
                    "UI_BROWSER_FALLBACK=true to use them automatically, or run: python -m playwright install chromium")
        return "Playwright's Chromium is not installed and no Chrome or Edge was found. Run: python -m playwright install chromium"
    return (f"Playwright's {browser_id} is not installed. Run: python -m playwright install {browser_id} "
            "(the Firefox or Safari already on this machine cannot be driven by Playwright).")
