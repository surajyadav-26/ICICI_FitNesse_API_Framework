"""JSON Schema check of API responses: the validator and the `schema` / `schema valid?` columns."""
import json
import os

import pytest

from core import json_schema
from fixtures.api.get_request_fixture import GetRequestFixture

USER = {"type": "object", "required": ["id", "name"],
        "properties": {"id": {"type": "integer"}, "name": {"type": "string", "minLength": 1},
                       "role": {"enum": ["admin", "viewer"]}, "tags": {"type": "array", "items": {"type": "string"}}},
        "additionalProperties": False}


def test_a_conforming_response_has_no_problems():
    assert json_schema.check({"id": 1, "name": "Asha", "role": "admin", "tags": ["a"]}, USER) == []


def test_problems_name_the_path_and_the_difference():
    problems = json_schema.check({"id": "1", "role": "boss", "tags": ["a", 2], "extra": True}, USER)
    assert "$: required property 'name' is missing" in problems
    assert "$.id: expected integer but found string" in problems
    assert any(p.startswith("$.role:") and "is not one of" in p for p in problems)
    assert "$.tags[1]: expected string but found integer" in problems
    assert "$: property 'extra' is not allowed" in problems


def test_numbers_text_and_lists():
    schema = {"type": "object", "properties": {
        "age": {"type": "number", "minimum": 18, "maximum": 65}, "code": {"type": "string", "pattern": "^[A-Z]{3}$"},
        "items": {"type": "array", "minItems": 1, "uniqueItems": True}}}
    assert json_schema.check({"age": 30, "code": "ABC", "items": [1, 2]}, schema) == []
    problems = json_schema.check({"age": 10, "code": "abc", "items": [1, 1]}, schema)
    assert any("below the minimum 18" in p for p in problems) and any("does not match the pattern" in p for p in problems)
    assert any("not unique" in p for p in problems)
    assert json_schema.check({"items": []}, schema) == ["$.items: has 0 item(s), at least 1 expected"]


def test_combinations_and_references():
    schema = {"definitions": {"id": {"type": "integer"}}, "type": "object",
              "properties": {"id": {"$ref": "#/definitions/id"}, "v": {"anyOf": [{"type": "string"}, {"type": "null"}]}}}
    assert json_schema.check({"id": 5, "v": None}, schema) == []
    assert json_schema.check({"id": "x", "v": 3}, schema) != []


def test_an_unsupported_keyword_is_a_problem_not_a_silent_pass():
    problems = json_schema.check({"a": 1}, {"type": "object", "dependencies": {"a": ["b"]}})
    assert problems == ["$: unsupported schema keyword 'dependencies'"]


def test_schema_comes_from_inline_json_or_a_file(tmp_path, monkeypatch):
    monkeypatch.setattr(json_schema, "SCHEMA_DIR", str(tmp_path))
    (tmp_path / "user.json").write_text(json.dumps(USER), encoding="utf-8")
    assert json_schema.load_schema("user")["required"] == ["id", "name"]
    assert json_schema.load_schema("user.json")["type"] == "object"
    assert json_schema.load_schema('{"type":"array"}') == {"type": "array"}
    for bad in ("", "../secret", "missing", "{not json"):
        with pytest.raises(json_schema.SchemaError):
            json_schema.load_schema(bad)


class FakeResponse:
    status_code = 200
    headers = {"Content-Type": "application/json"}

    def __init__(self, payload):
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


@pytest.fixture
def get_fixture(monkeypatch, tmp_path):
    monkeypatch.setattr(json_schema, "SCHEMA_DIR", str(tmp_path))
    (tmp_path / "user.json").write_text(json.dumps(USER), encoding="utf-8")
    state = {"payload": {"id": 1, "name": "Asha"}}
    monkeypatch.setattr("fixtures.api.base_fixture.requests.request", lambda *a, **k: FakeResponse(state["payload"]))
    fixture = GetRequestFixture()
    fixture.set_url("http://example.test/users/1")
    return fixture, state


def test_column_fixture_reports_valid(get_fixture):
    fixture, _ = get_fixture
    fixture.set_schema("user")
    fixture.execute()
    assert fixture.schema_valid() == "valid"


def test_column_fixture_reports_the_difference_and_fails_the_allure_step(get_fixture, monkeypatch):
    fixture, state = get_fixture
    state["payload"] = {"id": "1"}
    steps = []
    monkeypatch.setattr("fixtures.api.base_fixture.record_http_step",
                        lambda test, name, ok, ms, attachments, message="": steps.append((ok, message)))
    fixture.set_schema("user")
    fixture.execute()
    assert fixture.schema_valid().startswith("invalid: $: required property 'name' is missing")
    assert steps and steps[0][0] is False and "does not match the schema" in steps[0][1]


def test_no_schema_changes_nothing(get_fixture):
    fixture, _ = get_fixture
    fixture.execute()
    assert fixture.schema_valid() == "no schema" and fixture.status_code() == "200"


def test_the_columns_are_offered_in_the_step_builder():
    names = {column.name for column in GetRequestFixture.COLUMNS}
    assert {"schema", "schema_valid"} <= names


def test_a_schema_file_saved_with_a_bom_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(json_schema, "SCHEMA_DIR", str(tmp_path))
    (tmp_path / "bom.json").write_bytes(b"\xef\xbb\xbf" + json.dumps({"type": "object"}).encode("utf-8"))
    assert json_schema.load_schema("bom") == {"type": "object"}
