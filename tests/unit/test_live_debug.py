"""Live Debug: visible browsers for a whole run, limited in time, cleared by a normal Run."""
import json

from core import live_debug


def test_flag_is_active_until_it_expires(tmp_path):
    flag = str(tmp_path / "flag.txt")
    assert live_debug.is_active(flag) is False
    expires = live_debug.activate(60, flag, now=1000.0)
    assert expires == 1060.0
    assert live_debug.is_active(flag, now=1030.0) is True
    assert live_debug.is_active(flag, now=1030.0) is True        # reading does not consume it: every row's browser is headed
    assert live_debug.is_active(flag, now=1061.0) is False
    assert not (tmp_path / "flag.txt").exists()                  # an expired flag is removed


def test_clear_removes_the_flag_and_is_safe_twice(tmp_path):
    flag = str(tmp_path / "flag.txt")
    live_debug.activate(60, flag)
    live_debug.clear(flag)
    live_debug.clear(flag)
    assert live_debug.is_active(flag) is False


def test_old_style_true_flag_still_works_for_a_limited_time(tmp_path):
    flag = tmp_path / "flag.txt"
    flag.write_text("true", encoding="utf-8")
    modified = flag.stat().st_mtime
    assert live_debug.is_active(str(flag), now=modified + 10) is True
    assert live_debug.is_active(str(flag), now=modified + live_debug.DEFAULT_TTL_SECONDS + 1) is False


def test_garbage_flag_is_ignored(tmp_path):
    flag = tmp_path / "flag.txt"
    flag.write_text("{broken", encoding="utf-8")
    assert live_debug.is_active(str(flag)) is False
    flag.write_text(json.dumps({"other": 1}), encoding="utf-8")
    assert live_debug.is_active(str(flag)) is False


def test_every_browser_started_during_live_debug_is_headed(tmp_path, monkeypatch):
    """Two UiFixtures (two table rows) both see the flag; headless stays the default afterwards."""
    from fixtures.ui import ui_fixture

    flag = tmp_path / "runtime" / "live-debug.txt"
    live_debug.activate(60, str(flag))
    launched = []

    class FakeBrowser:
        def new_context(self, **kwargs):
            class Context:
                def new_page(self_inner):
                    class Page:
                        def on(self, *a):
                            pass
                    return Page()

                def on(self_inner, *a):
                    pass

                def close(self_inner):
                    pass
            return Context()

        def close(self):
            pass

    class FakeChromium:
        def launch(self, headless, **kwargs):
            launched.append(headless)
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()
        firefox = webkit = FakeChromium()

        def stop(self):
            pass

    class FakeStarter:
        def start(self):
            return FakePlaywright()

    monkeypatch.setattr(ui_fixture, "sync_playwright", lambda: FakeStarter())
    for _ in range(2):
        ui = ui_fixture.UiFixture("debug-test")
        ui._workspace_dir = str(tmp_path)
        ui.set_headless("true")
        assert ui.start_browser() is not False
        ui.close_browser()
    assert launched == [False, False]
    live_debug.clear(str(flag))
    ui = ui_fixture.UiFixture("debug-test")
    ui._workspace_dir = str(tmp_path)
    ui.set_headless("true")
    ui.start_browser()
    ui.close_browser()
    assert launched[-1] is True
