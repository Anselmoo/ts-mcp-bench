"""Validation of JSON instances against the small JSON-Schema subset the plan and answer schemas use (no dependency)."""
from __future__ import annotations

import re

__all__ = ["validate_instance"]


def _type_matches(inst, t: str) -> bool:
    if t == "null":
        return inst is None
    if t == "boolean":
        return isinstance(inst, bool)
    if t == "integer":
        return isinstance(inst, int) and not isinstance(inst, bool)
    if t == "number":
        return isinstance(inst, (int, float)) and not isinstance(inst, bool)
    return isinstance(inst, {"string": str, "object": dict, "array": list}[t])


def _resolve(ref: str, root: dict) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported $ref {ref!r}")  # core sits below plan, so no PlanError here
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def validate_instance(schema: dict, inst, root: dict | None = None, path: str = "$") -> list[str]:
    """Errors (empty = valid). Supports: $ref, type, enum, const, required, properties, additionalProperties,
    items, minItems, minLength, minimum, pattern, oneOf. Anything else in a schema is ignored."""
    root = root if root is not None else schema
    if "$ref" in schema:
        return validate_instance(_resolve(schema["$ref"], root), inst, root, path)
    errs: list[str] = []
    if "oneOf" in schema:
        branches = [validate_instance(b, inst, root, path) for b in schema["oneOf"]]
        passing = [b for b in branches if not b]
        if len(passing) == 1:
            return []
        if passing:
            return [f"{path}: matches more than one alternative"]
        kind = inst.get("kind") if isinstance(inst, dict) else None
        for b, errs_b in zip(schema["oneOf"], branches, strict=False):
            target = _resolve(b["$ref"], root) if "$ref" in b else b
            if target.get("properties", {}).get("kind", {}).get("const") == kind:
                return errs_b
        return [f"{path}: kind must be 'header' or 'run', got {kind!r}"]
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_matches(inst, t) for t in types):
            return [f"{path}: expected {'|'.join(types)}, got {type(inst).__name__}"]
    if "const" in schema and (inst != schema["const"] or isinstance(inst, bool) != isinstance(schema["const"], bool)):
        errs.append(f"{path}: must be {schema['const']!r}, got {inst!r}")
    if "enum" in schema and inst not in schema["enum"]:
        errs.append(f"{path}: {inst!r} not in {schema['enum']!r}")
    if isinstance(inst, str):
        if len(inst) < schema.get("minLength", 0):
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errs.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(inst, (int, float)) and not isinstance(inst, bool) and "minimum" in schema \
            and inst < schema["minimum"]:
        errs.append(f"{path}: {inst} < minimum {schema['minimum']}")
    if isinstance(inst, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in inst:
                errs.append(f"{path}: missing required field {key!r}")
        extra = schema.get("additionalProperties", True)
        for key, val in inst.items():
            if key in props:
                errs += validate_instance(props[key], val, root, f"{path}.{key}")
            elif extra is False:
                errs.append(f"{path}: unexpected field {key!r}")
            elif isinstance(extra, dict):
                errs += validate_instance(extra, val, root, f"{path}.{key}")
    if isinstance(inst, list):
        if len(inst) < schema.get("minItems", 0):
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(inst):
                errs += validate_instance(schema["items"], item, root, f"{path}[{i}]")
    return errs
