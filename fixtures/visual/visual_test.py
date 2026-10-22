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
    viewport    optional, WIDTHxHEIGHT such as 1366x768, or `auto` to open the page at the size of the reference image.
                Use it so the page has the same shape as the reference image; the reference is scaled to the page when
                both have the same shape
    reference   optional, the design image to compare with: a file inside fixtures/visual/baseline (login-v2.png, or
                designs/login), or a full path such as C:\\designs\\login.png. PNG or JPEG. Empty = fixtures/visual/baseline/<name>.png
    reference only   optional, true = the reference image must already exist in fixtures/visual/baseline; nothing is captured
                or created (also VISUAL_REQUIRE_REFERENCE=true). Use this to check the screen against a design you supply
    threshold   optional, percent of pixels allowed to differ (default VISUAL_THRESHOLD, 0.1)
    ignore      optional, locators to mask, separated by commas (a clock, an ad)
    username, password   optional; sign in through pages/login_page.py (LoginPage) before opening the url
    browser     optional, chromium / firefox / webkit; empty -> the browser selected in the environment settings
Results: status? (passed / failed / new / updated), difference? (percent of pixels), differences? (what kind of difference
where: colour, position, size or content), message?, baseline? (where it came from),
report? (HTML report: baseline, actual, the marked differences and a defect description to paste into a bug)
A row that differs more than allowed is a failed test case in Allure even without an expected cell; open the
Visual Review Report from the profile menu to see baseline, actual and diff side by side and approve a new baseline.
"""
import os
import re

from PIL import Image

from core import visual_compare, visual_regions, visual_report
from core.config import Config
from core import browsers
from core.fixture_meta import input_column, output_column
from core.flow import is_failure
from fixtures.ui.decision_fixture import DecisionFixture, RowFailure
from fixtures.ui.sign_in import sign_in

_VIEWPORT = re.compile(r"^\s*(\d{3,5})\s*[xX*]\s*(\d{3,5})\s*$")


class VisualTest(DecisionFixture):
    DESCRIPTION = "Opens each page and compares it with its reference image or stored baseline; returns the difference."
    INPUTS = ("url", "name", "reference", "viewport", "threshold", "ignore", "username", "password", "reference_only", "browser")
    OUTPUTS = ("status", "difference", "differences", "message", "baseline", "report")
    COLUMNS = (
        input_column("url", required=True, example="${UI_BASE_URL}", help="Page to open; ${UI_BASE_URL} is the selected environment"),
        input_column("name", required=True, example="login page",
                     help="Baseline name: fixtures/visual/baseline/<name>.png when that file exists, else stored on the first run"),
        input_column("reference", example="designs/login.png",
                     help="Optional. The design image: a file in fixtures/visual/baseline, or a full path. Empty = <name>.png there"),
        input_column("viewport", example="1600x1043", help="Optional. WIDTHxHEIGHT, or auto = the size of the reference image"),
        input_column("reference_only", options=("true", "false"),
                     help="Optional. true = the reference image must exist; nothing is captured or created"),
        input_column("threshold", example="0.5", help="Optional. Percent of pixels allowed to differ. Default 0.1"),
        input_column("ignore", example="css=.clock", help="Optional. Locators to mask, separated by commas"),
        input_column("username", example="qa", help="Optional. Signs in through pages/login_page.py before opening the url"),
        input_column("password", secret=True, example="qa123", help="Optional. Masked in reports and on screen"),
        input_column("browser", options=browsers.CHOICES, help="Optional. Empty = the environment's browser"),
        output_column("status", example="passed", help="passed, failed, new (baseline created) or updated"),
        output_column("difference", example="0.0", help="Percent of pixels that differ"),
        output_column("differences", help="What differs and where: colour, position, size or content", default=False),
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
        if row.has("username"):
            sign_in(self.ui, row.username, row.password)         # pages behind a login need it before the url is opened
        reference = visual_compare.find_reference(name, row.reference)
        if row.has("reference") and not reference:
            raise RowFailure(f"Reference image '{row.reference}' was not found (looked in fixtures/visual/baseline and as a full path)")
        if row.get("reference_only", "").lower() == "true" or Config.VISUAL_REQUIRE_REFERENCE:
            if not reference:
                raise RowFailure(f"No reference image at fixtures/visual/baseline/{name}.png. Add the design screenshot there "
                                 "(a reference-only check never captures or creates one)")
        self.do(self.ui.navigate_to, row.url)
        if row.has("viewport"):
            if row.viewport.strip().lower() == "auto":
                if not reference:
                    raise RowFailure(f"viewport auto needs the reference image fixtures/visual/baseline/{name}.png")
                with Image.open(reference) as design:
                    size = {"width": design.width, "height": design.height}
            else:
                match = _VIEWPORT.match(row.viewport)
                if not match:
                    raise RowFailure(f"Invalid viewport '{row.viewport}' (use WIDTHxHEIGHT such as 1366x768, or auto)")
                size = {"width": int(match.group(1)), "height": int(match.group(2))}
            self.ui._page.set_viewport_size(size)
        for locator in [part.strip() for part in row.ignore.split(",") if part.strip()]:
            self.do(self.ui.ignore_visual_region, locator)
        if row.has("threshold"):
            self.do(self.ui.set_visual_threshold, row.threshold)
        if row.has("reference"):
            self.ui._visual_reference_file = reference                       # used by this comparison only
        outcome = self.ui.verify_visual_match(name)
        result = self.ui._last_visual
        if result is None:
            raise RowFailure("The visual comparison could not run" if is_failure(outcome) else "No visual result was produced")
        self._verdict = ""
        if result.status == "failed":
            self._verdict = result.message
        elif result.status == "new" and Config.VISUAL_FAIL_ON_NEW:
            self._verdict = "No baseline existed and VISUAL_FAIL_ON_NEW is on"
        source = result.baseline_source or ("reference image" if reference else f"stored baseline ({result.profile})")
        link = ""
        if os.path.isfile(os.path.join(visual_compare.result_dir(result.profile, result.name), "report.html")):
            link = f'<a href="{visual_report.report_url(result.profile, result.name)}" target="_blank">report</a>'
        return {"status": result.status, "difference": result.mismatch_pct, "message": result.message, "baseline": source,
                "differences": visual_regions.summary(result.regions), "report": link}

    def row_verdict(self, outputs):
        return self._verdict
