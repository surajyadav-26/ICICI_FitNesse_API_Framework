"""Unit tests for the visual regression engine (no browser needed)."""
import os

import pytest
from PIL import Image, ImageDraw

from core import visual_compare as vc


@pytest.fixture(autouse=True)
def stores(tmp_path, monkeypatch):
    monkeypatch.setattr(vc, "BASELINE_DIR", str(tmp_path / "baselines"))
    monkeypatch.setattr(vc, "RESULT_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(vc, "RESULTS_FILE", str(tmp_path / "results" / "results.json"))
    return tmp_path


def make_image(path, size=(200, 100), color=(255, 255, 255), box=None, box_color=(0, 0, 0)):
    image = Image.new("RGB", size, color)
    if box:
        ImageDraw.Draw(image).rectangle(box, fill=box_color)
    image.save(path)
    return str(path)


def test_first_run_creates_baseline_as_new(tmp_path):
    shot = make_image(tmp_path / "a.png")
    result = vc.check_against_baseline(shot, "chromium-200x100", "home")
    assert result.status == "new"
    assert os.path.isfile(vc.baseline_path("chromium-200x100", "home"))


def test_identical_image_passes(tmp_path):
    shot = make_image(tmp_path / "a.png", box=(10, 10, 50, 50))
    vc.check_against_baseline(shot, "p", "home")
    result = vc.check_against_baseline(shot, "p", "home")
    assert result.status == "passed" and result.mismatch_pct == 0 and result.diff_pixels == 0


def test_changed_region_fails_with_measured_percentage(tmp_path):
    vc.check_against_baseline(make_image(tmp_path / "a.png"), "p", "home")
    changed = make_image(tmp_path / "b.png", box=(0, 0, 99, 49))          # 100 x 50 px = 25 % of 200 x 100
    result = vc.check_against_baseline(changed, "p", "home", threshold_pct=1.0)
    assert result.status == "failed"
    assert result.mismatch_pct == pytest.approx(25.0, abs=0.1)
    assert os.path.isfile(os.path.join(vc.result_dir("p", "home"), "diff.png"))


def test_threshold_allows_small_differences(tmp_path):
    vc.check_against_baseline(make_image(tmp_path / "a.png"), "p", "home")
    tiny = make_image(tmp_path / "b.png", box=(0, 0, 9, 9))               # 100 px = 0.5 %
    assert vc.check_against_baseline(tiny, "p", "home", threshold_pct=0.1).status == "failed"
    assert vc.check_against_baseline(tiny, "p", "home", threshold_pct=1.0).status == "passed"


def test_pixel_tolerance_ignores_faint_colour_noise(tmp_path):
    vc.check_against_baseline(make_image(tmp_path / "a.png", color=(250, 250, 250)), "p", "home")
    noisy = make_image(tmp_path / "b.png", color=(255, 255, 255))         # 5 levels off everywhere
    assert vc.check_against_baseline(noisy, "p", "home", pixel_tolerance=10).status == "passed"
    assert vc.check_against_baseline(noisy, "p", "home", pixel_tolerance=2).status == "failed"


def test_size_change_always_fails(tmp_path):
    vc.check_against_baseline(make_image(tmp_path / "a.png", size=(200, 100)), "p", "home")
    taller = make_image(tmp_path / "b.png", size=(200, 150))
    result = vc.check_against_baseline(taller, "p", "home", threshold_pct=100.0)
    assert result.status == "failed" and result.size_mismatch
    assert "size changed" in result.message


def test_update_flag_replaces_baseline(tmp_path):
    vc.check_against_baseline(make_image(tmp_path / "a.png"), "p", "home")
    changed = make_image(tmp_path / "b.png", box=(0, 0, 99, 49))
    assert vc.check_against_baseline(changed, "p", "home", update=True).status == "updated"
    assert vc.check_against_baseline(changed, "p", "home").status == "passed"


def test_approve_promotes_latest_actual(tmp_path):
    vc.check_against_baseline(make_image(tmp_path / "a.png"), "p", "home")
    changed = make_image(tmp_path / "b.png", box=(0, 0, 99, 49))
    assert vc.check_against_baseline(changed, "p", "home").status == "failed"
    entry = vc.approve("p", "home")
    assert entry["status"] == "updated"
    assert vc.check_against_baseline(changed, "p", "home").status == "passed"


def test_approve_without_screenshot_raises():
    with pytest.raises(FileNotFoundError):
        vc.approve("p", "never-ran")


def test_results_index_lists_failures_first(tmp_path):
    vc.check_against_baseline(make_image(tmp_path / "a.png"), "p", "ok page")
    vc.check_against_baseline(make_image(tmp_path / "a.png"), "p", "ok page")
    vc.check_against_baseline(make_image(tmp_path / "a.png"), "p", "bad page")
    vc.check_against_baseline(make_image(tmp_path / "b.png", box=(0, 0, 99, 49)), "p", "bad page")
    statuses = [(item["name"], item["status"]) for item in vc.list_results()]
    assert statuses == [("bad page", "failed"), ("ok page", "passed")]


@pytest.mark.parametrize("name", ["../x", "", "a/b", "a\\b", ".hidden", "x" * 200])
def test_unsafe_names_are_rejected(name):
    with pytest.raises(ValueError):
        vc.clean_name(name)


@pytest.mark.parametrize("profile", ["../x", "", "a/b", "chromium 1x1"])
def test_unsafe_profiles_are_rejected(profile):
    with pytest.raises(ValueError):
        vc.clean_profile(profile)


def test_review_page_renders_cards_and_escapes_names(tmp_path):
    from core import visual_review
    assert "No visual results yet" in visual_review.render_page()
    vc.check_against_baseline(make_image(tmp_path / "a.png"), "p", "login box")
    vc.check_against_baseline(make_image(tmp_path / "b.png", box=(0, 0, 99, 49)), "p", "login box")
    page = visual_review.render_page()
    assert "login box" in page and "Mismatch" in page and "Approve as baseline" in page
    assert "/visual-image/p/login%20box/diff.png" in page
