"""
JSON Schema check for API responses, without an extra package.

    problems = check(response_json, schema_dict)      # [] when the response conforms
    schema = load_schema('{"type":"object","required":["id"]}')
    schema = load_schema("user")                      # data/schemas/user.json

Supported keywords: type, enum, const, required, properties, additionalProperties, items, minItems, maxItems, uniqueItems,
minimum, maximum, exclusiveMinimum, exclusiveMaximum, minLength, maxLength, pattern, allOf, anyOf, oneOf, not and local
"$ref": "#/definitions/name" (or "#/$defs/name"). Annotations ($schema, $id, title, description, default, examples, format)
are accepted and ignored. Any other keyword is reported as a problem instead of being skipped silently, so a schema that
cannot be enforced never passes by accident.
"""
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_DIR = os.path.join(BASE_DIR, "data", "schemas")

_ANNOTATIONS = {"$schema", "$id", "$comment", "title", "description", "default", "examples", "format", "definitions", "$defs",
                "readOnly", "writeOnly", "deprecated"}
_KEYWORDS = {"type", "enum", "const", "required", "properties", "additionalProperties", "items", "minItems", "maxItems",
             "uniqueItems", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "pattern",
             "allOf", "anyOf", "oneOf", "not", "$ref"}
_MAX_PROBLEMS = 20


class SchemaError(Exception):
    """The schema itself cannot be used (not JSON, unknown file)."""


def load_schema(text: str) -> dict:
    """A schema from inline JSON, or from data/schemas/<name>.json."""
    text = str(text or "").strip()
    if not text:
        raise SchemaError("The schema cell is empty")
    if text.startswith("{") or text.startswith("true") or text.startswith("false"):
        try:
            return json.loads(text)
        except ValueError as error:
            raise SchemaError(f"The schema is not valid JSON: {error}")
    name = text[:-5] if text.lower().endswith(".json") else text
    if not re.fullmatch(r"[\w\-. ]+", name) or ".." in name:
        raise SchemaError(f"'{text}' is neither JSON nor a schema file name in data/schemas")
    path = os.path.join(SCHEMA_DIR, name + ".json")
    if not os.path.isfile(path):
        raise SchemaError(f"Schema file not found: data/schemas/{name}.json")
    try:
        with open(path, "r", encoding="utf-8-sig") as schema_file:        # Notepad adds a BOM; accept it
            return json.load(schema_file)
    except ValueError as error:
        raise SchemaError(f"data/schemas/{name}.json is not valid JSON: {error}")


def check(instance, schema) -> list:
    """Problems found (each 'path: message'); an empty list means the instance conforms."""
    problems: list = []
    _validate(instance, schema, "$", schema if isinstance(schema, dict) else {}, problems)
    return problems[:_MAX_PROBLEMS]


def _type_ok(value, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool) or (isinstance(value, float) and value.is_integer())
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "null":
        return value is None
    return False


def _type_name(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def _resolve(ref: str, root: dict):
    if not ref.startswith("#/"):
        raise SchemaError(f"Only local references are supported, not '{ref}'")
    node = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            raise SchemaError(f"Reference '{ref}' does not exist in the schema")
        node = node[part]
    return node


def _validate(value, schema, path: str, root: dict, problems: list) -> None:
    if len(problems) >= _MAX_PROBLEMS:
        return
    if schema is True or schema == {}:
        return
    if schema is False:
        problems.append(f"{path}: no value is allowed here")
        return
    if not isinstance(schema, dict):
        problems.append(f"{path}: the schema must be an object")
        return
    for keyword in schema:
        if keyword not in _KEYWORDS and keyword not in _ANNOTATIONS:
            problems.append(f"{path}: unsupported schema keyword '{keyword}'")
    if "$ref" in schema:
        try:
            _validate(value, _resolve(schema["$ref"], root), path, root, problems)
        except SchemaError as error:
            problems.append(f"{path}: {error}")

    expected = schema.get("type")
    if expected is not None:
        names = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(value, name) for name in names):
            problems.append(f"{path}: expected {' or '.join(names)} but found {_type_name(value)}")
            return
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path}: {json.dumps(value)} is not one of {json.dumps(schema['enum'])}")
    if "const" in schema and value != schema["const"]:
        problems.append(f"{path}: expected {json.dumps(schema['const'])} but found {json.dumps(value)}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            problems.append(f"{path}: {value} is below the minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            problems.append(f"{path}: {value} is above the maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            problems.append(f"{path}: {value} must be above {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            problems.append(f"{path}: {value} must be below {schema['exclusiveMaximum']}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            problems.append(f"{path}: text is shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            problems.append(f"{path}: text is longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            problems.append(f"{path}: text does not match the pattern {schema['pattern']}")

    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                problems.append(f"{path}: required property '{name}' is missing")
        properties = schema.get("properties", {})
        for name, sub_schema in properties.items():
            if name in value:
                _validate(value[name], sub_schema, f"{path}.{name}", root, problems)
        extra = schema.get("additionalProperties", True)
        if extra is not True:
            for name in value:
                if name in properties:
                    continue
                if extra is False:
                    problems.append(f"{path}: property '{name}' is not allowed")
                else:
                    _validate(value[name], extra, f"{path}.{name}", root, problems)

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            problems.append(f"{path}: has {len(value)} item(s), at least {schema['minItems']} expected")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            problems.append(f"{path}: has {len(value)} item(s), at most {schema['maxItems']} expected")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            problems.append(f"{path}: items are not unique")
        items = schema.get("items")
        if isinstance(items, dict) or isinstance(items, bool):
            for index, item in enumerate(value):
                _validate(item, items, f"{path}[{index}]", root, problems)
        elif isinstance(items, list):
            for index, (item, sub_schema) in enumerate(zip(value, items)):
                _validate(item, sub_schema, f"{path}[{index}]", root, problems)

    for sub_schema in schema.get("allOf", []):
        _validate(value, sub_schema, path, root, problems)
    if "anyOf" in schema:
        if not any(not check_branch(value, sub_schema, root) for sub_schema in schema["anyOf"]):
            problems.append(f"{path}: does not match any of the allowed shapes (anyOf)")
    if "oneOf" in schema:
        matches = sum(1 for sub_schema in schema["oneOf"] if not check_branch(value, sub_schema, root))
        if matches != 1:
            problems.append(f"{path}: matches {matches} of the allowed shapes, exactly 1 expected (oneOf)")
    if "not" in schema and not check_branch(value, schema["not"], root):
        problems.append(f"{path}: must not match the schema in 'not'")


def check_branch(value, schema, root) -> list:
    problems: list = []
    _validate(value, schema, "$", root, problems)
    return problems
