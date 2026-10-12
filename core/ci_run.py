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

Exit code 1 when a table is wrong or raised an exception, 2 when FitNesse could not be reached or answered with something
unreadable, so a runner can tell "the tests failed" from "the tests did not run".
"""
import argparse
import os
import re
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


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", default="FrontPage")
    parser.add_argument("--kind", choices=("suite", "test"), default="suite")
    parser.add_argument("--base-url", default=Config.fitnesse_url())
    parser.add_argument("--api-url", default="")
    parser.add_argument("--ui-url", default="")
    parser.add_argument("--out", default="test_results.xml")
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args(argv)

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


if __name__ == "__main__":
    sys.exit(main())
