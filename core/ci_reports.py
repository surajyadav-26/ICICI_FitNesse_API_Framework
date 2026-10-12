"""
Build step for CI: turns the files a run left on disk into publishable reports and decides the quality gate.

    python -m core.ci_reports            write the indexes and the Allure report, print a summary, exit 0
    python -m core.ci_reports --gate     the same, and exit 1 when a visual comparison failed or an accessibility check failed
    python -m core.ci_reports --site DIR also collect everything into DIR as one static site (for GitHub Pages or any web server)

What it writes (all below FitNesseRoot/files/testResults, so the Collect Artifacts step already picks them up):
    allure-report/index.html     Allure dashboard (needs the Allure command-line tool; skipped with a warning when missing)
    visual/index.html            latest visual comparisons, each linking to its own report.html
    accessibility/index.html     every accessibility check of the run

The summary is one line per area, so the console log of a failed build says what failed without opening a report.
"""
import html
import os
import shutil
import sys

from core import accessibility_review, visual_compare, visual_report
from core.config import Config


def build_allure() -> str:
    """Generates the Allure report; returns "" on success or the reason it was skipped."""
    results = os.path.join(visual_compare.BASE_DIR, "FitNesseRoot", "files", "testResults", "allure-results")
    if not os.path.isdir(results) or not os.listdir(results):
        return "no Allure results were written"
    try:
        from core.allure_report import generate_allure_report
        generate_allure_report(Config.fitnesse_url())
        return ""
    except Exception as error:                # a missing CLI must not hide the other reports
        return f"Allure report skipped: {error}"


def build_site(target: str, results_root: str = None, simple_report: str = None, environment: dict = None) -> list:
    """
    Collects the reports of one run into a folder that can be served as it is:

        index.html, allure/, visual/, accessibility/, simple-report.html

    Returns the names of the parts that were found. Parts that do not exist are left out of the index, not faked.
    """
    base = os.path.join(visual_compare.BASE_DIR, "FitNesseRoot", "files")
    results_root = results_root or os.path.join(base, "testResults")
    simple_report = simple_report or os.path.join(base, "report.html")
    environment = os.environ if environment is None else environment
    os.makedirs(target, exist_ok=True)

    parts = []
    for label, source_name, folder in (("Allure report", "allure-report", "allure"),
                                       ("Visual regression", "visual", "visual"),
                                       ("Accessibility", "accessibility", "accessibility")):
        source = os.path.join(results_root, source_name)
        if os.path.isfile(os.path.join(source, "index.html")):
            shutil.copytree(source, os.path.join(target, folder), dirs_exist_ok=True)
            parts.append((label, f"{folder}/index.html"))
    if os.path.isfile(simple_report):
        shutil.copyfile(simple_report, os.path.join(target, "simple-report.html"))
        parts.append(("Simple report", "simple-report.html"))

    esc = html.escape
    run_bits = []
    if environment.get("GITHUB_REPOSITORY"):
        run_bits.append(esc(environment["GITHUB_REPOSITORY"]))
    if environment.get("GITHUB_REF_NAME"):
        run_bits.append("branch " + esc(environment["GITHUB_REF_NAME"]))
    if environment.get("GITHUB_RUN_NUMBER"):
        run_bits.append("run #" + esc(environment["GITHUB_RUN_NUMBER"]))
    if environment.get("GITHUB_SHA"):
        run_bits.append("commit " + esc(environment["GITHUB_SHA"][:8]))
    cards = "".join(f"<a class='card' href='{esc(link)}'><b>{esc(label)}</b><span>Open</span></a>" for label, link in parts)
    if not cards:
        cards = "<p>No reports were produced by this run.</p>"
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(Config.APP_NAME)} - Test reports</title>
<style>
body {{ margin:0; background:#F9F9F9; color:#0A192F; font-family:Arial,sans-serif; }}
header {{ background:#fff; border-bottom:3px solid #E77817; padding:18px 28px; }} h1 {{ margin:0; font-size:22px; }}
header p {{ margin:6px 0 0; color:#5C6E89; font-size:13px; }}
main {{ max-width:900px; margin:28px auto; padding:0 20px; display:flex; gap:16px; flex-wrap:wrap; }}
.card {{ flex:1; min-width:200px; background:#fff; border:1px solid #E5E8EB; border-top:4px solid #E77817; border-radius:10px;
        padding:20px; text-decoration:none; color:inherit; display:block; }}
.card:hover {{ border-top-color:#C23029; box-shadow:0 4px 14px rgba(10,25,47,.08); }}
.card b {{ display:block; font-size:17px; }} .card span {{ color:#C23029; font-weight:700; font-size:13px; }}
</style></head><body>
<header><h1>{esc(Config.APP_TITLE)} - test reports</h1><p>{' &middot; '.join(run_bits) or 'Latest run'}</p></header>
<main>{cards}</main></body></html>"""
    with open(os.path.join(target, "index.html"), "w", encoding="utf-8") as index:
        index.write(page)
    open(os.path.join(target, ".nojekyll"), "w").close()          # GitHub Pages: serve the folders as they are
    return [label for label, _ in parts]


def main(argv: list) -> int:
    gate = "--gate" in argv
    problems = []

    visual_items = visual_compare.list_results()
    visual_report.write_index(results=visual_items)
    failed_visual = [item for item in visual_items if item.get("status") == "failed"]
    print(f"[ci-reports] visual: {len(visual_items)} comparison(s), {len(failed_visual)} mismatch(es)")
    for item in failed_visual:
        print(f"[ci-reports]   MISMATCH {item.get('name')} [{item.get('profile')}] {item.get('mismatch_pct')}% - {item.get('message')}")
    problems += [f"visual mismatch: {item.get('name')}" for item in failed_visual]

    runs = accessibility_review.list_runs()
    accessibility_review.write_index()
    failed_access = [run for run in runs if run.get("status") == "FAIL"]
    print(f"[ci-reports] accessibility: {len(runs)} check(s), {len(failed_access)} failed")
    for run in failed_access:
        print(f"[ci-reports]   FAIL {run.get('url')} - {run.get('countedViolations')} counted violation(s), "
              f"{run.get('maxViolations')} allowed")
    problems += [f"accessibility failed: {run.get('url')}" for run in failed_access]

    note = build_allure()
    print(f"[ci-reports] allure: {note or 'report generated'}")

    if "--site" in argv:
        position = argv.index("--site") + 1
        if position >= len(argv):
            print("[ci-reports] --site needs a folder name")
            return 2
        found = build_site(argv[position])
        print(f"[ci-reports] site: {argv[position]} ({', '.join(found) or 'no reports found'})")

    if gate and problems:
        print(f"[ci-reports] quality gate FAILED ({len(problems)} problem(s))")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
