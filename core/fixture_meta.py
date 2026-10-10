"""
Describes the columns of a column-table fixture so the Step Builder (and the docs) can list them.

    class LoginTest(DecisionFixture):
        DESCRIPTION = "Logs in with each username / password."
        COLUMNS = (
            input_column("username", required=True, example="admin"),
            input_column("browser", options=("chromium", "firefox", "webkit"), help="Empty = the environment's browser"),
            output_column("login_result", example="Success"),
        )

The name is snake_case; the wiki header is the same words with spaces ("login result?" for outputs).
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    name: str                      # snake_case, e.g. "wcag_version"
    kind: str = "input"            # "input" (filled by the tester) or "output" (ends with ? and is compared)
    required: bool = False         # only meaningful for inputs
    help: str = ""
    options: tuple = ()            # allowed values, shown as a drop-down
    example: str = ""
    secret: bool = False           # shown masked in the Step Builder and the reports
    default: bool = True           # outputs: pre-selected in the Step Builder

    @property
    def header(self) -> str:
        """The header cell used in the wiki table."""
        words = self.name.replace("_", " ")
        return words + ("?" if self.kind == "output" else "")

    def to_dict(self) -> dict:
        return {"name": self.name, "header": self.header, "kind": self.kind, "required": self.required,
                "help": self.help, "options": list(self.options), "example": self.example,
                "secret": self.secret, "default": self.default}


def input_column(name: str, required: bool = False, help: str = "", options: tuple = (), example: str = "",
                 secret: bool = False) -> Column:
    return Column(name, "input", required, help, tuple(options), example, secret)


def output_column(name: str, help: str = "", example: str = "", default: bool = True) -> Column:
    return Column(name, "output", False, help, (), example, False, default)


def table_name(class_name: str) -> str:
    """LoginTest -> "login test" (the first cell of the wiki table)."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", class_name).lower()
