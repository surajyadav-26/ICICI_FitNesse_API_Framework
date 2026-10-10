"""
Visual checks as a column table: one row per page and baseline name.

    |visual test|
    |url             |name      |viewport |threshold|browser|status?|
    |${UI_BASE_URL}  |login page|1600x1043|0.5      |       |passed |

Columns (url and name are required)
    url         page to open; ${UI_BASE_URL} is the selected environment
    name        baseline name. The page is compared with fixtures/visual/baseline/<name>.png when that file exists (your own
                reference image, used for every browser); otherwise with the baseline the framework stored for this browser and
                viewport, which is created on the first run
    viewport    optional, WIDTHxHEIGHT such as 1366x768. Use it so the page has the same shape as the reference image;
                the reference is scaled to the page when both have the same shape
    threshold   optional, percent of pixels allowed to differ (default VISUAL_THRESHOLD, 0.1)
    ignore      optional, locators to mask, separated by commas (a clock, an ad)
    browser     optional, chromium / firefox / webkit; empty -> the browser selected in the environment settings
Results: status? (passed / failed / new / updated), difference? (percent of pixels), message?, baseline? (where it came from),
report? (HTML report: baseline, actual, the marked differences and a defect description to paste into a bug)
A row that differs more than allowed is a failed test case in Allure even without an expected cell; open the
Visual Review Report from the profile menu to see baseline, actual and diff side by side and approve a new baseline.
"""
import os
import re

from core import visual_compare, visual_report
from core.config import Config
from core.fixture_meta import input_column, output_column
from core.flow import is_failure
from fixtures.ui.decision_fixture import DecisionFixture, RowFailure

_VIEWPORT = re.compile(r"^\s*(\d{3,5})\s*[xX*]\s*(\d{3,5})\s*$")


class VisualTest(DecisionFixture):
    DESCRIPTION = "Opens each page and compares it with its reference image or stored baseline; returns the difference."
    INPUTS = ("url", "name", "viewport", "threshold", "ignore", "browser")
    OUTPUTS = ("status", "difference", "message", "baseline", "report")
    COLUMNS = (
        input_column("url", required=True, example="${UI_BASE_URL}", help="Page to open; ${UI_BASE_URL} is the selected environment"),
        input_column("name", required=True, example="login page",
                     help="Baseline name: fixtures/visual/baseline/<name>.png when that file exists, else stored on the first run"),
        input_column("viewport", example="1600x1043", help="Optional. WIDTHxHEIGHT; match the shape of your reference image"),
        input_column("threshold", example="0.5", help="Optional. Percent of pixels allowed to differ. Default 0.1"),
        input_column("ignore", example="css=.clock", help="Optional. Locators to mask, separated by commas"),
        input_column("browser", options=("chromium", "firefox", "webkit"), help="Optional. Empty = the environment's browser"),
        output_column("status", example="passed", help="passed, failed, new (baseline created) or updated"),
        output_column("difference", example="0.0", help="Percent of pixels that differ"),
        output_column("message", help="What the comparison found", default=False),
        output_column("baseline", help="reference image or stored baseline", default=False),
        output_column("report", help="Link to the HTML report: baseline, actual, marked differences and a defect description"),
    )

    def __init__(self) -> None:
        super().__init__()
        self._verdict = ""

    def run_row(self, row):
        name = row.name
        if not name:
            raise RowFailure("The name column is empty: give the baseline a name such as 'login page'")
        self.do(self.ui.navigate_to, row.url)
        if row.has("viewport"):
            match = _VIEWPORT.match(row.viewport)
            if not match:
                raise RowFailure(f"Invalid viewport '{row.viewport}' (use WIDTHxHEIGHT such as 1366x768)")
            self.ui._page.set_viewport_size({"width": int(match.group(1)), "height": int(match.group(2))})
        for locator in [part.strip() for part in row.ignore.split(",") if part.strip()]:
            self.do(self.ui.ignore_visual_region, locator)
        if row.has("threshold"):
            self.do(self.ui.set_visual_threshold, row.threshold)
        outcome = self.ui.verify_visual_match(name)
        result = self.ui._last_visual
        if result is None:
            raise RowFailure("The visual comparison could not run" if is_failure(outcome) else "No visual result was produced")
        self._verdict = ""
        if result.status == "failed":
            self._verdict = result.message
        elif result.status == "new" and Config.VISUAL_FAIL_ON_NEW:
            self._verdict = "No baseline existed and VISUAL_FAIL_ON_NEW is on"
        reference = visual_compare.reference_path(name)
        source = "reference image" if os.path.isfile(reference) else f"stored baseline ({result.profile})"
        link = ""
        if os.path.isfile(os.path.join(visual_compare.result_dir(result.profile, result.name), "report.html")):
            link = f'<a href="{visual_report.report_url(result.profile, result.name)}" target="_blank">report</a>'
        return {"status": result.status, "difference": result.mismatch_pct, "message": result.message, "baseline": source,
                "report": link}

    def row_verdict(self, outputs):
        return self._verdict
