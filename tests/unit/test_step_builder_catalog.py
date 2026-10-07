"""Every row the Step Builder can generate must resolve to a real UiFixture method."""
import os
import re

import pytest

from fixtures.ui_fixture import UiFixture

HEADER = os.path.join(os.path.dirname(__file__), "..", "..", "FitNesseRoot", "PageHeader", "content.txt")
ACTION_PATTERN = re.compile(r'\{c:"([^"]+)", l:"([^"]+)", s:\[([^\]]*)\], p:\[(.*?)\], d:')

REQUIRED_ACTIONS = [
    "Open Browser", "Navigate to URL", "Refresh Page", "Go Back", "Go Forward", "Close Browser",
    "Enter Text", "Clear Field", "Press Key", "Click Element", "Double Click", "Right Click", "Hover",
    "Scroll to Element", "Select Dropdown", "Check Checkbox", "Uncheck Checkbox", "Select Radio Button",
    "Set Toggle", "Wait for Element Visible", "Wait for Element Invisible", "Wait for Element Clickable",
    "Wait for Text", "Wait for Page Load", "Wait for Timeout", "Verify Text Present", "Verify Text Not Present",
    "Verify Element Present", "Verify Element Not Present", "Verify Element Visible", "Verify Element Enabled",
    "Verify Field Value", "Verify Dropdown Value", "Verify URL", "Verify Page Title", "Handle Alert - Accept",
    "Handle Alert - Dismiss", "Verify Alert Text", "Switch to Frame", "Switch to Default Frame",
    "Switch Window/Tab", "Close Current Tab", "Upload File", "Verify File Downloaded", "Set Variable",
    "Get Variable", "Capture Text to Variable", "Generate Test Data", "IF", "ELSE", "END IF", "FOR EACH",
    "END LOOP", "Break", "Retry Action", "Continue on Failure", "Stop on Failure", "Take Screenshot",
    "Execute Reusable Component",
]


def load_actions():
    with open(HEADER, encoding="utf-8") as header:
        text = header.read()
    actions = []
    for category, label, tokens, params in ACTION_PATTERN.findall(text):
        tokens = re.findall(r'"([^"]*)"', tokens)
        optional = set(re.findall(r'\["(\w+)","[^"]*","\w+","opt"', params))
        actions.append((category, label, tokens, optional))
    return actions


def method_for(tokens):
    """Slim naming: keyword cells sit at even positions, arguments at odd ones."""
    if tokens[0] in ("ensure", "reject", "show"):
        tokens = tokens[1:]
    elif tokens[0] == "check":
        tokens = tokens[1:-1]
    return "_".join(" ".join(tokens[0::2]).lower().split())


def row_variants(tokens, optional):
    """The full row, plus the row generated when every optional parameter is left empty."""
    trimmed = []
    for token in tokens:
        match = re.fullmatch(r"\{(\w+)\}", token)
        if match and match.group(1) in optional:
            if len(trimmed) > 1:
                trimmed.pop()
            continue
        trimmed.append(token)
    return [list(tokens)] + ([trimmed] if trimmed != list(tokens) else [])


ACTIONS = load_actions()


def test_catalog_covers_every_requested_action():
    labels = {label for _, label, _, _ in ACTIONS}
    assert [label for label in REQUIRED_ACTIONS if label not in labels] == []


@pytest.mark.parametrize("category,label,tokens,optional", ACTIONS, ids=[a[1] for a in ACTIONS])
def test_builder_row_maps_to_fixture_method(category, label, tokens, optional):
    fixture = UiFixture("catalog-test")
    for variant in row_variants(tokens, optional):
        method = method_for(variant)
        assert callable(getattr(fixture, method, None)), f"{label}: no UiFixture.{method} for row {variant}"
