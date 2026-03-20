"""JSON $ref resolver for API specification dicts."""

__author__ = "Dave Hall <skwashd@gmail.com>"
__copyright__ = "Copyright 2026, Dave Hall https://proactiveops.io"
__license__ = "MIT"

import copy
from typing import cast

from picofun.errors import CircularRefError, RefPathNotFoundError

type JsonValue = (
    str | int | float | bool | None | dict[str, JsonValue] | list[JsonValue]
)


def resolve_refs(spec_dict: dict) -> dict:
    """
    Recursively resolve all $ref pointers in a spec dict.

    Replaces {"$ref": "#/path/to/thing"} with the resolved value
    from within the same document. Tracks visited paths for circular
    reference detection.

    Args:
        spec_dict: The full specification dictionary.

    Returns:
        A new dict with all $ref pointers resolved.

    Raises:
        RefPathNotFoundError: If a $ref path cannot be resolved.
        CircularRefError: If a circular $ref is detected.

    """
    result = copy.deepcopy(spec_dict)
    return cast(dict, _resolve(result, spec_dict, set()))


def _lookup(spec_dict: dict, ref_path: str) -> JsonValue:
    """Walk into spec_dict following a $ref path like '#/components/schemas/Pet'."""
    parts = ref_path.lstrip("#").strip("/").split("/")
    current = spec_dict
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            raise RefPathNotFoundError(ref_path)
        current = current[part]
    return current


def _resolve(node: JsonValue, root: dict, visited: set) -> JsonValue:
    """Recursively resolve $ref pointers in node."""
    if isinstance(node, dict):
        if "$ref" in node:
            ref_path = node["$ref"]
            if not isinstance(ref_path, str) or not ref_path.startswith("#/"):
                return node
            if ref_path in visited:
                raise CircularRefError(ref_path)
            visited = visited | {ref_path}
            target = _lookup(root, ref_path)
            return _resolve(copy.deepcopy(target), root, visited)
        return {key: _resolve(value, root, visited) for key, value in node.items()}
    if isinstance(node, list):
        return [_resolve(item, root, visited) for item in node]
    return node
