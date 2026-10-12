"""
Layout checks as a column table: alignment, box size and colours of chosen elements, without comparing pixels.

    |layout test|
    |url               |name      |elements                                   |tolerance|username|password|status?|differences?|
    |${UI_BASE_URL}home|home page |LoginPage.username, LoginPage.login button |2        |qa      |qa123   |passed |            |

Columns (url, name and elements are required)
    url         page to open; ${UI_BASE_URL} is the selected environment
    name        baseline name; the first run stores the measured values, later runs compare with them
                (fixtures/visual/layout/<name>.json, if present, is used instead - for values you wrote by hand)
    elements    locators to measure, separated by commas: page object names (LoginPage.username), css=..., text=...
    tolerance   optional, pixels a position or size may move (default LAYOUT_TOLERANCE, 2). Colours must match exactly
    username, password   optional; sign in through pages/login_page.py (LoginPage) before opening the url
    viewport    optional, WIDTHxHEIGHT such as 1366x768
    update      optional, true = accept this run as the new baseline
    browser     optional, chromium / firefox / webkit; empty -> the browser selected in the environment settings
Results: status? (passed / failed / new / updated), differences? (what moved or changed colour), checked? (elements),
report? (HTML report with the measured values and a defect description)
"""
import os
import re

from core import layout_compare
from core.config import Config
from core.fixture_meta import input_column, output_column
from fixtures.ui.decision_fixture import DecisionFixture, RowFailure
from fixtures.ui.sign_in import sign_in

_VIEWPORT = re.compile(r"^\s*(\d{3,5})\s*[xX*]\s*(\d{3,5})\s*$")


class LayoutTest(DecisionFixture):
    DESCRIPTION = "Compares the position, size and colours of chosen elements with a baseline; text and images do not matter."
    INPUTS = ("url", "name", "elements", "tolerance", "username", "password", "viewport", "update", "browser")
    OUTPUTS = ("status", "differences", "checked", "report")
    COLUMNS = (
        input_column("url", required=True, example="${UI_BASE_URL}", help="Page to open; ${UI_BASE_URL} is the selected environment"),
        input_column("name", required=True, example="home page", help="Baseline name; stored on the first run"),
        input_column("elements", required=True, example="LoginPage.username, LoginPage.login button",
                     help="Elements to measure, separated by commas (page object names, css=..., text=...)"),
        input_column("tolerance", example="2", help="Optional. Pixels a position or size may move. Default 2"),
        input_column("username", example="qa", help="Optional. Signs in through pages/login_page.py before opening the url"),
        input_column("password", secret=True, example="qa123", help="Optional. Masked in reports and on screen"),
        input_column("viewport", example="1366x768", help="Optional. WIDTHxHEIGHT"),
        input_column("update", options=("true", "false"), help="Optional. true accepts this run as the new baseline"),
        input_column("browser", options=("chromium", "firefox", "webkit"), help="Optional. Empty = the environment's browser"),
        output_column("status", example="passed", help="passed, failed, new (baseline created) or updated"),
        output_column("differences", help="What moved, resized or changed colour"),
        output_column("checked", example="2", help="Number of elements measured", default=False),
        output_column("report", help="Link to the HTML report with the measured values and a defect description"),
    )

    def __init__(self) -> None:
        super().__init__()
        self._verdict = ""

    def run_row(self, row):
        if not row.name:
            raise RowFailure("The name column is empty: give the baseline a name such as 'home page'")
        names = [part.strip() for part in row.elements.split(",") if part.strip()]
        if not names:
            raise RowFailure("The elements column is empty: list the elements to measure, separated by commas")
        try:
            tolerance = float(row.get("tolerance", Config.LAYOUT_TOLERANCE))
        except ValueError:
            raise RowFailure(f"Invalid tolerance '{row.tolerance}' (use a number of pixels such as 2)")
        if row.has("username"):
            sign_in(self.ui, row.username, row.password)
        self.do(self.ui.navigate_to, row.url)
        if row.has("viewport"):
            match = _VIEWPORT.match(row.viewport)
            if not match:
                raise RowFailure(f"Invalid viewport '{row.viewport}' (use WIDTHxHEIGHT such as 1366x768)")
            self.ui._page.set_viewport_size({"width": int(match.group(1)), "height": int(match.group(2))})

        profile = self.ui._visual_profile()
        snapshot = layout_compare.capture(self.ui._locator, names)
        update = row.get("update", "").lower() == "true" or Config.VISUAL_UPDATE_BASELINE
        result = layout_compare.check(snapshot, profile, row.name, tolerance, update,
                                      {"url": self.ui._page.url, "test": getattr(self.ui, "_test_name", "")})
        self._record(result)
        self._verdict = result["message"] + ": " + "; ".join(item["message"] for item in result["differences"][:3]) \
            if result["status"] == "failed" else ""
        if result["status"] == "new" and Config.VISUAL_FAIL_ON_NEW:
            self._verdict = "No baseline existed and VISUAL_FAIL_ON_NEW is on"
        link = f'<a href="{layout_compare.report_url(profile, row.name)}" target="_blank">report</a>'
        shown = "<br>".join(item["message"] for item in result["differences"][:5])
        if len(result["differences"]) > 5:
            shown += f"<br>... and {len(result['differences']) - 5} more"
        return {"status": result["status"], "differences": shown, "checked": result["elements"], "report": link}

    def row_verdict(self, outputs):
        return self._verdict

    def _record(self, result: dict) -> None:
        """Adds the result to Allure (with the report attached) and to the simple report."""
        headline = (f"Layout {result['status']}: {result['name']} [{result['profile']}] - {result['message']}")
        report_file = os.path.join(layout_compare.result_dir(result["profile"], result["name"]), "report.html")
        allure = getattr(self.ui, "_allure", None)
        if allure:
            try:
                links = []
                if os.path.isfile(report_file):
                    with open(report_file, "r", encoding="utf-8") as report:
                        link = allure.add_attachment(f"Layout report - {result['name']}", report.read(), "text/html", "html", step=True)
                    if link:
                        links.append(link)
                failed = result["status"] == "failed"
                allure.mark("visual", **{"Layout": result["name"], "Visual profile": result["profile"]})
                if failed:
                    allure.set_failed(f"Visual mismatch (layout) '{result['name']}': {result['message']}")
                allure.add_step(headline, "failed" if failed else "passed", 1, links, result["message"] if failed else "")
                for item in result["differences"]:
                    allure.add_step(item["message"], "failed", 1, message=item["message"])
            except Exception:
                pass
        try:
            self.ui._log_simple_step(headline, "FAILED" if result["status"] == "failed" else "PASSED",
                                     f"Report: {Config.fitnesse_url()}{layout_compare.report_url(result['profile'], result['name'])}")
        except Exception:
            pass
