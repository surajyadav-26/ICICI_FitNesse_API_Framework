"""API tables: the cells of the `?` columns are what each row expects, and the reports say so when they differ."""
import json

import pytest

from fixtures.api.get_request_fixture import GetRequestFixture


class FakeResponse:
    headers = {"Content-Type": "application/json", "X-Mode": "test"}

    def __init__(self, status, payload):
        self.status_code, self._payload, self.text = status, payload, json.dumps(payload)

    def json(self):
        return self._payload


@pytest.fixture
def api(monkeypatch):
    answers = []
    steps, records = [], []
    monkeypatch.setattr("fixtures.api.base_fixture.requests.request", lambda *a, **k: answers.pop(0))
    monkeypatch.setattr("fixtures.api.base_fixture.record_http_step",
                        lambda test, name, ok, ms, attachments, message="": steps.append((ok, message)))
    monkeypatch.setattr(GetRequestFixture, "_record_to_report",
                        lambda self, **kw: records.append((kw["right"], kw["wrong"])))
    monkeypatch.setattr("core.report_generator.add_record", lambda record: records.append(("step", record["url"])))
    return answers, steps, records


def play(header, rows, answers_for_rows, answers):
    """Plays what Slim does for a decision table: table(), then set_*, execute and the `?` outputs per row."""
    fixture = GetRequestFixture()
    fixture.table([header] + [list(row) for row in rows])
    outputs = []
    for row, answer in zip(rows, answers_for_rows):
        answers.append(answer)
        for column, value in zip(header, row):
            if not column.endswith("?"):
                getattr(fixture, "set_" + column.replace(" ", "_"))(value)
        fixture.execute()
        outputs.append({c.rstrip("?").replace(" ", "_"): getattr(fixture, c.rstrip("?").replace(" ", "_"))() for c in header if c.endswith("?")})
    return outputs


def test_a_404_test_passes_when_the_table_expects_a_404(api):
    answers, steps, records = api
    play(["url", "status code?"], [["http://x/missing", "404"]], [FakeResponse(404, {"error": "nf"})], answers)
    assert steps == [(True, "")] and records[0] == (1, 0)


def test_a_wrong_status_is_reported_with_expected_and_actual(api):
    answers, steps, records = api
    play(["url", "status code?"], [["http://x/missing", "200"]], [FakeResponse(404, {})], answers)
    assert steps[0][0] is False and steps[0][1] == "status code: expected '200' but was '404'"
    assert records[0] == (0, 1) and records[1] == ("step", "FAILED: GET http://x/missing - status code: expected '200' but was '404'")


def test_a_wrong_json_value_and_the_row_it_belongs_to(api):
    answers, steps, records = api
    play(["url", "key", "status code?", "json value?"],
         [["http://x/a", "name", "200", "Asha"], ["http://x/b", "name", "200", "Ravi"]],
         [FakeResponse(200, {"name": "Asha"}), FakeResponse(200, {"name": "Meera"})], answers)
    assert steps[0] == (True, "")
    assert steps[1][0] is False and steps[1][1] == "json value: expected 'Ravi' but was 'Meera'"


def test_empty_and_comparator_cells_are_not_judged(api):
    answers, steps, records = api
    play(["url", "status code?", "response time?"], [["http://x/a", "", ""], ["http://x/b", "<500", ""]],
         [FakeResponse(200, {}), FakeResponse(200, {})], answers)
    assert steps == [(True, ""), (True, "")]


def test_without_a_table_the_old_behaviour_stays(api):
    answers, steps, records = api
    answers.append(FakeResponse(404, {}))
    fixture = GetRequestFixture()
    fixture.set_url("http://x/missing")
    fixture.execute()
    assert steps[0][0] is False and steps[0][1] == "Unexpected status 404"


def test_the_allure_categories_know_the_new_messages():
    from core import allure_report
    import re
    by_name = {c["name"]: c for c in allure_report.CATEGORIES}
    assert re.search(by_name["API failures"]["messageRegex"], "status code: expected '200' but was '404'")
    assert re.search(by_name["API failures"]["messageRegex"], "Response does not match the schema: $.id")
    assert re.search(by_name["Wrong result (expected vs actual)"]["messageRegex"], "login_result: expected 'Success' but was 'No'")
