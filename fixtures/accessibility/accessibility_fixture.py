"""
Accessibility checks as a script table (one page per table):

    |script|accessibility fixture|
    |set url|${UI_BASE_URL}|
    |set wcag version|2.1|
    |set wcag level|AA|
    |set max violations|0|
    |set minimum impact|minor|
    |run accessibility check|
    |check|status|PASS|
    |show|violations|
    |show|compliance|
    |show|report|

Optional settings: set browser (chromium / firefox / webkit; default = the environment's browser), set max violations (default 0),
set minimum impact (minor / moderate / serious / critical; violations below it are listed but not counted).
`run accessibility check` returns false (red) when the page has more counted violations than allowed.
"""
from core import accessibility
from core.flow import StepError
from core.html_utils import clean_html_text, clean_html_url
from core.logger import logger
from fixtures.accessibility.checker import AccessibilityError, run_check


class AccessibilityFixture:
    def __init__(self) -> None:
        self._url = ""
        self._version = "2.1"
        self._level = "AA"
        self._max_violations = 0
        self._minimum_impact = "minor"
        self._browser = ""
        self._summary = None
        self._report_path = ""

    # ── settings ──────────────────────────────────────────────────────────────
    def set_url(self, value: str) -> None:
        self._url = clean_html_url(value)

    def set_wcag_version(self, value: str) -> None:
        self._version = clean_html_text(value) or "2.1"

    def set_wcag_level(self, value: str) -> None:
        self._level = clean_html_text(value).upper() or "AA"

    def set_max_violations(self, value: str) -> None:
        self._max_violations = int(clean_html_text(value) or 0)

    def set_minimum_impact(self, value: str) -> None:
        self._minimum_impact = clean_html_text(value) or "minor"

    def set_browser(self, value: str) -> None:
        self._browser = clean_html_text(value)

    # ── the check ─────────────────────────────────────────────────────────────
    def run_accessibility_check(self):
        """True when the page is within the allowed number of violations."""
        from fixtures.ui.ui_fixture import UiFixture
        ui = UiFixture("Accessibility Check")
        try:
            if self._browser:
                ui.set_browser(self._browser)
            if ui.start_browser() is False:
                return StepError("The browser could not be started")
            self._summary, self._report_path = run_check(ui, self._url, self._version, self._level, self._minimum_impact,
                                                         self._max_violations, self._url or "accessibility")
            return self._summary["status"] == "PASS"
        except (AccessibilityError, ValueError) as error:
            logger.error(f"[Accessibility] {error}")
            return StepError(str(error))
        finally:
            ui.close_browser()

    # ── results (use with show / check) ───────────────────────────────────────
    def status(self) -> str:
        return self._summary["status"] if self._summary else "NOT RUN"

    def violations(self) -> str:
        return str(self._summary["countedViolations"]) if self._summary else "0"

    def all_violations(self) -> str:
        return str(self._summary["violationCount"]) if self._summary else "0"

    def passed_checks(self) -> str:
        return str(self._summary["passedChecks"]) if self._summary else "0"

    def needs_review(self) -> str:
        return str(self._summary["incompleteCount"]) if self._summary else "0"

    def compliance(self) -> str:
        return f"{self._summary['compliancePercentage']}%" if self._summary else "n/a"

    def details(self) -> str:
        """The worst violations, one per line."""
        if not self._summary:
            return "No check was run"
        lines = [f"[{v['impact']}] {v['id']}: {v['help']} ({len(v['nodes'])} element(s))" for v in self._summary["violations"][:8]]
        return "<br>".join(lines) or "No violations"

    def report(self) -> str:
        if not self._report_path:
            return "No report"
        return f'<a href="{accessibility.report_url(self._report_path)}" target="_blank">View accessibility report</a>'
