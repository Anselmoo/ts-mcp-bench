"""Tests for tsbench.core.schema (the small JSON-Schema subset used by plans and answers)."""
from __future__ import annotations

import pytest

from tsbench.core.schema import _resolve, _type_matches, validate_instance

DEFS = {"$defs": {"n": {"type": "integer"}}}
ONE_OF = {
    "oneOf": [{"$ref": "#/$defs/header"}, {"$ref": "#/$defs/run"}],
    "$defs": {
        "header": {"type": "object", "properties": {"kind": {"const": "header"}, "n": {"type": "integer"}},
                   "required": ["kind", "n"]},
        "run": {"type": "object", "properties": {"kind": {"const": "run"}}, "required": ["kind"]},
    },
}


def test_type_matches_each_json_type():
    assert _type_matches(None, "null") and not _type_matches(0, "null")
    assert _type_matches(True, "boolean") and not _type_matches(1, "boolean")
    assert _type_matches(3, "integer") and not _type_matches(3.5, "integer") and not _type_matches(True, "integer")
    assert _type_matches(3.5, "number") and _type_matches(3, "number") and not _type_matches(False, "number")
    assert _type_matches("x", "string") and _type_matches({}, "object") and _type_matches([], "array")
    assert not _type_matches([], "object")


def test_validate_instance_applies_the_type_rules():
    schema = {"type": ["integer", "null"]}
    assert validate_instance(schema, None) == []
    assert validate_instance(schema, 2) == []
    assert validate_instance(schema, True)
    assert validate_instance(schema, 2.5)


def test_type_errors_name_every_allowed_type_and_the_real_type():
    assert validate_instance({"type": ["integer", "null"]}, "x") == ["$: expected integer|null, got str"]
    assert validate_instance({"type": "integer"}, 2.5) == ["$: expected integer, got float"]
    assert validate_instance({"type": "string"}, None) == ["$: expected string, got NoneType"]


def test_errors_start_at_the_root_path_by_default():
    assert validate_instance({"type": "string"}, 1) == ["$: expected string, got int"]
    assert validate_instance({"type": "string"}, 1, path="$.x") == ["$.x: expected string, got int"]


def test_ref_resolves_against_the_root_and_keeps_the_path():
    schema = {"type": "object", "properties": {"a": {"$ref": "#/$defs/n"}}, **DEFS}
    assert validate_instance(schema, {"a": 1}) == []
    assert validate_instance(schema, {"a": "x"}) == ["$.a: expected integer, got str"]


def test_ref_must_be_a_local_pointer():
    with pytest.raises(ValueError, match=r"unsupported \$ref 'http://x'"):
        validate_instance({"$ref": "http://x"}, 1)
    with pytest.raises(ValueError, match=r"unsupported \$ref 'n'"):
        _resolve("n", {})


def test_const_checks_value_and_bool_kind():
    assert validate_instance({"const": "header"}, "run") == ["$: must be 'header', got 'run'"]
    assert validate_instance({"const": "header"}, "header") == []
    assert validate_instance({"const": 1}, True) == ["$: must be 1, got True"]
    assert validate_instance({"const": True}, 1) == ["$: must be True, got 1"]


def test_enum_lists_the_allowed_values():
    assert validate_instance({"enum": ["a", "b"]}, "c") == ["$: 'c' not in ['a', 'b']"]
    assert validate_instance({"enum": ["a", "b"]}, "b") == []


def test_string_length_and_pattern():
    assert validate_instance({"minLength": 3}, "ab") == ["$: shorter than 3"]
    assert validate_instance({"minLength": 3}, "abc") == []
    assert validate_instance({"pattern": "^a"}, "b") == ["$: does not match ^a"]
    assert validate_instance({"pattern": "^a"}, "ab") == []


def test_minimum_is_inclusive_and_skips_booleans():
    assert validate_instance({"minimum": 1}, 0) == ["$: 0 < minimum 1"]
    assert validate_instance({"minimum": 1}, 0.5) == ["$: 0.5 < minimum 1"]
    assert validate_instance({"minimum": 1}, 1) == []
    assert validate_instance({"minimum": 2}, True) == []


def test_required_fields_are_listed_one_by_one():
    assert validate_instance({"required": ["a", "b"]}, {"a": 1}) == ["$: missing required field 'b'"]


def test_property_errors_carry_the_property_path():
    schema = {"properties": {"a": {"type": "integer"}}}
    assert validate_instance(schema, {"a": "x"}) == ["$.a: expected integer, got str"]
    assert validate_instance(schema, {"a": 1}) == []


def test_extra_fields_are_open_by_default():
    schema = {"properties": {"a": {"type": "integer"}}}
    assert validate_instance(schema, {"a": 1, "b": "x"}) == []
    assert validate_instance({**schema, "additionalProperties": False}, {"a": 1, "b": 2}) == [
        "$: unexpected field 'b'"]


def test_extra_fields_follow_their_schema_and_keep_every_error():
    schema = {"properties": {"a": {"type": "integer"}}, "additionalProperties": {"type": "integer"}}
    assert validate_instance(schema, {"a": 1, "x": "a", "y": "b"}) == [
        "$.x: expected integer, got str", "$.y: expected integer, got str"]


def test_array_length_and_items():
    assert validate_instance({"minItems": 1}, []) == ["$: fewer than 1 items"]
    assert validate_instance({"minItems": 1}, [1]) == []
    assert validate_instance({"items": {"type": "integer"}}, [1, "a"]) == ["$[1]: expected integer, got str"]
    assert validate_instance({"items": {"type": "integer"}}, [1, "a", "b"]) == [
        "$[1]: expected integer, got str", "$[2]: expected integer, got str"]
    assert validate_instance({}, [1, "a"]) == []


def test_items_keep_the_root_for_refs():
    schema = {"type": "array", "items": {"$ref": "#/$defs/n"}, **DEFS}
    assert validate_instance(schema, [1, 2]) == []
    assert validate_instance(schema, [1, "x"]) == ["$[1]: expected integer, got str"]


def test_one_of_picks_the_branch_named_by_kind():
    assert validate_instance(ONE_OF, {"kind": "header", "n": 1}) == []
    assert validate_instance(ONE_OF, {"kind": "run"}) == []
    assert validate_instance(ONE_OF, {"kind": "header", "n": "x"}) == ["$.n: expected integer, got str"]
    assert validate_instance(ONE_OF, {"kind": "other"}) == ["$: kind must be 'header' or 'run', got 'other'"]
    assert validate_instance(ONE_OF, {"n": 1}) == ["$: kind must be 'header' or 'run', got None"]
    assert validate_instance(ONE_OF, 5) == ["$: kind must be 'header' or 'run', got None"]


def test_one_of_accepts_inline_branches_and_branches_without_properties():
    inline = {"oneOf": [{"type": "object", "required": ["x"]},
                        {"type": "object", "properties": {"kind": {"const": "run"}}}]}
    assert validate_instance(inline, {"kind": "run"}) == []
    assert validate_instance(inline, {"kind": "zzz"}) == ["$: kind must be 'header' or 'run', got 'zzz'"]
    mixed = {"oneOf": [{"type": "object", "required": ["x"]}, {"$ref": "#/$defs/run"}], "$defs": ONE_OF["$defs"]}
    assert validate_instance(mixed, {"kind": "zzz"}) == ["$: kind must be 'header' or 'run', got 'zzz'"]


def test_one_of_rejects_two_passing_branches_with_its_path():
    schema = {"oneOf": [{"type": "object"}, {"type": "object", "required": []}]}
    assert validate_instance(schema, {}) == ["$: matches more than one alternative"]
    nested = {"properties": {"a": schema}}
    assert validate_instance(nested, {"a": {}}) == ["$.a: matches more than one alternative"]
    nested_kind = {"properties": {"a": ONE_OF}, "$defs": ONE_OF["$defs"]}
    assert validate_instance(nested_kind, {"a": {"kind": "header", "n": "x"}}) == [
        "$.a.n: expected integer, got str"]
