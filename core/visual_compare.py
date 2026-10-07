"""
Visual regression engine: baseline storage, image comparison and result bookkeeping.

Layout
    data/visual/baselines/<profile>/<name>.png          reviewed baselines (commit these)
    FitNesseRoot/files/testResults/visual/<profile>/<name>/{baseline,actual,diff}.png
    FitNesseRoot/files/testResults/visual/results.json  latest result per profile/name (for the Visual Review page)

<profile> is "<browser>-<width>x<height>" so Chromium 1920x1080 is never compared with Firefox 1366x768.
"""
import json
import os
import re
import shutil
import time
from dataclasses import asdict, dataclass

from PIL import Image, ImageChops, ImageEnhance

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_DIR = os.path.join(BASE_DIR, "data", "visual", "baselines")
RESULT_DIR = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "visual")
RESULTS_FILE = os.path.join(RESULT_DIR, "results.json")

_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][\w\- .]{0,80}$")


@dataclass
class VisualResult:
    status: str                    # passed | failed | new | updated
    name: str
    profile: str
    mismatch_pct: float = 0.0
    diff_pixels: int = 0
    total_pixels: int = 0
    baseline_size: tuple = (0, 0)
    actual_size: tuple = (0, 0)
    size_mismatch: bool = False
    threshold_pct: float = 0.0
    timestamp: str = ""
    test: str = ""
    message: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["baseline_size"] = list(self.baseline_size)
        data["actual_size"] = list(self.actual_size)
        return data


def clean_name(name: str) -> str:
    cleaned = str(name or "").strip()
    if not _NAME_PATTERN.match(cleaned) or ".." in cleaned:
        raise ValueError(f"Invalid visual name '{name}': use letters, numbers, spaces, '-', '_' or '.'")
    return cleaned


def clean_profile(profile: str) -> str:
    cleaned = str(profile or "").strip()
    if not re.fullmatch(r"[\w\-]{1,60}", cleaned):
        raise ValueError(f"Invalid visual profile '{profile}'")
    return cleaned


def baseline_path(profile: str, name: str) -> str:
    return os.path.join(BASELINE_DIR, clean_profile(profile), f"{clean_name(name)}.png")


def result_dir(profile: str, name: str) -> str:
    return os.path.join(RESULT_DIR, clean_profile(profile), clean_name(name))


# ── Comparison ────────────────────────────────────────────────────────────────
def compare_images(baseline_file: str, actual_file: str, diff_file: str, pixel_tolerance: int = 10) -> dict:
    """
    Compares two PNGs. A pixel differs when any colour channel moves by more than pixel_tolerance (0-255).
    Areas present in only one image (size change) count as different.
    Writes a diff image: the baseline faded, differing pixels in red. Returns the measured numbers.
    """
    baseline = Image.open(baseline_file).convert("RGB")
    actual = Image.open(actual_file).convert("RGB")
    width, height = max(baseline.width, actual.width), max(baseline.height, actual.height)
    size_mismatch = baseline.size != actual.size

    canvas_b = Image.new("RGB", (width, height), (255, 0, 255))
    canvas_a = Image.new("RGB", (width, height), (255, 0, 255))
    canvas_b.paste(baseline, (0, 0))
    canvas_a.paste(actual, (0, 0))

    channel_diffs = ImageChops.difference(canvas_b, canvas_a).split()
    strongest = channel_diffs[0]
    for channel in channel_diffs[1:]:
        strongest = ImageChops.lighter(strongest, channel)
    mask = strongest.point(lambda value: 255 if value > pixel_tolerance else 0)

    # Pixels outside either image are always different.
    outside = Image.new("L", (width, height), 255)
    outside.paste(0, (0, 0, min(baseline.width, actual.width), min(baseline.height, actual.height)))
    mask = ImageChops.lighter(mask, outside)

    diff_pixels = mask.histogram()[255]
    total_pixels = width * height

    faded = ImageEnhance.Brightness(ImageEnhance.Color(canvas_a).enhance(0.35)).enhance(1.35)
    highlight = Image.new("RGB", (width, height), (231, 40, 40))
    os.makedirs(os.path.dirname(diff_file), exist_ok=True)
    Image.composite(highlight, faded, mask).save(diff_file)

    return {
        "diff_pixels": diff_pixels,
        "total_pixels": total_pixels,
        "mismatch_pct": round(diff_pixels * 100.0 / total_pixels, 4) if total_pixels else 0.0,
        "baseline_size": baseline.size,
        "actual_size": actual.size,
        "size_mismatch": size_mismatch,
    }


def check_against_baseline(actual_file: str, profile: str, name: str, threshold_pct: float = 0.1,
                           pixel_tolerance: int = 10, update: bool = False, test: str = "") -> VisualResult:
    """
    Compares actual_file with the stored baseline.
      * no baseline yet  -> the screenshot becomes the baseline, status "new"
      * update=True      -> the screenshot replaces the baseline, status "updated"
      * otherwise        -> pixel comparison, "passed" when mismatch <= threshold_pct, else "failed"
    Artifacts for the review page are always written to the result folder.
    """
    base_file = baseline_path(profile, name)
    folder = result_dir(profile, name)
    os.makedirs(folder, exist_ok=True)
    shutil.copyfile(actual_file, os.path.join(folder, "actual.png"))
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")

    def finish(result: VisualResult) -> VisualResult:
        record_result(result)
        return result

    if update or not os.path.isfile(base_file):
        os.makedirs(os.path.dirname(base_file), exist_ok=True)
        shutil.copyfile(actual_file, base_file)
        shutil.copyfile(actual_file, os.path.join(folder, "baseline.png"))
        size = Image.open(actual_file).size
        status = "updated" if update else "new"
        for stale in ("diff.png",):
            if os.path.exists(os.path.join(folder, stale)):
                os.remove(os.path.join(folder, stale))
        return finish(VisualResult(status, name, profile, baseline_size=size, actual_size=size, threshold_pct=threshold_pct,
                                   timestamp=stamp, test=test,
                                   message="Baseline created from this run" if status == "new" else "Baseline updated"))

    shutil.copyfile(base_file, os.path.join(folder, "baseline.png"))
    measured = compare_images(base_file, actual_file, os.path.join(folder, "diff.png"), pixel_tolerance)
    passed = measured["mismatch_pct"] <= threshold_pct and not measured["size_mismatch"]
    message = "Matches baseline" if passed else (
        f"Image size changed {measured['baseline_size']} -> {measured['actual_size']}" if measured["size_mismatch"]
        else f"{measured['mismatch_pct']}% of pixels differ (allowed {threshold_pct}%)")
    return finish(VisualResult("passed" if passed else "failed", name, profile, measured["mismatch_pct"], measured["diff_pixels"],
                               measured["total_pixels"], measured["baseline_size"], measured["actual_size"],
                               measured["size_mismatch"], threshold_pct, stamp, test, message))


# ── Results index + approval (used by the Visual Review page) ────────────────
def _read_results() -> dict:
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as results_file:
            data = json.load(results_file)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_results(results: dict) -> None:
    os.makedirs(RESULT_DIR, exist_ok=True)
    temporary = RESULTS_FILE + ".tmp"
    with open(temporary, "w", encoding="utf-8") as results_file:
        json.dump(results, results_file, indent=2)
    os.replace(temporary, RESULTS_FILE)


def record_result(result: VisualResult) -> None:
    results = _read_results()
    results[f"{result.profile}/{result.name}"] = result.to_dict()
    _write_results(results)


def list_results() -> list:
    """Latest result per profile/name, failures first, then newest."""
    items = list(_read_results().values())
    order = {"failed": 0, "new": 1, "updated": 2, "passed": 3}
    items.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
    items.sort(key=lambda item: order.get(item.get("status"), 9))
    return items


def approve(profile: str, name: str) -> dict:
    """Accepts the latest screenshot as the new baseline."""
    folder = result_dir(profile, name)
    actual = os.path.join(folder, "actual.png")
    if not os.path.isfile(actual):
        raise FileNotFoundError(f"No screenshot to approve for {profile}/{name}")
    target = baseline_path(profile, name)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(actual, target)
    shutil.copyfile(actual, os.path.join(folder, "baseline.png"))
    diff = os.path.join(folder, "diff.png")
    if os.path.exists(diff):
        os.remove(diff)
    results = _read_results()
    key = f"{profile}/{name}"
    entry = results.get(key, {"name": name, "profile": profile})
    entry.update({"status": "updated", "mismatch_pct": 0.0, "diff_pixels": 0, "size_mismatch": False,
                  "message": "Baseline approved", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})
    results[key] = entry
    _write_results(results)
    return entry


def result_file(profile: str, name: str, kind: str) -> str:
    """Safe path of baseline.png / actual.png / diff.png for the review page."""
    if kind not in ("baseline", "actual", "diff"):
        raise ValueError("Unknown image kind")
    return os.path.join(result_dir(profile, name), f"{kind}.png")
