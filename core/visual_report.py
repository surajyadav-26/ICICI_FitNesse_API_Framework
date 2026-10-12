"""
The standalone HTML report of one visual comparison: what differs, where, and a ready-to-paste defect description.

    regions = find_regions(mask)                       # boxes around the differing areas (used by core/visual_compare.py)
    path = write_report(result, folder, context)       # <folder>/report.html, one self-contained file (images embedded)

The report is a single file on purpose: a QA engineer can attach it to a defect as it is.
"""
import base64
import html
import io
import os
import time

from PIL import Image, ImageDraw

CELL = 24                 # differing pixels are grouped on a grid of CELL x CELL pixels
GAP = 2                   # cells closer than this many cells belong to the same region
MAX_REGIONS = 25          # regions listed; the rest are counted
MAX_CROPS = 8             # regions shown with baseline / actual crops
EMBED_WIDTH = 1600        # embedded screenshots are scaled down to this width


# ── regions ───────────────────────────────────────────────────────────────────
def find_regions(mask: Image.Image) -> list:
    """Boxes around the differing areas of a 0/255 mask: [{x, y, width, height, pixels}], biggest first."""
    import numpy

    flags = numpy.asarray(mask.convert("L")) > 0
    height, width = flags.shape
    if not flags.any():
        return []
    rows, cols = -(-height // CELL), -(-width // CELL)
    padded = numpy.zeros((rows * CELL, cols * CELL), dtype=bool)
    padded[:height, :width] = flags
    cells = padded.reshape(rows, CELL, cols, CELL).any(axis=(1, 3))

    seen = numpy.zeros_like(cells, dtype=bool)
    regions = []
    for start_row, start_col in zip(*numpy.nonzero(cells)):
        if seen[start_row, start_col]:
            continue
        stack, members = [(start_row, start_col)], []
        seen[start_row, start_col] = True
        while stack:
            row, col = stack.pop()
            members.append((row, col))
            for next_row in range(max(row - GAP, 0), min(row + GAP + 1, rows)):
                for next_col in range(max(col - GAP, 0), min(col + GAP + 1, cols)):
                    if cells[next_row, next_col] and not seen[next_row, next_col]:
                        seen[next_row, next_col] = True
                        stack.append((next_row, next_col))
        top, bottom = min(m[0] for m in members) * CELL, min(max(m[0] for m in members) * CELL + CELL, height)
        left, right = min(m[1] for m in members) * CELL, min(max(m[1] for m in members) * CELL + CELL, width)
        inside = flags[top:bottom, left:right]
        ys, xs = numpy.nonzero(inside)                       # tighten the box to the pixels that really differ
        regions.append({"x": int(left + xs.min()), "y": int(top + ys.min()),
                        "width": int(xs.max() - xs.min() + 1), "height": int(ys.max() - ys.min() + 1),
                        "pixels": int(inside.sum())})
    regions.sort(key=lambda region: -region["pixels"])
    return regions


# ── pieces of the report ──────────────────────────────────────────────────────
def _data_uri(image: Image.Image, max_width: int = EMBED_WIDTH) -> str:
    image = image.convert("RGB")
    if image.width > max_width:
        image = image.resize((max_width, max(1, round(image.height * max_width / image.width))), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=88)                  # a screenshot as PNG is several MB; JPEG keeps the report small
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _annotated(actual: Image.Image, regions: list) -> Image.Image:
    image = actual.convert("RGB").copy()
    draw = ImageDraw.Draw(image)
    line = max(2, image.width // 400)
    for number, region in enumerate(regions, 1):
        box = (region["x"] - 4, region["y"] - 4, region["x"] + region["width"] + 4, region["y"] + region["height"] + 4)
        draw.rectangle(box, outline=(231, 40, 40), width=line)
        label = str(number)
        size = max(18, image.width // 90)
        draw.rectangle((box[0], max(box[1] - size, 0), box[0] + size * len(label) * 0.7 + 8, max(box[1] - size, 0) + size),
                       fill=(231, 40, 40))
        draw.text((box[0] + 4, max(box[1] - size, 0) + 2), label, fill=(255, 255, 255))
    return image


def _crop(image: Image.Image, region: dict, pad: int = 14, max_width: int = 420, max_height: int = 300) -> Image.Image:
    left, top = max(region["x"] - pad, 0), max(region["y"] - pad, 0)
    right = min(region["x"] + region["width"] + pad, image.width)
    bottom = min(region["y"] + region["height"] + pad, image.height)
    piece = image.convert("RGB").crop((left, top, right, bottom))
    scale = min(1.0, max_width / piece.width, max_height / piece.height)
    if scale < 1.0:
        piece = piece.resize((max(1, round(piece.width * scale)), max(1, round(piece.height * scale))), Image.LANCZOS)
    return piece


def defect_text(result, context: dict, regions: list) -> str:
    """Plain text a tester can paste into a defect."""
    lines = [
        f"[Visual] '{result.name}' differs from its baseline by {result.mismatch_pct}%" if result.status == "failed"
        else f"[Visual] '{result.name}' - {result.status}",
        "",
        f"Page: {context.get('url', '')}",
        f"Environment: {result.profile}",
        f"Baseline: {context.get('baseline_source', '')}",
        f"Result: {result.message}",
        f"Differing pixels: {result.diff_pixels} of {result.total_pixels} ({result.mismatch_pct}%), allowed {result.threshold_pct}%",
    ]
    if regions:
        lines.append(f"Differences ({len(regions)} area(s)):")
        for number, region in enumerate(regions[:MAX_CROPS], 1):
            lines.append(f"  {number}. at x={region['x']}, y={region['y']}, size {region['width']}x{region['height']} px")
    lines += ["", f"Test: {context.get('test') or result.test}", f"Run time: {result.timestamp}",
              "Evidence: attach this report file (baseline, actual and diff are inside it)."]
    return "\n".join(lines)


_STATUS_TEXT = {"failed": "MISMATCH", "passed": "MATCH", "new": "NEW BASELINE", "updated": "BASELINE UPDATED"}

_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Visual Regression Report - __NAME__</title>
<style>
:root { --red:#C23029; --orange:#E77817; --dark:#97291E; --ink:#0A192F; --slate:#5C6E89; --line:#E5E8EB; --green:#1E7A4C; }
* { box-sizing:border-box; }
body { margin:0; background:#F9F9F9; color:var(--ink); font-family:Arial,sans-serif; font-size:14px; }
header { background:#fff; border-bottom:3px solid var(--orange); padding:16px 28px; display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
h1 { margin:0; font-size:20px; } h2 { font-size:15px; margin:26px 0 10px; color:var(--dark); text-transform:uppercase; letter-spacing:.4px; }
.badge { padding:4px 12px; border-radius:6px; font-weight:800; font-size:12px; }
.badge.failed { background:#FBDADA; color:#B3261E; } .badge.passed { background:#DCFCE7; color:var(--green); }
.badge.new, .badge.updated { background:#F7DCC5; color:var(--dark); }
main { max-width:1300px; margin:20px auto; padding:0 24px 60px; }
.cards { display:flex; gap:12px; flex-wrap:wrap; }
.card { flex:1; min-width:150px; background:#fff; border:1px solid var(--line); border-top:4px solid var(--orange); border-radius:10px; padding:12px 16px; }
.card span { font-size:11px; font-weight:800; color:var(--slate); text-transform:uppercase; } .card b { display:block; font-size:22px; margin-top:4px; }
.card.bad { border-top-color:#DC3434; } .card.bad b { color:#B3261E; } .card.good { border-top-color:var(--green); } .card.good b { color:var(--green); }
table { border-collapse:collapse; background:#fff; border:1px solid var(--line); width:100%; }
th, td { text-align:left; padding:8px 12px; border-top:1px solid var(--line); vertical-align:top; } th { width:200px; color:var(--slate); background:#FCEEE2; }
.tabs { display:flex; gap:6px; margin-bottom:10px; flex-wrap:wrap; }
.tab { border:1.5px solid var(--line); background:#fff; border-radius:8px; padding:6px 14px; font-weight:800; font-size:12px; cursor:pointer; color:var(--slate); }
.tab.active { border-color:var(--orange); background:#FCEEE2; color:var(--dark); }
.view { display:none; } .view.active { display:block; } .view.side.active { display:flex; gap:14px; }
figure { margin:0; flex:1; min-width:0; } figcaption { font-size:11px; font-weight:800; color:var(--slate); text-transform:uppercase; margin-bottom:6px; }
figure img, .single img { width:100%; display:block; border:1px solid var(--line); border-radius:6px; background:#fff; }
.slide { position:relative; max-width:1000px; line-height:0; } .slide .top { position:absolute; inset:0; clip-path:inset(0 50% 0 0); }
.slide img { width:100%; display:block; } .slide input { position:absolute; left:0; right:0; bottom:-28px; width:100%; accent-color:var(--orange); }
.slide .handle { position:absolute; top:0; bottom:0; left:50%; width:2px; background:var(--orange); pointer-events:none; }
.region { background:#fff; border:1px solid var(--line); border-left:5px solid #DC3434; border-radius:10px; padding:12px 16px; margin-bottom:12px; }
.region h3 { margin:0 0 8px; font-size:14px; } .pair { display:flex; gap:14px; flex-wrap:wrap; } .pair figure { flex:0 1 420px; }
textarea { width:100%; min-height:210px; font-family:Consolas,monospace; font-size:12px; padding:10px; border:1px solid var(--line); border-radius:8px; }
button.copy { margin-top:8px; border:none; background:linear-gradient(90deg,var(--red),#EA761B); color:#fff; font-weight:800; border-radius:8px; padding:9px 18px; cursor:pointer; }
.note { color:var(--slate); font-size:12px; }
</style></head><body>
<header><h1>Visual Regression Report - __NAME__</h1><span class="badge __STATUS__">__STATUS_TEXT__</span>
<span class="note">__TIME__ &middot; __PROFILE__</span></header>
<main>
<div class="cards">
<div class="card __DIFFCLASS__"><span>Difference</span><b>__PCT__%</b></div>
<div class="card"><span>Allowed</span><b>__THRESHOLD__%</b></div>
<div class="card"><span>Differing pixels</span><b>__PIXELS__</b></div>
<div class="card"><span>Areas</span><b>__AREAS__</b></div>
<div class="card"><span>Image size</span><b style="font-size:16px">__SIZE__</b></div>
</div>
<h2>Details</h2>
<table>__DETAILS__</table>
__REGIONS__
<h2>Compare</h2>
<div class="tabs">
<button class="tab active" data-view="side">Side by side</button><button class="tab" data-view="marked">Differences marked</button>
<button class="tab" data-view="slider">Slider</button><button class="tab" data-view="diff">Diff</button>
</div>
<div class="view side active"><figure><figcaption>Baseline (expected)</figcaption><img src="__BASELINE__" alt="baseline"></figure>
<figure><figcaption>Actual (this run)</figcaption><img src="__ACTUAL__" alt="actual"></figure></div>
<div class="view marked single"><img src="__MARKED__" alt="actual with the differences marked"></div>
<div class="view slider"><div class="slide"><img src="__BASELINE__" alt=""><div class="top"><img src="__ACTUAL__" alt=""></div>
<input type="range" min="0" max="100" value="50" oninput="slide(this)"><span class="handle"></span></div>
<p class="note" style="margin-top:36px">Drag the slider: left = actual, right = baseline.</p></div>
<div class="view diff single"><img src="__DIFF__" alt="difference"></div>
<h2>Defect description</h2>
<textarea id="defect" readonly>__DEFECT__</textarea><br><button class="copy" onclick="copyDefect()">Copy description</button>
<p class="note">This file contains the baseline, actual and difference images, so attaching it to the defect is enough.</p>
</main>
<script>
document.querySelectorAll('.tab').forEach(function(tab) { tab.onclick = function() {
  document.querySelectorAll('.tab').forEach(function(t) { t.classList.remove('active'); }); tab.classList.add('active');
  document.querySelectorAll('.view').forEach(function(v) { v.classList.toggle('active', v.classList.contains(tab.dataset.view)); }); }; });
function slide(input) { var box = input.parentNode; box.querySelector('.top').style.clipPath = 'inset(0 ' + (100 - input.value) + '% 0 0)';
  box.querySelector('.handle').style.left = input.value + '%'; }
function copyDefect() { var box = document.getElementById('defect'); box.select(); document.execCommand('copy'); }
</script></body></html>"""


def write_report(result, folder: str, context: dict = None) -> str:
    """Writes <folder>/report.html from baseline.png, actual.png and diff.png; returns its path."""
    context = context or {}
    esc = html.escape
    baseline = Image.open(os.path.join(folder, "baseline.png"))
    actual = Image.open(os.path.join(folder, "actual.png"))
    diff_path = os.path.join(folder, "diff.png")
    regions = list(getattr(result, "regions", None) or [])

    marked = _annotated(actual, regions[:MAX_REGIONS])
    diff = Image.open(diff_path) if os.path.isfile(diff_path) and result.status == "failed" else marked

    region_html = ""
    if regions:
        shown = regions[:MAX_CROPS]
        region_html = "<h2>What changed</h2>"
        for number, region in enumerate(shown, 1):
            region_html += (
                f"<div class='region'><h3>Area {number}: x={region['x']}, y={region['y']}, "
                f"{region['width']}&times;{region['height']} px, {region['pixels']} pixel(s)</h3><div class='pair'>"
                f"<figure><figcaption>Baseline</figcaption><img src='{_data_uri(_crop(baseline, region))}'></figure>"
                f"<figure><figcaption>Actual</figcaption><img src='{_data_uri(_crop(actual, region))}'></figure></div></div>")
        if len(regions) > len(shown):
            region_html += f"<p class='note'>... and {len(regions) - len(shown)} more area(s); see the marked image.</p>"

    detail_rows = [
        ("Page", context.get("url", "")), ("Test", context.get("test") or result.test),
        ("Baseline", context.get("baseline_source", "")), ("Environment", result.profile),
        ("Result", result.message), ("Pixel tolerance", f"{context.get('pixel_tolerance', '')} of 255 per colour channel"),
        ("Run time", result.timestamp),
    ]
    details = "".join(f"<tr><th>{esc(str(key))}</th><td>{esc(str(value))}</td></tr>" for key, value in detail_rows if value != "")
    size = f"{result.actual_size[0]}&times;{result.actual_size[1]}" if result.actual_size[0] else ""

    page = _TEMPLATE
    if result.status == "passed":
        start, end = page.index("<h2>Compare</h2>"), page.index("<h2>Defect description</h2>")
        page = (page[:start] + "<h2>Screenshot</h2><div class=\"view single active\"><img src=\"__ACTUAL__\" alt=\"actual\"></div>\n"
                + page[end:])
        page = page.replace('<button class="tab', '<button hidden class="tab')       # no tabs without a comparison
    for key, value in {
        "__NAME__": esc(result.name), "__STATUS_TEXT__": _STATUS_TEXT.get(result.status, result.status.upper()),
        "__STATUS__": esc(result.status), "__TIME__": esc(result.timestamp), "__PROFILE__": esc(result.profile),
        "__DIFFCLASS__": "bad" if result.status == "failed" else "good", "__PCT__": str(result.mismatch_pct),
        "__THRESHOLD__": str(result.threshold_pct), "__PIXELS__": f"{result.diff_pixels:,}", "__AREAS__": str(len(regions)),
        "__SIZE__": size, "__DETAILS__": details, "__REGIONS__": region_html,
        "__BASELINE__": _data_uri(baseline) if "__BASELINE__" in page else "", "__ACTUAL__": _data_uri(actual),
        "__MARKED__": _data_uri(marked) if "__MARKED__" in page else "",
        "__DIFF__": _data_uri(diff) if "__DIFF__" in page else "", "__DEFECT__": esc(defect_text(result, context, regions)),
    }.items():
        page = page.replace(key, value)
    path = os.path.join(folder, "report.html")
    with open(path, "w", encoding="utf-8") as report:
        report.write(page)
    return path


def write_index(folder: str = None, results: list = None) -> str:
    """Writes <results folder>/index.html listing the latest comparisons, each linking to its own report.html (relative links)."""
    from urllib.parse import quote
    from core import visual_compare
    from core.config import Config

    folder = folder or visual_compare.RESULT_DIR
    items = results if results is not None else visual_compare.list_results()
    esc = html.escape
    counts = {key: sum(1 for item in items if item.get("status") == key) for key in ("failed", "new", "updated", "passed")}
    rows = ""
    for item in items:
        link = f"{quote(item['profile'])}/{quote(item['name'])}/report.html"
        status = item.get("status", "")
        rows += (f"<tr><td><span class='badge {esc(status)}'>{esc(_STATUS_TEXT.get(status, status.upper()))}</span></td>"
                 f"<td>{esc(item.get('name', ''))}</td><td>{esc(item.get('profile', ''))}</td>"
                 f"<td>{item.get('mismatch_pct', 0)}%</td><td>{esc(item.get('message', ''))}</td>"
                 f"<td><a href='{link}'>Open report</a></td></tr>")
    if not rows:
        rows = "<tr><td colspan='6' style='text-align:center;padding:24px'>No visual comparisons in this run.</td></tr>"
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(Config.APP_NAME)} - Visual Regression Results</title>
<style>
body {{ margin:0; background:#F9F9F9; color:#0A192F; font-family:Arial,sans-serif; font-size:14px; }}
header {{ background:#fff; border-bottom:3px solid #E77817; padding:16px 28px; }} h1 {{ margin:0; font-size:20px; }}
main {{ max-width:1200px; margin:20px auto; padding:0 20px 50px; }}
.cards {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:18px; }}
.card {{ flex:1; min-width:140px; background:#fff; border:1px solid #E5E8EB; border-top:4px solid #E77817; border-radius:10px; padding:12px 16px; }}
.card b {{ display:block; font-size:24px; margin-top:4px; }}
table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid #E5E8EB; }}
th {{ text-align:left; background:#FCEEE2; color:#97291E; font-size:11px; text-transform:uppercase; padding:10px 12px; }}
td {{ padding:10px 12px; border-top:1px solid #E5E8EB; }} a {{ color:#C23029; font-weight:700; }}
.badge {{ padding:2px 10px; border-radius:6px; font-size:11px; font-weight:800; }}
.badge.failed {{ background:#FBDADA; color:#B3261E; }} .badge.passed {{ background:#DCFCE7; color:#15803D; }}
.badge.new, .badge.updated {{ background:#F7DCC5; color:#97291E; }}
</style></head><body>
<header><h1>{esc(Config.APP_NAME)} - Visual Regression Results</h1></header>
<main>
<div class="cards"><div class="card">Mismatch<b>{counts['failed']}</b></div><div class="card">Match<b>{counts['passed']}</b></div>
<div class="card">New baseline<b>{counts['new']}</b></div><div class="card">Updated<b>{counts['updated']}</b></div></div>
<table><tr><th>Status</th><th>Name</th><th>Browser / viewport</th><th>Difference</th><th>Result</th><th>Report</th></tr>{rows}</table>
</main></body></html>"""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "index.html")
    with open(path, "w", encoding="utf-8") as index:
        index.write(page)
    return path


def report_url(profile: str, name: str) -> str:
    """Address of the report below FitNesse's /files folder (relative, so it works on any host)."""
    from urllib.parse import quote
    return f"/files/testResults/visual/{quote(profile)}/{quote(name)}/report.html"
