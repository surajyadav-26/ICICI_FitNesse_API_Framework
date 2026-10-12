"""Runs one accessibility check on a UiFixture whose browser is running, and records it in Allure and the simple report."""
from core import accessibility
from core.config import Config
from core.flow import is_failure
from core.logger import logger


class AccessibilityError(Exception):
    """The page could not be opened or checked (not the same as the page having violations)."""


def run_check(ui, url: str, version: str = "2.1", level: str = "AA", minimum_impact: str = "minor",
              max_violations: int = 0, name: str = "accessibility") -> tuple:
    """
    Opens the url, runs axe-core and writes the report. Returns (summary, report html path).
    A page with violations is a normal result (status FAIL); an AccessibilityError means the check itself could not run.
    """
    accessibility.tags_for(version, level)            # fail early on a bad WCAG version / level
    accessibility.clean_impact(minimum_impact)
    if not str(url).strip():
        raise AccessibilityError("No url was given")
    if is_failure(ui.navigate_to(url)):
        raise AccessibilityError(f"Could not open {url}")
    page = ui._page
    try:
        page.wait_for_load_state("load", timeout=15000)
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass                                           # a busy page is still checked
    try:
        results = accessibility.run_axe(page, version, level)
    except Exception as error:
        raise AccessibilityError(f"axe-core could not run on {url}: {error}")

    summary = accessibility.summarize(results, page.url, version, level, minimum_impact, max_violations)
    html_path, json_path = accessibility.write_report(summary, name)
    _record(ui, summary, html_path, json_path, name)
    return summary, html_path


def _record(ui, summary: dict, html_path: str, json_path: str, name: str) -> None:
    headline = (f"Accessibility WCAG {summary['wcagVersion']} {summary['wcagLevel']} on {summary['url']}: {summary['status']} - "
                f"{summary['countedViolations']} violation(s) counted of {summary['violationCount']}, "
                f"compliance {summary['compliancePercentage']}%")
    link = Config.fitnesse_url() + accessibility.report_url(html_path)
    logger.info(f"[Accessibility] {headline} ({html_path})")
    allure = getattr(ui, "_allure", None)
    if allure:
        try:
            allure.mark("accessibility", **{"Page": summary["url"], "WCAG": f"{summary['wcagVersion']} {summary['wcagLevel']}"})
            with open(html_path, "r", encoding="utf-8") as report:
                report_link = allure.add_attachment(f"Accessibility report - {name}", report.read(), "text/html", "html", step=True)
            with open(json_path, "r", encoding="utf-8") as raw:
                json_link = allure.add_attachment(f"Accessibility data - {name}", raw.read(), "application/json", "json", step=True)
            allure.add_step(headline, "passed" if summary["status"] == "PASS" else "failed", 1,
                            [item for item in (report_link, json_link) if item])
            minimum = accessibility.IMPACTS.index(summary["minimumImpact"])
            for violation in summary["violations"]:
                counts = violation["impact"] in accessibility.IMPACTS and accessibility.IMPACTS.index(violation["impact"]) >= minimum
                failing = counts and summary["status"] != "PASS"      # inside the allowed limit it is information, not a failure
                note = "" if counts else " - below the minimum impact, not counted"
                if counts and not failing:
                    note = " - within the allowed limit"
                allure.add_step(f"[{violation['impact']}] {violation['id']}: {violation['help']} ({len(violation['nodes'])} element(s))" + note,
                                "failed" if failing else "passed", 1, message=violation["helpUrl"] if failing else "")
            if summary["status"] != "PASS":
                allure.set_failed(headline)
        except Exception as error:
            logger.debug(f"[Accessibility] Allure attachment skipped: {error}")
    ui._log_simple_step(headline, "PASSED" if summary["status"] == "PASS" else "FAILED", f"Report: {link}")
