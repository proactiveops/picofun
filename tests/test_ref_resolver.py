"""Tests for $ref resolver."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import copy

import pytest

from picofun.errors import CircularRefError, RefPathNotFoundError
from picofun.parsers.ref_resolver import resolve_refs


def test_simple_ref() -> None:
    """A dict with $ref is replaced with the target value."""
    spec = {
        "definitions": {
            "Foo": {"type": "object", "properties": {"id": {"type": "integer"}}}
        },
        "result": {"$ref": "#/definitions/Foo"},
    }
    resolved = resolve_refs(spec)
    assert resolved["result"] == {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
    }


def test_nested_chain() -> None:
    """A refs B, B refs C; all resolve correctly."""
    spec = {
        "definitions": {
            "C": {"type": "string"},
            "B": {"$ref": "#/definitions/C"},
            "A": {"$ref": "#/definitions/B"},
        },
        "result": {"$ref": "#/definitions/A"},
    }
    resolved = resolve_refs(spec)
    assert resolved["result"] == {"type": "string"}
    assert resolved["definitions"]["A"] == {"type": "string"}
    assert resolved["definitions"]["B"] == {"type": "string"}


def test_missing_path_raises_error() -> None:
    """A $ref pointing to a nonexistent path raises RefPathNotFoundError."""
    spec = {"result": {"$ref": "#/does/not/exist"}}
    with pytest.raises(RefPathNotFoundError):
        resolve_refs(spec)


def test_circular_ref_raises_error() -> None:
    """A refs B, B refs A raises CircularRefError."""
    spec = {
        "definitions": {
            "A": {"$ref": "#/definitions/B"},
            "B": {"$ref": "#/definitions/A"},
        },
        "result": {"$ref": "#/definitions/A"},
    }
    with pytest.raises(CircularRefError):
        resolve_refs(spec)


def test_non_string_ref_passed_through() -> None:
    """A $ref with a non-string value is left unchanged."""
    spec = {"result": {"$ref": 42, "other": "data"}}
    resolved = resolve_refs(spec)
    assert resolved["result"] == {"$ref": 42, "other": "data"}


def test_non_local_ref_passed_through() -> None:
    """A $ref not starting with '#/' is left unchanged."""
    spec = {"result": {"$ref": "https://example.com/schema.json"}}
    resolved = resolve_refs(spec)
    assert resolved["result"] == {"$ref": "https://example.com/schema.json"}


def test_non_ref_dicts_pass_through() -> None:
    """Dicts without $ref are returned unchanged."""
    spec = {"info": {"title": "My API", "version": "1.0"}}
    resolved = resolve_refs(spec)
    assert resolved == spec


def test_lists_with_refs() -> None:
    """Refs inside list elements are resolved."""
    spec = {
        "definitions": {"Item": {"type": "integer"}},
        "items": [{"$ref": "#/definitions/Item"}, {"type": "string"}],
    }
    resolved = resolve_refs(spec)
    assert resolved["items"] == [{"type": "integer"}, {"type": "string"}]


def test_input_not_mutated() -> None:
    """The original spec_dict is unchanged after calling resolve_refs."""
    spec = {
        "definitions": {"Foo": {"type": "object"}},
        "result": {"$ref": "#/definitions/Foo"},
    }
    original = copy.deepcopy(spec)
    resolve_refs(spec)
    assert spec == original
