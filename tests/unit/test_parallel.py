"""Parallel runs: the lock around shared files, finding the test pages, and running them N at a time."""
import json
import os
import subprocess
import sys
import time

import pytest

from core import ci_run
from core.file_lock import FileLock, write_atomically


# â”€â”€ the lock â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_WORKER = """
import json, os, sys
sys.path.insert(0, sys.argv[1])
from core.file_lock import FileLock, write_atomically
folder, data_file, count = sys.argv[2], sys.argv[3], int(sys.argv[4])
for _ in range(count):
    with FileLock("counter", directory=folder):
        current = json.load(open(data_file, encoding="utf-8")) if os.path.exists(data_file) else []
        current.append(os.getpid())
        write_atomically(data_file, json.dumps(current))
"""


def test_many_processes_never_lose_a_record(tmp_path):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_file = str(tmp_path / "history.json")
    workers = [subprocess.Popen([sys.executable, "-c", _WORKER, root, str(tmp_path / "locks"), data_file, "15"])
               for _ in range(6)]
    assert [worker.wait(timeout=120) for worker in workers] == [0] * 6
    assert len(json.load(open(data_file, encoding="utf-8"))) == 90


def test_a_lock_left_by_a_dead_process_is_taken_over(tmp_path):
    lock = FileLock("x", directory=str(tmp_path), stale_after=0.2, timeout=2)
    open(lock.path, "w").write("99999")
    time.sleep(0.3)
    assert lock.acquire() is True
    lock.release()
    assert not os.path.exists(lock.path)


def test_waiting_too_long_carries_on_instead_of_hanging(tmp_path):
    first = FileLock("y", directory=str(tmp_path))
    first.acquire()
    second = FileLock("y", directory=str(tmp_path), timeout=0.2)
    started = time.time()
    assert second.acquire() is False and time.time() - started < 2
    first.release()


def test_atomic_write_leaves_no_temporary_files(tmp_path):
    target = str(tmp_path / "a" / "b.json")
    write_atomically(target, "{}")
    write_atomically(target, '{"x": 1}')
    assert json.load(open(target, encoding="utf-8")) == {"x": 1}
    assert os.listdir(tmp_path / "a") == ["b.json"]


# â”€â”€ finding the pages â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def make_wiki(root, files):
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


@pytest.fixture
def wiki(tmp_path):
    root = tmp_path / "FitNesseRoot"
    make_wiki(root, {
        "FrontPage/Suite1.wiki": "---\nSuite\n---\n",
        "FrontPage/Suite1/LoginPage.wiki": "---\nTest\n---\n|login test|\n",
        "FrontPage/Suite1/ApiChecks.wiki": "---\nTest\n---\n|get request fixture|\n",
        "FrontPage/Suite1/MockedApi.wiki": "---\nTest\n---\n|mock server fixture|\n|start server|\n",
        "FrontPage/Suite1/LoginTest.wiki": "!1 no front matter, but the name ends in Test\n",
        "FrontPage/Suite1/Notes.wiki": "---\nHelp\n---\nnot a test\n",
        "FrontPage/Suite1/SetUp.wiki": "---\nTest\n---\n",
        "FrontPage/Suite1/Inner/Deep.wiki": "---\nTest\n---\n",
        "FrontPage/Suite1/OldStyle/content.txt": "|login test|\n",
        "FrontPage/Suite1/OldStyle/properties.xml": "<properties><Test/></properties>",
    })
    return str(root)


def test_test_pages_are_found_below_a_suite(wiki):
    found = dict(ci_run.find_test_pages("FrontPage.Suite1", wiki))
    assert set(found) == {"FrontPage.Suite1.LoginPage", "FrontPage.Suite1.ApiChecks", "FrontPage.Suite1.MockedApi",
                          "FrontPage.Suite1.LoginTest", "FrontPage.Suite1.Inner.Deep", "FrontPage.Suite1.OldStyle"}
    assert found["FrontPage.Suite1.MockedApi"] is True and found["FrontPage.Suite1.ApiChecks"] is False


def test_a_test_page_is_its_own_list(wiki):
    assert ci_run.find_test_pages("FrontPage.Suite1.LoginPage", wiki) == [("FrontPage.Suite1.LoginPage", False)]


# â”€â”€ running them â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def counts(right=1, wrong=0, exceptions=0):
    return {"right": right, "wrong": wrong, "ignores": 0, "exceptions": exceptions}


def test_pages_run_at_the_same_time_and_mock_server_pages_run_last(wiki, monkeypatch):
    monkeypatch.setattr(ci_run, "FITNESSE_ROOT", wiki)
    active, peak, order = [], [0], []

    def runner(base, page, kind):
        active.append(page)
        peak[0] = max(peak[0], len(active))
        order.append(page)
        time.sleep(0.2)
        active.remove(page)
        return counts(), "<x/>"

    summary = ci_run.run_parallel("http://x", "FrontPage.Suite1", 4, runner)
    assert peak[0] >= 3                                         # really concurrent
    assert order[-1] == "FrontPage.Suite1.MockedApi"             # the page that needs the mock server's port goes last, alone
    assert summary["totals"]["right"] == 6 and summary["not_run"] == []


def test_totals_add_up_and_a_page_that_could_not_run_is_named(wiki, monkeypatch):
    monkeypatch.setattr(ci_run, "FITNESSE_ROOT", wiki)

    def runner(base, page, kind):
        if page.endswith("ApiChecks"):
            raise RuntimeError("FitNesse did not answer")
        return (counts(wrong=1) if page.endswith("LoginPage") else counts()), "<x/>"

    summary = ci_run.run_parallel("http://x", "FrontPage.Suite1", 2, runner)
    assert summary["not_run"] == ["FrontPage.Suite1.ApiChecks"]
    assert summary["totals"]["wrong"] == 1 and summary["totals"]["right"] == 5


def test_a_suite_without_test_pages_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(ci_run, "FITNESSE_ROOT", str(tmp_path))
    with pytest.raises(RuntimeError, match="No test pages"):
        ci_run.run_parallel("http://x", "FrontPage.Nothing", 2, lambda *a: (counts(), ""))


@pytest.mark.parametrize("results, expected", [
    ({"a": counts()}, 0),
    ({"a": counts(wrong=1)}, 1),
    ({"a": counts(exceptions=1)}, 1),
])
def test_exit_codes_of_a_parallel_run(monkeypatch, tmp_path, results, expected):
    summary = {"suite": "S", "workers": 2, "seconds": 1, "totals": counts(
        sum(c["right"] for c in results.values()), sum(c["wrong"] for c in results.values()),
        sum(c["exceptions"] for c in results.values())), "not_run": [],
        "pages": {n: {"counts": c, "seconds": 1, "error": ""} for n, c in results.items()}}
    monkeypatch.setattr(ci_run, "run_parallel", lambda *a, **k: summary)
    monkeypatch.setattr(ci_run, "VARIABLE_PAGE", str(tmp_path / "v.txt"))
    out = tmp_path / "r.xml"
    assert ci_run.main(["--suite", "S", "--parallel", "2", "--out", str(out)]) == expected
    assert json.load(open(tmp_path / "r.json", encoding="utf-8"))["totals"]["right"] == summary["totals"]["right"]
