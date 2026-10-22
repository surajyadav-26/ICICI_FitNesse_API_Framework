"""What kind of difference each differing area is: a moved field, a resized box, a wrong colour, different content."""
import numpy
import pytest
from PIL import Image, ImageDraw

from core import visual_compare as vc
from core import visual_regions as vr


def screen(button=(100, 100, 220, 140), fill=(231, 120, 23), field=(100, 40, 300, 70), text_box=None):
    image = Image.new("RGB", (400, 220), (245, 247, 250))
    draw = ImageDraw.Draw(image)
    draw.rectangle(field, fill=(255, 255, 255), outline=(150, 160, 175))
    draw.rectangle(button, fill=fill)
    if text_box:
        draw.rectangle(text_box, fill=(40, 40, 40))
    return image


def difference(first, second, tmp_path):
    first.save(tmp_path / "a.png")
    second.save(tmp_path / "b.png")
    measured = vc.compare_images(str(tmp_path / "a.png"), str(tmp_path / "b.png"), str(tmp_path / "d.png"))
    return vr.describe(first, second, measured["regions"])


def only(regions):
    assert len(regions) >= 1
    return regions[0]


def test_a_button_in_another_colour_is_called_a_colour_difference(tmp_path):
    regions = difference(screen(), screen(fill=(194, 48, 41)), tmp_path)
    region = only(regions)
    assert region["kind"] == "colour"
    assert "#e77817" in region["detail"] and "#c23029" in region["detail"]


def test_a_field_that_moved_is_called_a_position_difference(tmp_path):
    regions = difference(screen(), screen(field=(108, 45, 308, 75)), tmp_path)
    kinds = [r["kind"] for r in regions]
    assert "position" in kinds
    moved = next(r for r in regions if r["kind"] == "position")
    assert "8 px right" in moved["detail"] and "5 px down" in moved["detail"]


def test_a_wider_button_is_called_a_size_difference(tmp_path):
    regions = difference(screen(), screen(button=(100, 100, 260, 140)), tmp_path)
    region = only(regions)
    assert region["kind"] == "size" and "width +40 px" in region["detail"] and "grew on the right" in region["detail"]


def test_an_element_that_is_missing_is_called_content(tmp_path):
    regions = difference(screen(text_box=(20, 180, 120, 200)), screen(), tmp_path)
    region = only(regions)
    assert region["kind"] == "content" and "missing on the screen" in region["detail"]
    regions = difference(screen(), screen(text_box=(20, 180, 120, 200)), tmp_path)
    assert only(regions)["detail"].startswith("present on the screen")


def test_identical_screens_have_nothing_to_describe(tmp_path):
    assert difference(screen(), screen(), tmp_path) == []


def test_the_comparison_result_carries_the_description(tmp_path, monkeypatch):
    monkeypatch.setattr(vc, "BASELINE_DIR", str(tmp_path / "b"))
    monkeypatch.setattr(vc, "REFERENCE_DIR", str(tmp_path / "r"))
    monkeypatch.setattr(vc, "RESULT_DIR", str(tmp_path / "out"))
    monkeypatch.setattr(vc, "RESULTS_FILE", str(tmp_path / "out" / "results.json"))
    (tmp_path / "r").mkdir()
    screen().save(tmp_path / "r" / "login page.png")                      # the supplied design
    screen(fill=(194, 48, 41)).save(tmp_path / "now.png")                 # the screen as built
    result = vc.check_against_baseline(str(tmp_path / "now.png"), "chromium-400x220", "login page", threshold_pct=0.1)
    assert result.status == "failed"
    assert result.regions[0]["kind"] == "colour"
    assert "colour at" in vr.summary(result.regions)


def test_summary_is_one_short_line():
    regions = [{"x": 1, "y": 2, "kind": "colour", "detail": "#aaa -> #bbb"}] * 6
    line = vr.summary(regions, limit=2)
    assert line.count("colour at (1, 2)") == 2 and line.endswith("and 4 more")
    assert vr.summary([{"x": 1, "y": 2}]) == ""


def test_a_wider_button_in_another_colour_gets_both_findings(tmp_path):
    regions = difference(screen(), screen(button=(100, 100, 260, 140), fill=(194, 48, 41)), tmp_path)
    detail = only(regions)["detail"]
    assert only(regions)["kind"] == "size" and "width 121 -> 161 px" in detail         # the whole button differs, so both widths
    assert "the colour also changed #e77817 -> #c23029" in detail


def test_a_field_far_out_of_line_is_still_a_move(tmp_path):
    regions = difference(screen(), screen(field=(114, 40, 314, 70)), tmp_path)           # 14 px to the right
    moved = [r for r in regions if r["kind"] == "position"]
    assert moved and all("14 px right" in r["detail"] for r in moved)


def test_a_removed_element_is_never_mistaken_for_a_move(tmp_path):
    regions = difference(screen(text_box=(20, 150, 80, 170)), screen(), tmp_path)        # a block just disappears
    assert regions and all(r["kind"] != "position" for r in regions)


def test_jpeg_compression_noise_is_not_reported_but_a_real_colour_change_is(tmp_path):
    first, second = screen(), screen(fill=(228, 124, 30))                              # a few levels: what a JPEG does to a colour
    first.save(tmp_path / "a.png")
    second.save(tmp_path / "b.png")
    measured = vc.compare_images(str(tmp_path / "a.png"), str(tmp_path / "b.png"), str(tmp_path / "d.png"), 1)
    assert measured["regions"]
    assert vr.describe(first, second, [dict(r) for r in measured["regions"]], 1, lossy=True) == []
    assert vr.describe(first, second, [dict(r) for r in measured["regions"]], 1)[0]["kind"] == "colour"      # a PNG design: reported
    real = screen(fill=(194, 48, 41))
    assert vr.describe(first, real, difference_regions(first, real, tmp_path), 10, lossy=True)[0]["kind"] == "colour"


def difference_regions(first, second, tmp_path):
    first.save(tmp_path / "c.png")
    second.save(tmp_path / "e.png")
    return vc.compare_images(str(tmp_path / "c.png"), str(tmp_path / "e.png"), str(tmp_path / "f.png"))["regions"]
