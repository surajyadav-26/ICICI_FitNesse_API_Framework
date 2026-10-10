"""The standalone HTML report of a visual comparison."""
import os

from PIL import Image, ImageDraw

from core import visual_compare as vc
from core import visual_report


def shot(path, size=(300, 200), boxes=()):
    image = Image.new("RGB", size, (255, 255, 255))
    for box in boxes:
        ImageDraw.Draw(image).rectangle(box, fill=(0, 0, 0))
    image.save(path)
    return str(path)


def mask_with(boxes, size=(300, 200)):
    mask = Image.new("L", size, 0)
    for box in boxes:
        ImageDraw.Draw(mask).rectangle(box, fill=255)
    return mask


def test_regions_are_found_per_area_biggest_first():
    regions = visual_report.find_regions(mask_with([(10, 10, 29, 19), (200, 120, 279, 189)]))
    assert len(regions) == 2
    assert regions[0] == {"x": 200, "y": 120, "width": 80, "height": 70, "pixels": 80 * 70}
    assert regions[1]["x"] == 10 and regions[1]["width"] == 20 and regions[1]["height"] == 10


def test_nearby_pixels_are_one_area_and_a_clean_mask_has_none():
    assert len(visual_report.find_regions(mask_with([(10, 10, 20, 20), (30, 10, 40, 20)]))) == 1
    assert visual_report.find_regions(mask_with([])) == []


def test_comparison_records_the_regions(tmp_path, monkeypatch):
    monkeypatch.setattr(vc, "BASELINE_DIR", str(tmp_path / "b"))
    monkeypatch.setattr(vc, "REFERENCE_DIR", str(tmp_path / "r"))
    monkeypatch.setattr(vc, "RESULT_DIR", str(tmp_path / "out"))
    monkeypatch.setattr(vc, "RESULTS_FILE", str(tmp_path / "out" / "results.json"))
    vc.check_against_baseline(shot(tmp_path / "a.png"), "p", "home")
    result = vc.check_against_baseline(shot(tmp_path / "b.png", boxes=[(20, 20, 79, 59)]), "p", "home")
    assert result.status == "failed" and len(result.regions) == 1
    assert result.regions[0]["x"] == 20 and result.regions[0]["width"] == 60
    assert result.to_dict()["regions"][0]["pixels"] == 60 * 40


def test_report_is_one_file_with_images_regions_and_a_defect_text(tmp_path, monkeypatch):
    monkeypatch.setattr(vc, "BASELINE_DIR", str(tmp_path / "b"))
    monkeypatch.setattr(vc, "REFERENCE_DIR", str(tmp_path / "r"))
    monkeypatch.setattr(vc, "RESULT_DIR", str(tmp_path / "out"))
    monkeypatch.setattr(vc, "RESULTS_FILE", str(tmp_path / "out" / "results.json"))
    vc.check_against_baseline(shot(tmp_path / "a.png"), "chromium-300x200", "login page")
    result = vc.check_against_baseline(shot(tmp_path / "b.png", boxes=[(20, 20, 79, 59)]), "chromium-300x200", "login page")
    folder = vc.result_dir("chromium-300x200", result.name)
    path = visual_report.write_report(result, folder, {"url": "http://x/login?a=<b>", "test": "LoginPage",
                                                         "baseline_source": "reference image", "pixel_tolerance": 10})
    page = open(path, encoding="utf-8").read()
    assert os.path.basename(path) == "report.html" and os.path.getsize(path) < 400_000
    assert page.count("data:image/jpeg;base64,") >= 5               # baseline, actual, marked, diff, crops
    assert "MISMATCH" in page and "Area 1: x=20, y=20, 60&times;40 px" in page
    assert "http://x/login?a=&lt;b&gt;" in page and "?a=<b>" not in page
    assert "[Visual] &#x27;login page&#x27; differs from its baseline" in page
    assert visual_report.report_url("chromium-300x200", "login page") == "/files/testResults/visual/chromium-300x200/login%20page/report.html"
