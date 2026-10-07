"""Unit tests for the UI flow engine (variables, IF/ELSE, FOR EACH, failure modes, components)."""
import pytest

from fixtures import ui_flow
from fixtures.ui_flow import FlowMixin, step


class FakeFixture(FlowMixin):
    """Minimal host for FlowMixin: records executed actions instead of driving a browser."""

    def __init__(self):
        self._init_flow()
        self.done = []
        self.visible = set()
        self.attempts = 0

    def _ok(self, description):
        return True

    def _peek(self, kind, argument):
        return argument in self.visible

    @step
    def act(self, value):
        self.done.append(value)
        return True

    @step
    def fail(self):
        self.done.append("fail")
        return False

    @step
    def flaky(self):
        self.attempts += 1
        return self.attempts >= 3

    @step(getter=True)
    def read(self, value):
        return value


def run(fixture, *rows):
    for name, *args in rows:
        getattr(fixture, name)(*args)


def test_variable_substitution_and_unknown_variable_left_literal():
    fx = FakeFixture()
    run(fx, ("set_variable_to", "who", "Asha"), ("act", "hi ${who} ${missing}"))
    assert fx.done == ["hi Asha ${missing}"]
    assert fx.get_variable("who") == "Asha"
    assert fx.get_variable("nope") == "variable not found"


def test_html_cell_cleanup_for_non_raw_steps():
    fx = FakeFixture()
    fx.act('a &amp; b <a href="http://x">http://x</a>')
    assert fx.done == ["a & b http://x"]


def test_if_else_picks_true_branch_and_skips_other():
    fx = FakeFixture()
    run(fx, ("set_variable_to", "role", "admin"),
        ("if_condition", "${role} == admin"), ("act", "admin-branch"),
        ("else_branch",), ("act", "other-branch"), ("end_if",))
    assert fx.done == ["admin-branch"]


def test_else_runs_when_condition_false_and_nested_if_in_skipped_branch():
    fx = FakeFixture()
    run(fx, ("if_condition", "1 > 2"),
        ("if_condition", "1 == 1"), ("act", "nested-should-skip"), ("end_if",),
        ("else_branch",), ("act", "else-ran"), ("end_if",))
    assert fx.done == ["else-ran"]


def test_if_on_page_state_prefixes():
    fx = FakeFixture()
    fx.visible.add("#banner")
    run(fx, ("if_condition", "element visible: #banner"), ("act", "yes"), ("end_if",),
        ("if_condition", "element visible: #nope"), ("act", "no"), ("end_if",))
    assert fx.done == ["yes"]


@pytest.mark.parametrize("condition,expected", [
    ("5 > 3", True), ("2 >= 3", False), ("abc contains b", True), ("abc not contains b", False),
    ("A ~= a", True), ("x != y", True), ("false", False), ("something", True),
])
def test_conditions(condition, expected):
    assert FakeFixture()._evaluate_condition(condition) is expected


def test_for_each_replays_body_per_item_with_variable():
    fx = FakeFixture()
    run(fx, ("for_each_in", "n", "a,b,c"), ("act", "item-${n}"), ("end_loop",))
    assert fx.done == ["item-a", "item-b", "item-c"]


def test_for_each_numeric_range_and_nested_loops():
    fx = FakeFixture()
    run(fx, ("for_each_in", "a", "1..2"), ("for_each_in", "b", "x,y"), ("act", "${a}${b}"), ("end_loop",), ("end_loop",))
    assert fx.done == ["1x", "1y", "2x", "2y"]


def test_break_leaves_loop_and_skips_rest_of_iteration():
    fx = FakeFixture()
    run(fx, ("for_each_in", "n", "1,2,3,4"),
        ("if_condition", "${n} == 3"), ("break_loop",), ("end_if",),
        ("act", "n${n}"), ("end_loop",))
    assert fx.done == ["n1", "n2"]


def test_loop_inside_false_if_does_not_run():
    fx = FakeFixture()
    run(fx, ("if_condition", "false"), ("for_each_in", "n", "1,2"), ("act", "x"), ("end_loop",), ("end_if",), ("act", "after"))
    assert fx.done == ["after"]


def test_loop_reports_failed_steps():
    fx = FakeFixture()
    fx.for_each_in("n", "1,2")
    fx.fail()
    assert fx.end_loop() == "2 step(s) failed inside the loop"


def test_unbalanced_flow_keywords_report_errors():
    fx = FakeFixture()
    assert fx.end_if() == "END IF without IF"
    assert fx.else_branch() == "ELSE without IF"
    assert fx.break_loop() == "BREAK outside a loop"
    assert fx.end_loop() == "END LOOP without FOR EACH"


def test_stop_on_failure_skips_remaining_steps_and_continue_resumes():
    fx = FakeFixture()
    fx.stop_on_failure()
    fx.fail()
    assert fx.act("later") == "skipped (stop on failure)"
    fx.continue_on_failure()
    assert fx.act("resumed") is True
    assert fx.done == ["fail", "resumed"]


def test_default_mode_continues_after_failure():
    fx = FakeFixture()
    fx.fail()
    fx.act("still-runs")
    assert fx.done == ["fail", "still-runs"]


def test_retry_action_applies_to_next_step_only(monkeypatch):
    monkeypatch.setattr(ui_flow.time, "sleep", lambda s: None)
    fx = FakeFixture()
    fx.retry_action("2")
    assert fx.flaky() is True
    assert fx.attempts == 3
    fx.attempts = 0
    assert fx.flaky() is False and fx.attempts == 1  # the retry was consumed by the first step


def test_getter_steps_are_not_failures():
    fx = FakeFixture()
    fx.stop_on_failure()
    assert fx.read("") == ""
    assert fx.act("ok") is True


def test_reusable_component_runs_steps_with_parameters(tmp_path, monkeypatch):
    monkeypatch.setattr(ui_flow, "COMPONENTS_DIR", str(tmp_path))
    (tmp_path / "Greet.flow").write_text(
        "# demo component\n| set variable | greeting | to | hello ${who} |\n| act | ${greeting} |\n| note | ignored |\n",
        encoding="utf-8")
    fx = FakeFixture()
    assert fx.execute_reusable_component_with("Greet", "who=Ravi") is True
    assert fx.done == ["hello Ravi"]
    assert "who" not in fx._vars                          # parameters are local
    assert fx.get_variable("greeting") == "hello Ravi"    # variables set inside persist


def test_reusable_component_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(ui_flow, "COMPONENTS_DIR", str(tmp_path))
    fx = FakeFixture()
    assert "not found" in fx.execute_reusable_component("Missing")
    assert "not found" in fx.execute_reusable_component("../../etc/passwd")
    (tmp_path / "Bad.flow").write_text("| no such step |\n| act | after |\n", encoding="utf-8")
    assert "failed" in fx.execute_reusable_component("Bad")
    assert fx.done == ["after"]


def test_reusable_component_recursion_is_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(ui_flow, "COMPONENTS_DIR", str(tmp_path))
    (tmp_path / "Loop.flow").write_text("| execute reusable component | Loop |\n", encoding="utf-8")
    fx = FakeFixture()
    assert "failed" in fx.execute_reusable_component("Loop")
