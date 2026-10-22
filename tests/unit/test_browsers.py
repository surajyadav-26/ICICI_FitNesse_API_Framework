"""Choosing a browser, including the Chrome / Edge installed on the machine, and falling back when Playwright's is missing."""
import os

import pytest

from core import browsers
from core.config import Config
from fixtures.ui.ui_fixture import UiFixture


# ── names and detection ──────────────────────────────────────────────────────
@pytest.mark.parametrize("typed, expected", [
    ("", "chromium"), ("Chromium", "chromium"), ("chrome", "chrome"), ("Google Chrome", "chrome"), ("edge", "msedge"),
    ("MSEdge", "msedge"), ("Microsoft Edge", "msedge"), ("firefox", "firefox"), ("safari", "webkit"), ("opera", "chromium")])
def test_any_spelling_resolves_to_one_id(typed, expected):
    assert browsers.normalize(typed) == expected


def test_a_system_browser_is_chromium_with_a_channel():
    assert browsers.resolve("chrome") == {"id": "chrome", "engine": "chromium", "channel": "chrome",
                                          "label": "Google Chrome (installed on this PC)"}
    assert browsers.resolve("edge")["channel"] == "msedge"
    assert browsers.resolve("firefox")["channel"] is None and browsers.resolve("firefox")["engine"] == "firefox"


def test_windows_paths_are_looked_up_in_the_program_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(browsers.sys, "platform", "win32")
    chrome = tmp_path / "pf" / "Google" / "Chrome" / "Application" / "chrome.exe"
    chrome.parent.mkdir(parents=True)
    chrome.write_text("x")
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "pf"))
    monkeypatch.setenv("PROGRAMFILES(X86)", str(tmp_path / "none"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    assert browsers.system_path("chrome") == str(chrome)
    assert browsers.system_path("msedge") == "" and browsers.system_path("firefox") == ""


def test_playwright_browsers_are_found_on_disk_without_starting_anything(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    assert not browsers.playwright_installed("chromium")
    (tmp_path / "chromium_headless_shell-1234").mkdir()
    (tmp_path / "firefox-99").mkdir()
    assert browsers.playwright_installed("chromium") and browsers.playwright_installed("firefox")
    assert not browsers.playwright_installed("webkit")


def test_available_lists_every_choice_with_a_hint_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    monkeypatch.setattr(browsers, "system_path", lambda browser_id: "C:/Chrome/chrome.exe" if browser_id == "chrome" else "")
    items = {item["id"]: item for item in browsers.available()}
    assert list(items) == list(browsers.CHOICES)
    assert items["chrome"]["installed"] and items["chrome"]["path"].endswith("chrome.exe")
    assert not items["msedge"]["installed"] and "not found" in items["msedge"]["hint"]
    assert not items["firefox"]["installed"] and "playwright install firefox" in items["firefox"]["hint"]


def test_only_a_missing_playwright_chromium_falls_back_to_an_installed_browser(monkeypatch):
    missing = RuntimeError("BrowserType.launch: Executable doesn't exist at C:\\x\\chrome.exe. Run playwright install")
    monkeypatch.setattr(browsers, "system_path", lambda browser_id: "C:/e.exe" if browser_id == "msedge" else "")
    assert browsers.fallback_for("chromium", missing) == "msedge"                     # Chrome is absent, Edge is there
    assert browsers.fallback_for("firefox", missing) == ""                            # nothing can stand in for Firefox
    assert browsers.fallback_for("chrome", missing) == ""                             # an explicit choice is not replaced
    assert browsers.fallback_for("chromium", RuntimeError("Target closed")) == ""     # another failure is not a missing browser
    monkeypatch.setattr(browsers, "system_path", lambda browser_id: "")
    assert browsers.fallback_for("chromium", missing) == ""


def test_the_messages_tell_the_tester_what_to_do():
    assert "python -m playwright install firefox" in browsers.missing_message("firefox")
    assert "cannot be driven" in browsers.missing_message("firefox")
    assert "msedge" in browsers.missing_message("chrome")
    assert "python -m playwright install chromium" in browsers.missing_message("chromium")


# ── the fixture starting a browser (a fake Playwright records what was asked) ─
class FakePage:
    url = "about:blank"

    def on(self, *args, **kwargs):
        pass


class FakeContext:
    def __init__(self):
        self.closed = False

    def new_page(self):
        return FakePage()

    def on(self, *args, **kwargs):
        pass

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self):
        self.closed = False

    def new_context(self, **kwargs):
        return FakeContext()

    def close(self):
        self.closed = True


class FakeEngine:
    def __init__(self, missing_without_channel=False):
        self.calls = []
        self.missing_without_channel = missing_without_channel

    def launch(self, **kwargs):
        self.calls.append(kwargs)
        if self.missing_without_channel and "channel" not in kwargs:
            raise RuntimeError("BrowserType.launch: Executable doesn't exist at C:\\pw\\chromium\\chrome.exe\n playwright install")
        return FakeBrowser()


class FakePlaywright:
    def __init__(self, missing_chromium=False):
        self.chromium = FakeEngine(missing_chromium)
        self.firefox = FakeEngine(missing_without_channel=True)
        self.webkit = FakeEngine()

    def start(self):
        return self

    def stop(self):
        pass


@pytest.fixture
def fixture_with(monkeypatch):
    def make(missing_chromium=False):
        playwright = FakePlaywright(missing_chromium)
        monkeypatch.setattr("fixtures.ui.ui_fixture.sync_playwright", lambda: playwright)
        monkeypatch.setattr("fixtures.ui.ui_fixture.UiFixture._log_simple_step", lambda *a, **k: None)
        monkeypatch.setattr(Config, "UI_BROWSER_FALLBACK", True)
        monkeypatch.setattr("core.browsers.system_path", lambda browser_id: "C:/x" if browser_id in ("chrome", "msedge") else "")
        ui = UiFixture("BrowserCheck")
        ui.set_test_name("BrowserCheck")
        ui._test_name_override = True
        return ui, playwright
    return make


def test_chrome_is_started_through_its_channel(fixture_with):
    ui, playwright = fixture_with()
    assert ui.start_browser("chrome") is True
    assert playwright.chromium.calls[0]["channel"] == "chrome" and ui._browser_id == "chrome"
    ui.close_browser()


def test_edge_is_started_through_its_channel(fixture_with):
    ui, playwright = fixture_with()
    ui.set_browser("edge")
    assert ui.start_browser() is True and playwright.chromium.calls[0]["channel"] == "msedge" and ui._browser_id == "msedge"
    ui.close_browser()


def test_playwright_chromium_is_started_without_a_channel(fixture_with):
    ui, playwright = fixture_with()
    assert ui.start_browser("chromium") is True
    assert "channel" not in playwright.chromium.calls[0] and ui._browser_id == "chromium"
    ui.close_browser()


def test_a_missing_playwright_chromium_uses_the_installed_chrome(fixture_with):
    ui, playwright = fixture_with(missing_chromium=True)
    assert ui.start_browser("chromium") is True
    assert [call.get("channel") for call in playwright.chromium.calls] == [None, "chrome"]
    assert ui._browser_id == "chrome"
    ui.close_browser()


def test_without_the_fallback_a_missing_chromium_is_an_error_that_says_what_to_do(fixture_with, monkeypatch):
    ui, playwright = fixture_with(missing_chromium=True)
    monkeypatch.setattr(Config, "UI_BROWSER_FALLBACK", False)
    assert ui.start_browser("chromium") is False
    assert "python -m playwright install chromium" in ui._start_error


def test_a_missing_firefox_is_not_replaced_by_chrome(fixture_with):
    ui, playwright = fixture_with()
    assert ui.start_browser("firefox") is False
    assert "playwright install firefox" in ui._start_error and "cannot be driven" in ui._start_error
    assert playwright.chromium.calls == []


def test_a_system_browser_that_is_not_installed_says_so(fixture_with, monkeypatch):
    ui, playwright = fixture_with()
    monkeypatch.setattr(playwright.chromium, "launch", lambda **kw: (_ for _ in ()).throw(RuntimeError("Chromium distribution 'chrome' is not found")))
    assert ui.start_browser("chrome") is False
    assert "Google Chrome is not installed on this machine" in ui._start_error


def test_the_visual_baselines_are_kept_per_browser_and_chrome_is_not_chromium(fixture_with):
    ui, _ = fixture_with()
    ui.start_browser("chrome")
    ui._page.evaluate = lambda script: [1600, 1043]
    assert ui._visual_profile() == "chrome-1600x1043"
    ui.close_browser()


# ── the page asks the user store server which browsers this machine can run ──
def test_the_server_lists_the_browsers_of_this_machine():
    import json
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer

    from core import user_store_server
    server = ThreadingHTTPServer(("127.0.0.1", 0), user_store_server.UserStoreHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        answer = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}/browsers", timeout=10).read())
    finally:
        server.shutdown()
    assert [item["id"] for item in answer["browsers"]] == list(browsers.CHOICES)
    assert {item["kind"] for item in answer["browsers"]} == {"playwright", "system"}
    assert answer["fallback"] in (True, False)
