"""
Login test table - one row per username/password pair.

    |import     |
    |fixtures.ui.scenario.login|

    |login test                                                         |
    |username|password|browser|login result?                            |
    |admin   |admin123|       |Success                                  |
    |admin   |wrong   |firefox|Invalid username or password.           |

Columns
    username, password  the credentials typed into the login form
    browser             optional; chromium / firefox / webkit. Empty -> the browser selected in the environment settings
    login result?       "Success" when the login screen closes, otherwise the error text the application shows

The locators and actions live in the page object: pages/login_page.py (LoginPage).
"""
from core import browsers
from core.fixture_meta import input_column, output_column
from fixtures.ui.decision_fixture import DecisionFixture
from pages.login_page import LoginPage


class LoginTest(DecisionFixture):
    DESCRIPTION = "Logs in to the framework with each username and password and returns what the login form shows."
    INPUTS = ("username", "password", "browser")
    OUTPUTS = ("login_result",)
    COLUMNS = (
        input_column("username", required=True, example="admin", help="User typed into the Username field"),
        input_column("password", required=True, example="admin123", secret=True, help="Typed into the Password field (masked in reports)"),
        input_column("browser", options=browsers.CHOICES, help="Optional. Empty = the browser selected in the environment settings"),
        output_column("login_result", example="Success", help='"Success", or the error text the form shows, e.g. Invalid username or password.'),
    )

    def run_row(self, row):
        page = LoginPage(self.ui)
        page.open()
        page.login(row.username, row.password)
        return {"login_result": page.outcome()}
