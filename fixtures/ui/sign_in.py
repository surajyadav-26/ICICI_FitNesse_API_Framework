"""
Signing in before a page that needs a login, for column-table fixtures that take username / password columns.

The application's own page object does the work. By convention every copy of the framework has pages/login_page.py with

    class LoginPage(BasePage):
        def open(self): ...                         opens the login screen
        def login(self, username, password): ...    types the credentials and submits
        def outcome(self) -> str: ...               "Success" or the error text the form shows

so a table such as `visual test` or `layout test` works unchanged in another application's copy.
"""
from fixtures.ui.decision_fixture import RowFailure


def sign_in(ui, username: str, password: str) -> None:
    """Logs in through the LoginPage page object; raises RowFailure with the application's message when it is refused."""
    try:
        from pages.login_page import LoginPage
    except ImportError as error:
        raise RowFailure(f"username / password were given but pages/login_page.py (LoginPage) is not available: {error}")
    page = LoginPage(ui)
    page.open()
    page.login(username, password)
    outcome = page.outcome()
    if outcome != "Success":
        raise RowFailure(f"Login as '{username}' failed: {outcome or 'no answer from the login form'}")
