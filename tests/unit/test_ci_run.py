"""The CI runner: environment URLs, result counts and exit codes (no FitNesse needed)."""
import pytest

from core import ci_run

SUITE_XML = """<?xml version="1.0"?><testResults><rootPath>FrontPage</rootPath>
<result><counts><right>1</right><wrong>0</wrong><ignores>0</ignores><exceptions>0</exceptions></counts></result>
<result><counts><right>2</right><wrong>1</wrong><ignores>3</ignores><exceptions>0</exceptions></counts></result>
<finalCounts><right>3</right><wrong>1</wrong><ignores>3</ignores><exceptions>0</exceptions></finalCounts></testResults>"""

PAGE_XML = """<?xml version="1.0"?><testResults>
<result><counts><right>1</right><wrong>0</wrong><ignores>0</ignores><exceptions>2</exceptions></counts></result></testResults>"""


def test_suite_counts_come_from_the_final_block():
    assert ci_run.parse_counts(SUITE_XML) == {"right": 3, "wrong": 1, "ignores": 3, "exceptions": 0}


def test_a_single_page_without_a_summary_is_added_up():
    assert ci_run.parse_counts(PAGE_XML)["exceptions"] == 2


@pytest.mark.parametrize("body", ["<html>Not Found</html", "plain text", "<testResults></testResults>"])
def test_an_answer_that_is_not_a_result_is_an_error(body):
    with pytest.raises(RuntimeError):
        ci_run.parse_counts(body, "FrontPage.Nothing")


def test_environment_urls_replace_or_add_the_variable(tmp_path):
    page = tmp_path / "content.txt"
    page.write_text("!define API_BASE_URL {https://old.example}\n!define UI_BASE_URL {http://localhost:8080/}\n!define x {1}\n",
                    encoding="utf-8")
    written = ci_run.set_environment("https://api.new/", "", str(page))
    assert written == {"API_BASE_URL": "https://api.new/"}
    text = page.read_text(encoding="utf-8")
    assert "!define API_BASE_URL {https://api.new/}" in text and "{http://localhost:8080/}" in text and "!define x {1}" in text
    ci_run.set_environment("", "https://app.new/", str(page))
    assert "!define UI_BASE_URL {https://app.new/}" in page.read_text(encoding="utf-8")
    empty = tmp_path / "other.txt"
    ci_run.set_environment("https://a/", "https://u/", str(empty))
    assert empty.read_text(encoding="utf-8") == "!define API_BASE_URL {https://a/}\n!define UI_BASE_URL {https://u/}\n"


def test_a_value_that_could_break_the_wiki_variable_is_refused(tmp_path):
    with pytest.raises(ValueError):
        ci_run.set_environment("https://a/}\n!define X {", "", str(tmp_path / "p.txt"))


@pytest.mark.parametrize("answer, extra, code", [
    (({"right": 3, "wrong": 0, "ignores": 0, "exceptions": 0}, "<x/>"), [], 0),
    (({"right": 3, "wrong": 1, "ignores": 0, "exceptions": 0}, "<x/>"), [], 1),
    (({"right": 3, "wrong": 0, "ignores": 0, "exceptions": 1}, "<x/>"), [], 1),
    (({"right": 3, "wrong": 2, "ignores": 0, "exceptions": 0}, "<x/>"), ["--no-fail"], 0),
])
def test_exit_code_follows_the_counts(monkeypatch, tmp_path, answer, extra, code):
    monkeypatch.setattr(ci_run, "run", lambda *a, **k: answer)
    monkeypatch.setattr(ci_run, "VARIABLE_PAGE", str(tmp_path / "v.txt"))
    assert ci_run.main(["--out", str(tmp_path / "r.xml")] + extra) == code
    assert (tmp_path / "r.xml").read_text(encoding="utf-8") == "<x/>"


def test_a_server_that_cannot_be_reached_is_exit_2_not_a_test_failure(monkeypatch, tmp_path):
    def unreachable(*args, **kwargs):
        raise RuntimeError("FitNesse did not answer")
    monkeypatch.setattr(ci_run, "run", unreachable)
    assert ci_run.main(["--out", str(tmp_path / "r.xml")]) == 2
