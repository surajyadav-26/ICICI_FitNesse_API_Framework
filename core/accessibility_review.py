"""The Accessibility Report page: every accessibility check that was run, newest first, each linking to its full report."""
import html
import json
import os
import re
from urllib.parse import quote

from core import accessibility

_SAFE_NAME = re.compile(r"^[\w\-]+\.html$")
LIMIT = 300


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


def report_path(file_name: str, folder: str = None) -> str:
    """Absolute path of one report file; raises ValueError for anything that is not a plain report file name."""
    if not _SAFE_NAME.match(file_name or ""):
        raise ValueError("Bad report name")
    return os.path.join(folder or accessibility.REPORT_DIR, file_name)


def render_page(folder: str = None) -> str:
    esc = html.escape
    runs = list_runs(folder)
    passed = sum(1 for run in runs if run.get("status") == "PASS")
    average = round(sum(run.get("compliancePercentage", 0) for run in runs) / len(runs), 1) if runs else 0
    rows = ""
    for run in runs:
        status = run.get("status", "")
        css = "ok" if status == "PASS" else "bad"
        rows += (
            f"<tr><td>{esc(run.get('timestamp', ''))}</td>"
            f"<td class='url'>{esc(run.get('url', ''))}</td>"
            f"<td>WCAG {esc(str(run.get('wcagVersion', '')))} {esc(str(run.get('wcagLevel', '')))}</td>"
            f"<td><span class='badge {css}'>{esc(status)}</span></td>"
            f"<td>{run.get('countedViolations', 0)} / {run.get('violationCount', 0)}</td>"
            f"<td>{run.get('affectedElements', 0)}</td><td>{run.get('compliancePercentage', 0)}%</td>"
            f"<td><a href='/accessibility-report/{quote(run['file'])}' target='_blank'>Open</a></td></tr>")
    if not rows:
        rows = ("<tr><td colspan='8' class='empty'>No accessibility checks yet. Run a page that uses "
                "<code>accessibility test</code> or <code>accessibility fixture</code>.</td></tr>")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ICICI Nirikshan - Accessibility Report</title><link rel="icon" href="/favicon.ico">
<style>
body {{ margin:0; background:#F9F9F9; color:#0A192F; font-family:'Mulish',Arial,sans-serif; }}
header {{ background:#fff; border-bottom:3px solid #E77817; padding:16px 28px; display:flex; align-items:center; gap:14px; }}
header img {{ height:34px; }} h1 {{ margin:0; font-size:20px; }}
main {{ max-width:1200px; margin:22px auto; padding:0 20px 50px; }}
.cards {{ display:flex; gap:14px; flex-wrap:wrap; margin-bottom:20px; }}
.card {{ flex:1; min-width:150px; background:#fff; border:1px solid #E5E8EB; border-top:4px solid #E77817; border-radius:10px; padding:14px 18px; }}
.card b {{ display:block; font-size:26px; margin-top:4px; }}
.card span {{ font-size:11px; font-weight:800; color:#5C6E89; text-transform:uppercase; }}
.wrap {{ overflow-x:auto; border:1px solid #E5E8EB; border-radius:10px; background:#fff; }}
table {{ width:100%; border-collapse:collapse; }}
th {{ text-align:left; background:#FCEEE2; color:#97291E; font-size:11px; text-transform:uppercase; padding:10px 12px; }}
td {{ padding:10px 12px; border-top:1px solid #E5E8EB; font-size:13px; }} td.url {{ word-break:break-all; }}
.badge {{ display:inline-block; padding:2px 10px; border-radius:6px; font-size:11px; font-weight:800; }}
.badge.ok {{ background:#DCFCE7; color:#15803D; }} .badge.bad {{ background:#FEE2E2; color:#B91C1C; }}
.empty {{ text-align:center; padding:28px; color:#5C6E89; }} a {{ color:#C23029; font-weight:700; }}
</style></head><body>
<header><img src="/logo.png" alt=""><h1>Accessibility Report</h1></header>
<main>
<div class="cards">
<div class="card"><span>Checks run</span><b>{len(runs)}</b></div>
<div class="card"><span>Passed</span><b>{passed}</b></div>
<div class="card"><span>Failed</span><b>{len(runs) - passed}</b></div>
<div class="card"><span>Average compliance</span><b>{average}%</b></div>
</div>
<div class="wrap"><table><tr><th>Time</th><th>Page</th><th>Standard</th><th>Status</th><th>Violations (counted / all)</th>
<th>Elements</th><th>Compliance</th><th>Report</th></tr>{rows}</table></div>
</main></body></html>"""
