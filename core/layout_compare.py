"""
Layout check: compares the position, size and colours of chosen elements instead of pixels, so a change of text or of an
image does not matter but a moved field, a resized box or a changed colour does.

    snapshot = capture(page, locator_for, ["LoginPage.username", "css=.logo"])    # browser part
    differences = compare(baseline_snapshot, snapshot, tolerance=2)                # pure, no browser
    result = check(snapshot, profile, name, tolerance)                             # baseline bookkeeping + report

Layout
    fixtures/visual/layout/<name>.json                       reference values you wrote or copied (used for every browser)
    data/visual/layouts/<profile>/<name>.json                snapshot the framework stored on the first run (commit these)
    FitNesseRoot/files/testResults/layout/<profile>/<name>/  report.html and result.json of the latest run
"""
import html
import json
import os
import re
import time
from urllib.parse import quote

from core.config import Config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_DIR = os.path.join(BASE_DIR, "data", "visual", "layouts")
REFERENCE_DIR = os.path.join(BASE_DIR, "fixtures", "visual", "layout")
RESULT_DIR = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "layout")

GEOMETRY = ("x", "y", "width", "height")
STYLES = ("color", "backgroundColor", "borderColor", "borderWidth", "fontSize", "fontWeight", "fontFamily", "textAlign")
_LABEL = {"x": "left position", "y": "top position", "width": "width", "height": "height", "color": "text colour",
          "backgroundColor": "background colour", "borderColor": "border colour", "borderWidth": "border width",
          "fontSize": "font size", "fontWeight": "font weight", "fontFamily": "font", "textAlign": "text alignment"}
_NAME = re.compile(r"^[A-Za-z0-9][\w\- .]{0,80}$")

_CAPTURE_JS = """element => {
  const box = element.getBoundingClientRect(), s = getComputedStyle(element);
  return {x: box.x + window.scrollX, y: box.y + window.scrollY, width: box.width, height: box.height,
          color: s.color, backgroundColor: s.backgroundColor, borderColor: s.borderTopColor, borderWidth: s.borderTopWidth,
          fontSize: s.fontSize, fontWeight: s.fontWeight, fontFamily: s.fontFamily, textAlign: s.textAlign};
}"""


def clean_name(name: str) -> str:
    cleaned = str(name or "").strip()
    if not _NAME.match(cleaned) or ".." in cleaned:
        raise ValueError(f"Invalid layout name '{name}': use letters, numbers, spaces, '-', '_' or '.'")
    return cleaned


def clean_profile(profile: str) -> str:
    cleaned = str(profile or "").strip()
    if not re.fullmatch(r"[\w\-]{1,60}", cleaned):
        raise ValueError(f"Invalid layout profile '{profile}'")
    return cleaned


def normalize_color(value: str) -> str:
    """rgb(0, 0, 0) -> #000000; a fully transparent colour -> transparent; anything else is returned as it is."""
    match = re.fullmatch(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)", str(value).strip())
    if not match:
        return str(value).strip()
    red, green, blue, alpha = match.groups()
    if alpha is not None and float(alpha) == 0:
        return "transparent"
    return "#{:02x}{:02x}{:02x}".format(int(red), int(green), int(blue))


def normalize(raw: dict) -> dict:
    """One element's measured values in the form that is stored and compared."""
    item = {}
    for key in GEOMETRY:
        item[key] = round(float(raw.get(key, 0)), 1)
    for key in STYLES:
        value = str(raw.get(key, "")).strip()
        item[key] = normalize_color(value) if key in ("color", "backgroundColor", "borderColor") else value
    return item


# ── browser part ──────────────────────────────────────────────────────────────
def capture(locator_for, names: list) -> dict:
    """Measures every named element on the current page. locator_for(name) returns a Playwright locator."""
    snapshot = {}
    for name in names:
        try:
            locator = locator_for(name).first
            locator.wait_for(state="visible", timeout=5000)
            snapshot[name] = normalize(locator.evaluate(_CAPTURE_JS))
        except Exception as error:
            snapshot[name] = {"missing": True, "reason": str(error).splitlines()[0][:160] if str(error) else "not found"}
    return snapshot


# ── comparison (no browser) ───────────────────────────────────────────────────
def compare(baseline: dict, actual: dict, tolerance: float = 2.0) -> list:
    """Differences between two snapshots: [{element, property, expected, actual, message}]."""
    differences = []
    for element, expected in baseline.items():
        found = actual.get(element)
        if found is None or found.get("missing"):
            differences.append({"element": element, "property": "presence", "expected": "visible", "actual": "not found",
                                "message": f"{element}: the element was not found on the page"})
            continue
        if expected.get("missing"):
            continue                                    # the baseline never had it; nothing to compare
        for key in GEOMETRY:
            if abs(float(found[key]) - float(expected[key])) > tolerance:
                differences.append({"element": element, "property": key, "expected": expected[key], "actual": found[key],
                                    "message": f"{element}: {_LABEL[key]} {expected[key]} -> {found[key]} (allowed +/-{tolerance:g} px)"})
        for key in STYLES:
            if key in expected and found.get(key) != expected[key]:
                differences.append({"element": element, "property": key, "expected": expected[key], "actual": found.get(key, ""),
                                    "message": f"{element}: {_LABEL[key]} {expected[key]} -> {found.get(key, '')}"})
    for element in actual:
        if element not in baseline:
            differences.append({"element": element, "property": "presence", "expected": "not in the baseline", "actual": "added",
                                "message": f"{element}: is not in the baseline (update the baseline to include it)"})
    return differences


# ── baselines and results ─────────────────────────────────────────────────────
def reference_path(name: str) -> str:
    return os.path.join(REFERENCE_DIR, f"{clean_name(name)}.json")


def baseline_path(profile: str, name: str) -> str:
    return os.path.join(BASELINE_DIR, clean_profile(profile), f"{clean_name(name)}.json")


def result_dir(profile: str, name: str) -> str:
    return os.path.join(RESULT_DIR, clean_profile(profile), clean_name(name))


def report_url(profile: str, name: str) -> str:
    return f"/files/testResults/layout/{quote(profile)}/{quote(name)}/report.html"


def _read(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as stored:
        data = json.load(stored)
    return data.get("elements", data) if isinstance(data, dict) else {}


def _write(path: str, snapshot: dict, profile: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as stored:
        json.dump({"profile": profile, "saved": time.strftime("%Y-%m-%d %H:%M:%S"), "elements": snapshot}, stored, indent=2)


def check(snapshot: dict, profile: str, name: str, tolerance: float = 2.0, update: bool = False, context: dict = None) -> dict:
    """
    Compares the snapshot with the stored values and writes the report.
      * no baseline yet -> the snapshot becomes the baseline, status "new"
      * update=True     -> the snapshot replaces the baseline, status "updated"
      * otherwise       -> status "passed" or "failed" with the list of differences
    A reference file in fixtures/visual/layout wins over the per-profile snapshot.
    """
    reference = reference_path(name)
    target = reference if os.path.isfile(reference) else baseline_path(profile, name)
    source = "reference file fixtures/visual/layout/" + os.path.basename(reference) if target == reference else f"stored baseline ({profile})"
    differences, status, message = [], "passed", "Matches the baseline"
    if update or not os.path.isfile(target):
        _write(target, snapshot, profile)
        status = "updated" if update else "new"
        message = "Baseline updated" if update else "Baseline created from this run"
    else:
        differences = compare(_read(target), snapshot, tolerance)
        if differences:
            status, message = "failed", f"{len(differences)} difference(s) in the layout"
    result = {"status": status, "name": name, "profile": profile, "tolerance": tolerance, "message": message,
              "differences": differences, "elements": len(snapshot), "baseline_source": source,
              "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "snapshot": snapshot, **(context or {})}
    folder = result_dir(profile, name)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "result.json"), "w", encoding="utf-8") as stored:
        json.dump(result, stored, indent=2)
    write_report(result, folder)
    return result


# ── report ────────────────────────────────────────────────────────────────────
def defect_text(result: dict) -> str:
    lines = [f"[Layout] '{result['name']}' differs from its baseline" if result["status"] == "failed"
             else f"[Layout] '{result['name']}' - {result['status']}", "",
             f"Page: {result.get('url', '')}", f"Environment: {result['profile']}", f"Baseline: {result['baseline_source']}",
             f"Result: {result['message']}", f"Allowed position / size difference: +/-{result['tolerance']:g} px"]
    if result["differences"]:
        lines.append("Differences:")
        lines += [f"  - {item['message']}" for item in result["differences"]]
    lines += ["", f"Test: {result.get('test', '')}", f"Run time: {result['timestamp']}"]
    return "\n".join(lines)


def write_report(result: dict, folder: str) -> str:
    esc = html.escape
    wrong = {(item["element"], item["property"]) for item in result["differences"]}
    sections = ""
    for element, values in result["snapshot"].items():
        if values.get("missing"):
            sections += (f"<h3>{esc(element)}</h3><p class='bad'>Not found on the page: {esc(values.get('reason', ''))}</p>")
            continue
        rows = "".join(
            f"<tr class='{'bad' if (element, key) in wrong else ''}'><th>{esc(_LABEL[key])}</th><td>{esc(str(values[key]))}</td></tr>"
            for key in GEOMETRY + STYLES)
        sections += f"<h3>{esc(element)}</h3><table>{rows}</table>"
    diff_rows = "".join(
        f"<tr><td>{esc(item['element'])}</td><td>{esc(_LABEL.get(item['property'], item['property']))}</td>"
        f"<td>{esc(str(item['expected']))}</td><td class='bad'>{esc(str(item['actual']))}</td></tr>" for item in result["differences"])
    if not diff_rows:
        diff_rows = "<tr><td colspan='4' style='text-align:center'>No differences.</td></tr>"
    badge = {"failed": "MISMATCH", "passed": "MATCH", "new": "NEW BASELINE", "updated": "BASELINE UPDATED"}[result["status"]]
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(Config.APP_NAME)} - Layout Report - {esc(result['name'])}</title>
<style>
body {{ margin:0; background:#F9F9F9; color:#0A192F; font-family:Arial,sans-serif; font-size:14px; }}
header {{ background:#fff; border-bottom:3px solid #E77817; padding:16px 28px; display:flex; gap:14px; align-items:center; flex-wrap:wrap; }}
h1 {{ margin:0; font-size:20px; }} h2 {{ color:#97291E; text-transform:uppercase; font-size:15px; margin:26px 0 10px; }} h3 {{ margin:18px 0 6px; }}
main {{ max-width:1100px; margin:20px auto; padding:0 24px 60px; }}
.badge {{ padding:4px 12px; border-radius:6px; font-weight:800; font-size:12px; background:{'#FBDADA' if result['status'] == 'failed' else '#DCFCE7'}; color:{'#B3261E' if result['status'] == 'failed' else '#15803D'}; }}
table {{ border-collapse:collapse; background:#fff; border:1px solid #E5E8EB; min-width:420px; }}
th, td {{ text-align:left; padding:7px 12px; border-top:1px solid #E5E8EB; }} th {{ width:200px; color:#5C6E89; background:#FCEEE2; }}
tr.bad td, td.bad, p.bad {{ color:#B3261E; font-weight:700; background:#FEE2E2; }}
textarea {{ width:100%; min-height:200px; font-family:Consolas,monospace; font-size:12px; padding:10px; border:1px solid #E5E8EB; border-radius:8px; }}
.note {{ color:#5C6E89; font-size:12px; }}
</style></head><body>
<header><h1>Layout report - {esc(result['name'])}</h1><span class="badge">{badge}</span>
<span class="note">{esc(result['timestamp'])} &middot; {esc(result['profile'])} &middot; {esc(result.get('url', ''))}</span></header>
<main>
<p>{esc(result['message'])}. Baseline: {esc(result['baseline_source'])}. Position and size may differ by +/-{result['tolerance']:g} px.</p>
<h2>Differences</h2>
<table><tr><th>Element</th><th>Property</th><th>Expected</th><th>Actual</th></tr>{diff_rows}</table>
<h2>Measured in this run</h2>{sections}
<h2>Defect description</h2><textarea readonly>{esc(defect_text(result))}</textarea>
</main></body></html>"""
    path = os.path.join(folder, "report.html")
    with open(path, "w", encoding="utf-8") as report:
        report.write(page)
    return path

