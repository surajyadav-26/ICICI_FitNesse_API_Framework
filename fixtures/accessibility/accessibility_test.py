"""
Accessibility checks as a column table: one row per page / WCAG setting.

    |import|
    |fixtures.accessibility|

    |accessibility test|
    |url                |wcag version|max violations|browser|violations?|compliance?|status?|
    |${UI_BASE_URL}     |2.1         |0             |       |           |           |PASS   |
    |${UI_BASE_URL}home |2.2         |3             |firefox|           |           |       |

Columns (all but url are optional)
    url              page to check
    wcag version     2.0 / 2.1 / 2.2 (default 2.1)             wcag level      A / AA / AAA (default AA)
    max violations   allowed counted violations (default 0)    minimum impact  minor / moderate / serious / critical (default minor)
    browser          chromium / firefox / webkit; empty -> the browser selected in the environment settings
Results: violations?, all violations?, passed checks?, needs review?, compliance?, status?, report?
A row whose page has more counted violations than allowed is a failed test case in Allure even without an expected cell.
"""
from core import accessibility
from core import browsers
from core.fixture_meta import input_column, output_column
from fixtures.accessibility.checker import AccessibilityError, run_check
from fixtures.ui.decision_fixture import DecisionFixture


class AccessibilityTest(DecisionFixture):
    DESCRIPTION = "Checks each page against WCAG with axe-core and returns the violation counts and a report."
    INPUTS = ("url", "wcag_version", "wcag_level", "max_violations", "minimum_impact", "browser")
    OUTPUTS = ("violations", "all_violations", "passed_checks", "needs_review", "compliance", "status", "report")
    COLUMNS = (
        input_column("url", required=True, example="${UI_BASE_URL}", help="Page to check; ${UI_BASE_URL} is the selected environment"),
        input_column("wcag_version", options=("2.0", "2.1", "2.2"), help="Optional. Default 2.1"),
        input_column("wcag_level", options=("A", "AA", "AAA"), help="Optional. Default AA"),
        input_column("max_violations", example="0", help="Optional. Violations allowed before the page fails. Default 0"),
        input_column("minimum_impact", options=("minor", "moderate", "serious", "critical"),
                     help="Optional. Findings below this impact are listed but not counted. Default minor"),
        input_column("browser", options=browsers.CHOICES, help="Optional. Empty = the environment's browser"),
        output_column("violations", example="0", help="Violations that count (impact at or above the minimum)"),
        output_column("status", example="PASS", help="PASS or FAIL against max violations"),
        output_column("compliance", help="Passed rules as a percentage of all checked rules", default=False),
        output_column("all_violations", help="All violations, whatever their impact", default=False),
        output_column("passed_checks", help="Rules that passed", default=False),
        output_column("needs_review", help="Rules axe-core could not decide", default=False),
        output_column("report", help="Link to the HTML report", default=False),
    )

    def __init__(self) -> None:
        super().__init__()
        self._message = ""

    def run_row(self, row):
        try:
            summary, html_path = run_check(
                self.ui, row.url, row.get("wcag_version", "2.1"), row.get("wcag_level", "AA"),
                row.get("minimum_impact", "minor"), int(row.get("max_violations", 0)), row.url or "accessibility")
        except ValueError as error:
            raise AccessibilityError(str(error))
        self._message = (f"{summary['countedViolations']} counted violation(s), {summary['maxViolations']} allowed "
                         f"(WCAG {summary['wcagVersion']} {summary['wcagLevel']})")
        return {
            "violations": summary["countedViolations"], "all_violations": summary["violationCount"],
            "passed_checks": summary["passedChecks"], "needs_review": summary["incompleteCount"],
            "compliance": f"{summary['compliancePercentage']}%", "status": summary["status"],
            "report": f'<a href="{accessibility.report_url(html_path)}" target="_blank">report</a>',
        }

    def row_verdict(self, outputs):
        return self._message if outputs.get("status") == "FAIL" else ""
