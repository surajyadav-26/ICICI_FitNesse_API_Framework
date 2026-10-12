"""
Runs a FitNesse suite from a CI job (GitHub Actions, or any other runner) and turns the answer into an exit code.

    python -m core.ci_run --suite FrontPage.Regression
    python -m core.ci_run --suite FrontPage.Regression.LoginPage --kind test
    python -m core.ci_run --suite FrontPage --api-url https://api.example.com --ui-url https://app.example.com/

  --api-url / --ui-url  written to VariablePage as API_BASE_URL / UI_BASE_URL before the run (the environment of this run)
  --kind                suite (default) or test; a single page is run with ?test
  --base-url            FitNesse address (default: this copy's FITNESSE_PORT)
  --out                 where FitNesse's result XML is saved (default test_results.xml)
  --no-fail             always exit 0; the counts are still printed
  --parallel N          run the test pages of the suite N at a time (default 1 = the suite runs one page after another)

Exit code 1 when a table is wrong or raised an exception, 2 when FitNesse could not be reached or answered with something
unreadable, so a runner can tell "the tests failed" from "the tests did not run".

Parallel runs
    FitNesse runs the pages of one suite request one after another, but it serves several requests at the same time, each
    with its own Slim process. --parallel N finds the test pages under the suite and sends N requests at once. Pages that
    use the embedded mock server (one fixed port) run afterwards, one at a time. SetUp / TearDown pages are not run on
    their own. The result of each page is printed, and the totals are written as JSON next to --out.
"""
import argparse
import concurrent.futures
import json
import os
import re
import time
import sys
import urllib.error
import urllib.request
from xml.etree import ElementTree

from core.config import Config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIABLE_PAGE = os.path.join(BASE_DIR, "FitNesseRoot", "VariablePage", "content.txt")
KEYS = ("right", "wrong", "ignores", "exceptions")


def set_environment(api_url: str = "", ui_url: str = "", path: str = None) -> dict:
    """Writes the API / UI base URLs of this run into VariablePage; an empty value keeps what the page has."""
    path = path or VARIABLE_PAGE
    text = open(path, encoding="utf-8-sig").read() if os.path.exists(path) else ""
    written = {}
    for name, value in (("API_BASE_URL", api_url), ("UI_BASE_URL", ui_url)):
        value = str(value or "").strip()
        if not value:
            continue
        if re.search(r"[{}\r\n]", value):
            raise ValueError(f"{name} contains characters that are not allowed in a wiki variable")
        line = f"!define {name} {{{value}}}"
        pattern = re.compile(rf"^!define {name} \{{[^}}]*\}}\s*$", re.M)
        if pattern.search(text):
            text = pattern.sub(lambda match: line, text)
        else:
            text = (text.rstrip("\n") + "\n" if text.strip() else "") + line + "\n"
        written[name] = value
    if written:
        with open(path, "w", encoding="utf-8", newline="\n") as page:
            page.write(text)
    return written


def parse_counts(body: str, name: str = "") -> dict:
    """Right / wrong / ignores / exceptions from FitNesse's XML answer; raises RuntimeError when it is not a result."""
    try:
        root = ElementTree.fromstring(body.lstrip("﻿"))
    except ElementTree.ParseError:
        raise RuntimeError(f"FitNesse answered with something that is not a result ({body[:120]!r})")
    final = root.find("finalCounts")
    if final is not None:
        return {key: int(final.findtext(key, "0") or 0) for key in KEYS}
    results = root.findall("result")
    if not results:
        raise RuntimeError(f"The answer has no results; is '{name}' a test or suite page?")
    return {key: sum(int(node.text or 0) for node in root.findall(f"./result/counts/{key}")) for key in KEYS}


def run(base_url: str, name: str, kind: str = "suite", timeout: int = 3600) -> tuple:
    """Runs the page; returns (counts, raw XML). Raises RuntimeError when FitNesse cannot be reached or understood."""
    url = f"{base_url.rstrip('/')}/{name}?{'test' if kind == 'test' else 'suite'}&format=xml"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as error:
        raise RuntimeError(f"FitNesse did not answer at {url}: {error}")
    return parse_counts(body, name), body


FITNESSE_ROOT = os.path.join(BASE_DIR, "FitNesseRoot")
_NOT_RUN_ALONE = {"SetUp", "TearDown", "SuiteSetUp", "SuiteTearDown"}
MAX_WORKERS = 8


def _front_matter(text: str) -> set:
    """Page types written in a .wiki file's front matter ("---\nTest\n---")."""
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return set()
    found = set()
    for line in lines[1:12]:
        if line.strip() == "---":
            break
        found.add(line.split(":")[0].strip())
    return found


def _page_info(path: str, is_directory: bool) -> tuple:
    """(is a test page, text of the page) for a wiki file or a page folder."""
    try:
        if is_directory:
            properties = os.path.join(path, "properties.xml")
            props = open(properties, encoding="utf-8-sig").read() if os.path.exists(properties) else ""
            content = os.path.join(path, "content.txt")
            text = open(content, encoding="utf-8-sig").read() if os.path.exists(content) else ""
            return "<Test" in props, text
        text = open(path, encoding="utf-8-sig").read()
        return "Test" in _front_matter(text), text
    except OSError:
        return False, ""


def find_test_pages(suite: str, root: str = None) -> list:
    """
    Test pages under a suite (or the page itself when it is a test), as [(page name, uses the mock server)].
    Read from the wiki files, so nothing has to run to find them.
    """
    root = root or FITNESSE_ROOT
    parts = suite.split(".")
    pages = []

    def add(name: str, path: str, directory: bool) -> None:
        if name.split(".")[-1] in _NOT_RUN_ALONE:
            return
        is_test, text = _page_info(path, directory)
        last = name.split(".")[-1]
        # FitNesse also treats a page named Test... or ...Test as a test page, whatever its properties say
        if is_test or last.startswith("Test") or last.endswith("Test"):
            pages.append((name, "mock server fixture" in text.lower()))

    own_file = os.path.join(root, *parts) + ".wiki"
    own_dir = os.path.join(root, *parts)
    if os.path.isfile(own_file):
        add(suite, own_file, False)
    elif os.path.isdir(own_dir) and os.path.exists(os.path.join(own_dir, "content.txt")):
        add(suite, own_dir, True)
    if pages:
        return pages                                    # the page is a test itself

    for base, directories, files in os.walk(own_dir):
        directories.sort()
        relative = os.path.relpath(base, own_dir)
        prefix = suite if relative == "." else suite + "." + relative.replace(os.sep, ".")
        for name in sorted(files):
            if name.endswith(".wiki"):
                add(f"{prefix}.{name[:-5]}", os.path.join(base, name), False)
        if relative != "." and os.path.exists(os.path.join(base, "content.txt")):
            add(prefix, base, True)
    return pages


def run_parallel(base_url: str, suite: str, workers: int, runner=None) -> dict:
    """Runs every test page of the suite, `workers` at a time; returns the totals and the result of each page."""
    runner = runner or run
    pages = find_test_pages(suite)
    if not pages:
        raise RuntimeError(f"No test pages were found below '{suite}' in {FITNESSE_ROOT}")
    parallel = [name for name, mock in pages if not mock]
    serial = [name for name, mock in pages if mock]
    results = {}

    def one(name: str) -> tuple:
        started = time.time()
        try:
            counts, _ = runner(base_url, name, "test")
            return name, {"counts": counts, "seconds": round(time.time() - started, 1), "error": ""}
        except RuntimeError as error:
            return name, {"counts": dict.fromkeys(KEYS, 0), "seconds": round(time.time() - started, 1), "error": str(error)}

    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, MAX_WORKERS))) as pool:
        for name, outcome in pool.map(one, parallel):
            results[name] = outcome
    for name in serial:                                  # they share the mock server's fixed port
        results[name] = one(name)[1]

    totals = {key: sum(item["counts"][key] for item in results.values()) for key in KEYS}
    return {"suite": suite, "workers": workers, "seconds": round(time.time() - started, 1), "totals": totals,
            "not_run": [name for name, item in results.items() if item["error"]], "pages": results}


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", default="FrontPage")
    parser.add_argument("--kind", choices=("suite", "test"), default="suite")
    parser.add_argument("--base-url", default=Config.fitnesse_url())
    parser.add_argument("--api-url", default="")
    parser.add_argument("--ui-url", default="")
    parser.add_argument("--out", default="test_results.xml")
    parser.add_argument("--no-fail", action="store_true")
    parser.add_argument("--parallel", type=int, default=1)
    args = parser.parse_args(argv)

    if args.parallel > 1 and args.kind == "suite":
        return _main_parallel(args)

    try:
        for name, value in set_environment(args.api_url, args.ui_url).items():
            print(f"[ci-run] {name} = {value}")
        counts, body = run(args.base_url, args.suite, args.kind)
    except (RuntimeError, ValueError) as error:
        print(f"[ci-run] could not run: {error}")
        return 2

    with open(args.out, "w", encoding="utf-8") as saved:
        saved.write(body)
    print(f"[ci-run] {args.suite}: right={counts['right']} wrong={counts['wrong']} "
          f"ignores={counts['ignores']} exceptions={counts['exceptions']}")
    failed = counts["wrong"] > 0 or counts["exceptions"] > 0
    if failed:
        print("[ci-run] the run has failures")
    return 0 if (args.no_fail or not failed) else 1


def _main_parallel(args) -> int:
    try:
        for name, value in set_environment(args.api_url, args.ui_url).items():
            print(f"[ci-run] {name} = {value}")
        summary = run_parallel(args.base_url, args.suite, args.parallel)
    except (RuntimeError, ValueError) as error:
        print(f"[ci-run] could not run: {error}")
        return 2
    for name, item in summary["pages"].items():
        counts = item["counts"]
        state = f"could not run: {item['error']}" if item["error"] else (
            f"right={counts['right']} wrong={counts['wrong']} ignores={counts['ignores']} exceptions={counts['exceptions']}")
        print(f"[ci-run]   {name}: {state} ({item['seconds']} s)")
    totals = summary["totals"]
    print(f"[ci-run] {args.suite} with {min(args.parallel, MAX_WORKERS)} worker(s), {summary['seconds']} s: "
          f"right={totals['right']} wrong={totals['wrong']} ignores={totals['ignores']} exceptions={totals['exceptions']}")
    target = os.path.splitext(args.out)[0] + ".json"
    with open(target, "w", encoding="utf-8") as saved:
        json.dump({key: value for key, value in summary.items()}, saved, indent=2)
    if summary["not_run"]:
        print(f"[ci-run] {len(summary['not_run'])} page(s) could not run")
        return 2
    failed = totals["wrong"] > 0 or totals["exceptions"] > 0
    if failed:
        print("[ci-run] the run has failures")
    return 0 if (args.no_fail or not failed) else 1


if __name__ == "__main__":
    sys.exit(main())
