"""
Accessibility (WCAG) engine: runs axe-core in the browser page, turns its output into a verdict and writes a report.

    results = run_axe(page, "2.1", "AA")
    summary = summarize(results, url, "2.1", "AA", minimum_impact="minor", max_violations=0)
    html_path, json_path = write_report(summary, "home page")

axe-core (Deque Systems, MPL-2.0) is vendored in core/axe.min.js, so no download or npm install is needed.
Compliance % = passed rules / (passed + violated + needs-review rules), counted per rule as in the axe summary.
"""
import html

from core.config import Config
import json
import os
import re
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AXE_FILE = os.path.join(BASE_DIR, "core", "axe.min.js")
REPORT_DIR = os.path.join(BASE_DIR, "FitNesseRoot", "files", "testResults", "accessibility")

IMPACTS = ["minor", "moderate", "serious", "critical"]
_TAGS = {
    "2.0": {"A": ["wcag2a"], "AA": ["wcag2a", "wcag2aa"], "AAA": ["wcag2a", "wcag2aa", "wcag2aaa"]},
    "2.1": {"A": ["wcag2a", "wcag21a"], "AA": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
            "AAA": ["wcag2a", "wcag2aa", "wcag2aaa", "wcag21a", "wcag21aa", "wcag21aaa"]},
    "2.2": {"A": ["wcag2a", "wcag21a"],        # axe has no separate 2.2 level-A rules
            "AA": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
            "AAA": ["wcag2a", "wcag2aa", "wcag2aaa", "wcag21a", "wcag21aa", "wcag21aaa", "wcag22aa"]},
}


def tags_for(version: str = "2.1", level: str = "AA") -> list:
    """axe rule tags for a WCAG version and conformance level."""
    version, level = str(version).strip() or "2.1", str(level).strip().upper() or "AA"
    if version not in _TAGS:
        raise ValueError(f"Unsupported WCAG version '{version}' (use 2.0, 2.1 or 2.2)")
    if level not in _TAGS[version]:
        raise ValueError(f"Unsupported WCAG level '{level}' (use A, AA or AAA)")
    return list(_TAGS[version][level])


def clean_impact(value: str) -> str:
    impact = str(value or "minor").strip().lower()
    if impact not in IMPACTS:
        raise ValueError(f"Unknown impact '{value}' (use minor, moderate, serious or critical)")
    return impact


def run_axe(page, version: str = "2.1", level: str = "AA") -> dict:
    """Injects axe-core into the page and returns its raw results."""
    with open(AXE_FILE, "r", encoding="utf-8") as axe_file:
        page.evaluate(axe_file.read())
    options = {"runOnly": {"type": "tag", "values": tags_for(version, level)}, "resultTypes": ["violations", "incomplete"]}
    return page.evaluate("async (options) => await window.axe.run(document, options)", options)


def summarize(results: dict, url: str, version: str = "2.1", level: str = "AA", minimum_impact: str = "minor",
              max_violations: int = 0) -> dict:
    """Condenses axe results into counts, the violation list and a PASS / FAIL verdict."""
    minimum = IMPACTS.index(clean_impact(minimum_impact))
    violations = []
    for rule in results.get("violations", []):
        violations.append({
            "id": rule.get("id", ""),
            "impact": rule.get("impact") or "minor",
            "description": rule.get("description", ""),
            "help": rule.get("help", ""),
            "helpUrl": rule.get("helpUrl", ""),
            "wcagTags": [tag for tag in rule.get("tags", []) if tag.startswith("wcag")],
            "nodes": [{"target": ", ".join(str(t) for t in node.get("target", [])), "html": node.get("html", ""),
                       "summary": node.get("failureSummary", "")} for node in rule.get("nodes", [])],
        })
    violations.sort(key=lambda v: -IMPACTS.index(v["impact"]) if v["impact"] in IMPACTS else 0)
    counted = [v for v in violations if v["impact"] in IMPACTS and IMPACTS.index(v["impact"]) >= minimum]
    passed = len(results.get("passes", []))
    incomplete = len(results.get("incomplete", []))
    total = passed + len(violations) + incomplete
    by_impact = {impact: sum(1 for v in violations if v["impact"] == impact) for impact in reversed(IMPACTS)}
    return {
        "url": url, "wcagVersion": str(version), "wcagLevel": str(level).upper(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "minimumImpact": clean_impact(minimum_impact), "maxViolations": int(max_violations),
        "passedChecks": passed, "violationCount": len(violations), "countedViolations": len(counted),
        "incompleteCount": incomplete, "affectedElements": sum(len(v["nodes"]) for v in violations),
        "compliancePercentage": round(passed * 100.0 / total, 2) if total else 100.0,
        "byImpact": by_impact, "violations": violations,
        "status": "PASS" if len(counted) <= int(max_violations) else "FAIL",
    }


def _file_stem(name: str) -> str:
    return re.sub(r"[^\w\-]+", "_", str(name)).strip("_")[:60] or "accessibility"


def write_report(summary: dict, name: str, folder: str = None, keep: int = None) -> tuple:
    """
    Writes <page>-<id>-<time>.html and .json; returns (html path, json path).
    The id is a short hash of the full address, version and level, so two pages whose addresses start the same never share a
    file name, and only the newest `keep` reports of one page and standard are kept (ACCESSIBILITY_KEEP_RUNS).
    """
    import hashlib
    folder = folder or REPORT_DIR
    os.makedirs(folder, exist_ok=True)
    key = f"{name}|{summary.get('wcagVersion', '')}|{summary.get('wcagLevel', '')}"
    prefix = f"{_file_stem(name)[:40]}-{hashlib.sha1(key.encode('utf-8')).hexdigest()[:8]}"
    stem = f"{prefix}-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    html_path, json_path = os.path.join(folder, stem + ".html"), os.path.join(folder, stem + ".json")
    with open(json_path, "w", encoding="utf-8") as json_file:
        json.dump(summary, json_file, indent=2)
    with open(html_path, "w", encoding="utf-8") as html_file:
        html_file.write(render_html(summary))
    _prune(folder, prefix, keep if keep is not None else Config.ACCESSIBILITY_KEEP_RUNS)
    return html_path, json_path


def _prune(folder: str, prefix: str, keep: int) -> None:
    """Removes the oldest reports of one page and standard beyond `keep` (0 or less keeps everything)."""
    if keep <= 0:
        return
    stems = sorted({name[:-5] for name in os.listdir(folder)
                    if name.startswith(prefix + "-") and name.endswith(".json")})
    for stem in stems[:-keep]:
        for extension in (".json", ".html"):
            try:
                os.remove(os.path.join(folder, stem + extension))
            except OSError:
                pass


def report_url(path: str) -> str:
    """Path of a written report below FitNesse's /files folder (relative, so it works on any host)."""
    relative = os.path.relpath(path, os.path.join(BASE_DIR, "FitNesseRoot")).replace(os.sep, "/")
    return "/" + relative


def render_html(summary: dict) -> str:
    esc = html.escape
    status_class = "pass" if summary["status"] == "PASS" else "fail"
    rows = ""
    for violation in summary["violations"]:
        elements = "".join(
            f"<li><code>{esc(node['target'])}</code><pre>{esc(node['html'][:300])}</pre><small>{esc(node['summary'].splitlines()[1] if node['summary'] and len(node['summary'].splitlines()) > 1 else '')}</small></li>"
            for node in violation["nodes"][:10])
        more = f"<li><em>... and {len(violation['nodes']) - 10} more</em></li>" if len(violation["nodes"]) > 10 else ""
        rows += (f"<tr><td><span class='impact {esc(violation['impact'])}'>{esc(violation['impact'])}</span></td>"
                 f"<td><strong>{esc(violation['id'])}</strong><br>{esc(violation['help'])}<br>"
                 f"<a href='{esc(violation['helpUrl'])}' target='_blank'>how to fix</a></td>"
                 f"<td>{esc(', '.join(violation['wcagTags']))}</td><td><ul>{elements}{more}</ul></td></tr>")
    if not rows:
        rows = "<tr><td colspan='4' style='text-align:center;padding:24px'>No violations found.</td></tr>"
    impacts = " ".join(f"<span class='impact {impact}'>{impact}: {count}</span>" for impact, count in summary["byImpact"].items())
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>{Config.APP_NAME} - Accessibility Report</title>
<link rel="icon" type="image/x-icon" href="/files/fitnesse/icici/img/icici-favicon.ico">
<style>
body {{ margin:0; background:#F9F9F9; color:#0A192F; font-family:'Mulish',Arial,sans-serif; }}
header {{ background:#fff; border-bottom:3px solid #E77817; padding:18px 32px; }}
h1 {{ margin:0; font-size:20px; }} header p {{ margin:4px 0 0; color:#5C6E89; font-size:13px; }}
main {{ max-width:1200px; margin:22px auto; padding:0 24px 50px; }}
.cards {{ display:flex; gap:14px; flex-wrap:wrap; margin-bottom:20px; }}
.card {{ flex:1; min-width:150px; background:#fff; border:1px solid #E5E8EB; border-top:4px solid #E77817; border-radius:10px; padding:14px 18px; }}
.card b {{ display:block; font-size:26px; margin-top:4px; }} .card span {{ font-size:11px; font-weight:800; color:#5C6E89; text-transform:uppercase; }}
.card.pass {{ border-top-color:#1E7A4C; }} .card.pass b {{ color:#1E7A4C; }} .card.fail {{ border-top-color:#DC3434; }} .card.fail b {{ color:#B3261E; }}
table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid #E5E8EB; border-radius:10px; }}
th {{ text-align:left; background:#FCEEE2; font-size:11px; text-transform:uppercase; padding:10px 12px; color:#97291E; }}
td {{ vertical-align:top; padding:12px; border-top:1px solid #E5E8EB; font-size:13px; }}
ul {{ margin:0; padding-left:18px; }} pre {{ margin:4px 0; background:#F9F9F9; padding:6px; border-radius:6px; white-space:pre-wrap; word-break:break-all; font-size:11px; }}
code {{ color:#97291E; font-size:12px; }} a {{ color:#C23029; }}
.impact {{ display:inline-block; padding:2px 10px; border-radius:6px; font-size:11px; font-weight:800; margin-right:6px; }}
.impact.critical {{ background:#FBDADA; color:#B3261E; }} .impact.serious {{ background:#F7DCC5; color:#97291E; }}
.impact.moderate {{ background:#FFF1C9; color:#8A6100; }} .impact.minor {{ background:#E3E8FA; color:#3B52A8; }}
</style></head><body>
<header><h1>Accessibility Report - WCAG {esc(summary['wcagVersion'])} Level {esc(summary['wcagLevel'])}</h1>
<p>{esc(summary['url'])} &middot; {esc(summary['timestamp'])} &middot; counting violations of impact {esc(summary['minimumImpact'])} or worse,
allowed {summary['maxViolations']}</p></header>
<main>
<div class="cards">
<div class="card {status_class}"><span>Status</span><b>{summary['status']}</b></div>
<div class="card"><span>Violations</span><b>{summary['violationCount']}</b></div>
<div class="card"><span>Affected elements</span><b>{summary['affectedElements']}</b></div>
<div class="card"><span>Passed checks</span><b>{summary['passedChecks']}</b></div>
<div class="card"><span>Needs review</span><b>{summary['incompleteCount']}</b></div>
<div class="card"><span>Compliance</span><b>{summary['compliancePercentage']}%</b></div>
</div>
<p>{impacts}</p>
<table><tr><th>Impact</th><th>Rule</th><th>WCAG</th><th>Affected elements</th></tr>{rows}</table>
</main></body></html>"""
