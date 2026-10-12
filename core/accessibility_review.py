"""
The Accessibility Report page: what was checked, what fails, and which rules fail most often, with a link to each full report.

Built for many pages: the list shows the latest result per page and standard (earlier runs are one tick away), is searchable
and paged, and a "most frequent issues" table says what to fix first across all pages.
"""
import html
import json
import os
import re
from urllib.parse import quote

from core import accessibility
from core.config import Config

_SAFE_NAME = re.compile(r"^[\w\-]+\.html$")
LIMIT = 1000
PAGE_SIZE = 25
TOP_ISSUES = 10


def list_runs(folder: str = None) -> list:
    """Summaries of the written reports (newest first); each has a 'file' key with the .html name."""
    folder = folder or accessibility.REPORT_DIR
    if not os.path.isdir(folder):
        return []
    runs = []
    for name in os.listdir(folder):
        if not name.endswith(".json"):
            continue
        path = os.path.join(folder, name)
        try:
            with open(path, "r", encoding="utf-8") as raw:
                summary = json.load(raw)
            summary["file"] = name[:-5] + ".html"
            summary["_mtime"] = os.path.getmtime(path)
        except (OSError, ValueError):
            continue
        if isinstance(summary, dict) and os.path.isfile(os.path.join(folder, summary["file"])):
            runs.append(summary)
    runs.sort(key=lambda item: item["_mtime"], reverse=True)
    return runs[:LIMIT]


def latest_per_page(runs: list) -> tuple:
    """(latest run of each page + standard, how many runs each has); runs must be newest first."""
    latest, counts = {}, {}
    for run in runs:
        key = (run.get("url", ""), str(run.get("wcagVersion", "")), str(run.get("wcagLevel", "")))
        counts[key] = counts.get(key, 0) + 1
        latest.setdefault(key, run)
    return latest, counts


def top_issues(latest_runs: list, limit: int = TOP_ISSUES) -> list:
    """The rules that fail most, over the latest result of every page: worst impact first, then pages, then elements."""
    rules = {}
    for run in latest_runs:
        for violation in run.get("violations", []):
            rule = rules.setdefault(violation.get("id", "?"), {
                "id": violation.get("id", "?"), "impact": violation.get("impact", "minor"), "help": violation.get("help", ""),
                "helpUrl": violation.get("helpUrl", ""), "pages": set(), "elements": 0})
            rule["pages"].add(run.get("url", ""))
            rule["elements"] += len(violation.get("nodes", []))
            seen = violation.get("impact")
            if seen in accessibility.IMPACTS and rule["impact"] in accessibility.IMPACTS \
                    and accessibility.IMPACTS.index(seen) > accessibility.IMPACTS.index(rule["impact"]):
                rule["impact"] = seen
    order = {impact: number for number, impact in enumerate(accessibility.IMPACTS)}
    ranked = sorted(rules.values(), key=lambda r: (-order.get(r["impact"], 0), -len(r["pages"]), -r["elements"], r["id"]))
    return ranked[:limit]


def report_path(file_name: str, folder: str = None) -> str:
    """Absolute path of one report file; raises ValueError for anything that is not a plain report file name."""
    if not _SAFE_NAME.match(file_name or ""):
        raise ValueError("Bad report name")
    return os.path.join(folder or accessibility.REPORT_DIR, file_name)


def write_index(folder: str = None) -> str:
    """Writes <folder>/index.html (links relative to the folder) so a CI server can publish the folder as it is."""
    folder = folder or accessibility.REPORT_DIR
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "index.html")
    with open(path, "w", encoding="utf-8") as index:
        index.write(render_page(folder, link_base=""))
    return path


def render_page(folder: str = None, link_base: str = "/accessibility-report/") -> str:
    esc = html.escape
    runs = list_runs(folder)
    latest, counts = latest_per_page(runs)
    latest_runs = list(latest.values())
    latest_ids = {id(run) for run in latest_runs}
    passed = sum(1 for run in latest_runs if run.get("status") == "PASS")
    average = round(sum(run.get("compliancePercentage", 0) for run in latest_runs) / len(latest_runs), 1) if latest_runs else 0

    rows = ""
    for run in runs:
        status = run.get("status", "")
        css = "ok" if status == "PASS" else "bad"
        key = (run.get("url", ""), str(run.get("wcagVersion", "")), str(run.get("wcagLevel", "")))
        is_latest = id(run) in latest_ids
        text = esc(f"{run.get('url', '')} wcag {run.get('wcagVersion', '')} {run.get('wcagLevel', '')}".lower(), quote=True)
        runs_cell = f"{counts[key]} run(s)" if is_latest and counts[key] > 1 else ("earlier run" if not is_latest else "1 run")
        rows += (
            f"<tr class='row{'' if is_latest else ' old'}' data-old='{0 if is_latest else 1}' data-status='{esc(status)}' data-text='{text}'>"
            f"<td>{esc(run.get('timestamp', ''))}</td>"
            f"<td class='url'>{esc(run.get('url', ''))}</td>"
            f"<td>WCAG {esc(str(run.get('wcagVersion', '')))} {esc(str(run.get('wcagLevel', '')))}</td>"
            f"<td><span class='badge {css}'>{esc(status)}</span></td>"
            f"<td>{run.get('countedViolations', 0)} / {run.get('violationCount', 0)}</td>"
            f"<td>{run.get('affectedElements', 0)}</td><td>{run.get('compliancePercentage', 0)}%</td>"
            f"<td class='muted'>{runs_cell}</td>"
            f"<td><a href='{link_base}{quote(run['file'])}' target='_blank'>Open</a></td></tr>")
    if not rows:
        rows = ("<tr><td colspan='9' class='empty'>No accessibility checks yet. Run a page that uses "
                "<code>accessibility test</code> or <code>accessibility fixture</code>.</td></tr>")

    issue_rows = "".join(
        f"<tr><td><span class='impact {esc(rule['impact'])}'>{esc(rule['impact'])}</span></td><td><strong>{esc(rule['id'])}</strong><br>"
        f"<span class='muted'>{esc(rule['help'])}</span></td><td>{len(rule['pages'])}</td><td>{rule['elements']}</td>"
        f"<td><a href='{esc(rule['helpUrl'])}' target='_blank' rel='noopener'>how to fix</a></td></tr>"
        for rule in top_issues(latest_runs))
    issues = (f"<h2>Most frequent issues <small>(latest result of every page)</small></h2><div class='wrap'><table>"
              f"<tr><th>Impact</th><th>Rule</th><th>Pages</th><th>Elements</th><th>Fix</th></tr>{issue_rows}</table></div>"
              if issue_rows else "")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{Config.APP_NAME} - Accessibility Report</title><link rel="icon" href="/favicon.ico">
<style>
body {{ margin:0; background:#F9F9F9; color:#0A192F; font-family:'Mulish',Arial,sans-serif; }}
header {{ background:#fff; border-bottom:3px solid #E77817; padding:16px 28px; }}
h1 {{ margin:0; font-size:20px; }} h2 {{ font-size:15px; color:#97291E; text-transform:uppercase; margin:26px 0 10px; }}
h2 small {{ text-transform:none; color:#5C6E89; font-weight:600; }}
main {{ max-width:1250px; margin:22px auto; padding:0 20px 50px; }}
.cards {{ display:flex; gap:14px; flex-wrap:wrap; margin-bottom:20px; }}
.card {{ flex:1; min-width:150px; background:#fff; border:1px solid #E5E8EB; border-top:4px solid #E77817; border-radius:10px; padding:14px 18px; }}
.card b {{ display:block; font-size:26px; margin-top:4px; }}
.card span {{ font-size:11px; font-weight:800; color:#5C6E89; text-transform:uppercase; }}
.tools {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin:0 0 10px; }}
.tools input[type=search] {{ flex:1; min-width:220px; border:1.5px solid #E5E8EB; border-radius:8px; padding:8px 12px; font-size:13px; }}
.tools select, .tools button {{ border:1.5px solid #E5E8EB; background:#fff; border-radius:8px; padding:7px 12px; font-size:12px; font-weight:800; color:#5C6E89; cursor:pointer; }}
.tools button:disabled {{ opacity:.4; cursor:default; }} .tools label {{ font-size:12px; color:#5C6E89; font-weight:700; }}
.tools .info {{ font-size:12px; color:#5C6E89; font-weight:700; }}
.wrap {{ overflow-x:auto; border:1px solid #E5E8EB; border-radius:10px; background:#fff; }}
table {{ width:100%; border-collapse:collapse; }}
th {{ text-align:left; background:#FCEEE2; color:#97291E; font-size:11px; text-transform:uppercase; padding:10px 12px; }}
td {{ padding:10px 12px; border-top:1px solid #E5E8EB; font-size:13px; vertical-align:top; }} td.url {{ word-break:break-all; }}
tr.old td {{ color:#5C6E89; background:#FAFAFA; }} .muted {{ color:#5C6E89; font-size:12px; }}
.badge {{ display:inline-block; padding:2px 10px; border-radius:6px; font-size:11px; font-weight:800; }}
.badge.ok {{ background:#DCFCE7; color:#15803D; }} .badge.bad {{ background:#FEE2E2; color:#B91C1C; }}
.impact {{ display:inline-block; padding:2px 10px; border-radius:6px; font-size:11px; font-weight:800; }}
.impact.critical {{ background:#FBDADA; color:#B3261E; }} .impact.serious {{ background:#F7DCC5; color:#97291E; }}
.impact.moderate {{ background:#FFF1C9; color:#8A6100; }} .impact.minor {{ background:#E3E8FA; color:#3B52A8; }}
.empty {{ text-align:center; padding:28px; color:#5C6E89; }} a {{ color:#C23029; font-weight:700; }}
</style></head><body>
<header><h1>Accessibility Report</h1></header>
<main>
<div class="cards">
<div class="card"><span>Pages checked</span><b>{len(latest_runs)}</b></div>
<div class="card"><span>Passing</span><b>{passed}</b></div>
<div class="card"><span>Failing</span><b>{len(latest_runs) - passed}</b></div>
<div class="card"><span>Average compliance</span><b>{average}%</b></div>
<div class="card"><span>Runs kept</span><b>{len(runs)}</b></div>
</div>
{issues}
<h2>Pages</h2>
<div class="tools">
  <input type="search" id="q" placeholder="Search by page address...">
  <select id="status"><option value="">All results</option><option value="FAIL">Failing only</option><option value="PASS">Passing only</option></select>
  <select id="size"><option>10</option><option selected>{PAGE_SIZE}</option><option>50</option><option>100</option></select>
  <label><input type="checkbox" id="old"> include earlier runs</label>
  <button id="prev">&laquo; Previous</button><span class="info" id="info"></span><button id="next">Next &raquo;</button>
</div>
<div class="wrap"><table id="runs"><tr><th>Time</th><th>Page</th><th>Standard</th><th>Status</th><th>Violations (counted / all)</th>
<th>Elements</th><th>Compliance</th><th>Runs</th><th>Report</th></tr>{rows}</table></div>
</main>
<script>
var rows = Array.prototype.slice.call(document.querySelectorAll('#runs tr.row'));
var state = {{ page: 0 }};
function show() {{
  var query = document.getElementById('q').value.trim().toLowerCase(), status = document.getElementById('status').value;
  var withOld = document.getElementById('old').checked, size = parseInt(document.getElementById('size').value, 10) || {PAGE_SIZE};
  var visible = rows.filter(function(row) {{
    return (withOld || row.dataset.old === '0') && (!status || row.dataset.status === status) &&
           (!query || row.dataset.text.indexOf(query) !== -1);
  }});
  var pages = Math.max(1, Math.ceil(visible.length / size));
  state.page = Math.min(state.page, pages - 1);
  rows.forEach(function(row) {{ row.style.display = 'none'; }});
  visible.slice(state.page * size, (state.page + 1) * size).forEach(function(row) {{ row.style.display = ''; }});
  document.getElementById('info').textContent = visible.length + ' result(s) - page ' + (state.page + 1) + ' of ' + pages;
  document.getElementById('prev').disabled = state.page === 0;
  document.getElementById('next').disabled = state.page >= pages - 1;
}}
['q', 'status', 'size', 'old'].forEach(function(id) {{
  document.getElementById(id).addEventListener(id === 'q' ? 'input' : 'change', function() {{ state.page = 0; show(); }});
}});
document.getElementById('prev').onclick = function() {{ state.page -= 1; show(); }};
document.getElementById('next').onclick = function() {{ state.page += 1; show(); }};
show();
</script></body></html>"""
