"""Passing a reference image: by name, by a file in fixtures/visual/baseline, or by a full path; PNG or JPEG."""
import os

import pytest
from PIL import Image, ImageDraw

from core import visual_compare as vc


@pytest.fixture(autouse=True)
def stores(tmp_path, monkeypatch):
    monkeypatch.setattr(vc, "BASELINE_DIR", str(tmp_path / "baselines"))
    monkeypatch.setattr(vc, "REFERENCE_DIR", str(tmp_path / "reference"))
    monkeypatch.setattr(vc, "RESULT_DIR", str(tmp_path / "results"))
    monkeypatch.setattr(vc, "RESULTS_FILE", str(tmp_path / "results" / "results.json"))
    (tmp_path / "reference").mkdir()
    return tmp_path


def picture(path, color=(240, 240, 240), box=None, box_color=(30, 30, 30), size=(200, 100)):
    image = Image.new("RGB", size, color)
    if box:
        ImageDraw.Draw(image).rectangle(box, fill=box_color)
    image.save(path)
    return str(path)


def test_the_name_finds_a_png_or_jpeg_in_the_reference_folder(stores):
    assert vc.find_reference("login page") == ""
    picture(stores / "reference" / "login page.jpg")
    assert vc.find_reference("login page").endswith("login page.jpg")
    picture(stores / "reference" / "login page.png")
    assert vc.find_reference("login page").endswith("login page.png")                # png wins when both exist


def test_an_explicit_reference_may_be_a_subfolder_without_an_extension_or_a_full_path(stores):
    (stores / "reference" / "designs" / "v2").mkdir(parents=True)
    picture(stores / "reference" / "designs" / "v2" / "login.png")
    assert vc.find_reference("", "designs/v2/login.png").endswith("login.png")
    assert vc.find_reference("", "designs/v2/login").endswith("login.png")           # the extension may be left out
    elsewhere = picture(stores / "elsewhere.jpeg")
    assert vc.find_reference("", elsewhere) == elsewhere                             # any full path on the machine
    assert vc.find_reference("", "designs/missing.png") == ""
    assert vc.find_reference("", "designs/v2/login.txt") == ""


def test_a_named_reference_is_compared_and_never_overwritten(stores):
    design = picture(stores / "design.jpg", box=(10, 10, 60, 40))
    before = open(design, "rb").read()
    shot = picture(stores / "now.png", box=(10, 10, 60, 40))
    result = vc.check_against_baseline(shot, "chromium-200x100", "home", reference_file=design, update=True, threshold_pct=5)   # JPEG blurs edges
    assert result.status == "passed"                                                   # `update` is ignored for a named design
    assert open(design, "rb").read() == before
    assert result.baseline_source == f"reference image {design}"                       # outside the folder: the full path
    assert not os.path.exists(vc.baseline_path("chromium-200x100", "home"))            # nothing was created next to it


def test_a_jpeg_reference_is_shown_in_the_report_as_a_real_png(stores):
    design = picture(stores / "design.jpg")
    shot = picture(stores / "now.png", box=(0, 0, 99, 49))
    vc.check_against_baseline(shot, "p", "home", reference_file=design)
    shown = os.path.join(vc.result_dir("p", "home"), "baseline.png")
    with open(shown, "rb") as handle:
        assert handle.read(8) == b"\x89PNG\r\n\x1a\n"


def test_a_missing_named_reference_is_an_error_not_a_new_baseline(stores):
    shot = picture(stores / "now.png")
    with pytest.raises(FileNotFoundError, match="Reference image not found"):
        vc.check_against_baseline(shot, "p", "home", reference_file=str(stores / "nope.png"))
    assert not os.path.exists(vc.baseline_path("p", "home"))


def test_the_source_inside_the_folder_is_shown_relative(stores):
    (stores / "reference" / "designs").mkdir()
    design = picture(stores / "reference" / "designs" / "login.png")
    shot = picture(stores / "now.png")
    result = vc.check_against_baseline(shot, "p", "home", reference_file=design)
    assert result.baseline_source == "reference image designs/login.png"


def test_approving_a_jpeg_reference_keeps_it_a_jpeg(stores):
    picture(stores / "reference" / "home.jpg")
    shot = picture(stores / "now.png", box=(0, 0, 100, 50))
    vc.check_against_baseline(shot, "p", "home")                                       # fails: the name finds home.jpg
    vc.approve("p", "home")
    with Image.open(stores / "reference" / "home.jpg") as image:
        assert image.format == "JPEG"
    assert not os.path.exists(stores / "reference" / "home.png")
