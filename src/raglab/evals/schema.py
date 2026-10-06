"""A small JSON Schema validator for the subset the run record schema uses.

Supported keywords: type (one or a list), properties, required, additionalProperties (true, false
or a schema), items, enum, const, pattern, minimum, maximum, minLength, minItems, $ref (to
"#/$defs/<name>") and $defs, plus the annotations $schema, $id, $comment, title and description.
A schema that uses any other keyword is refused (SchemaError), so a keyword this validator would
silently ignore can never weaken the check. As in JSON Schema, a boolean is not a number or an
integer, and an integer-valued float is an integer.
"""

import re
from typing import cast

type Json = object
type Schema = dict[str, object]

KEYWORDS = frozenset(
    {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "const",
        "pattern",
        "minimum",
        "maximum",
        "minLength",
        "minItems",
        "$ref",
        "$defs",
        "$schema",
        "$id",
        "$comment",
        "title",
        "description",
    }
)
TYPES = frozenset({"object", "array", "string", "number", "integer", "boolean", "null"})


class SchemaError(ValueError):
    """The schema itself uses something this validator does not support."""


def _is_type(value: Json, name: str) -> bool:
    match name:
        case "object":
            return isinstance(value, dict)
        case "array":
            return isinstance(value, list)
        case "string":
            return isinstance(value, str)
        case "boolean":
            return isinstance(value, bool)
        case "null":
            return value is None
        case "integer":
            return (isinstance(value, int) and not isinstance(value, bool)) or (
                isinstance(value, float) and value.is_integer()
            )
        case "number":
            return isinstance(value, int | float) and not isinstance(value, bool)
        case _:
            raise SchemaError(f"unknown type {name!r}")


def _as_schema(value: object, where: str) -> Schema:
    if not isinstance(value, dict):
        raise SchemaError(f"{where}: a schema is an object")
    return {str(k): v for k, v in cast(dict[object, object], value).items()}


def check_schema(schema: Schema, where: str = "#") -> None:
    """Refuse a schema that uses a keyword or a type outside the supported subset."""
    unknown = set(schema) - KEYWORDS
    if unknown:
        raise SchemaError(f"{where}: unsupported keywords {sorted(unknown)}")
    types = schema.get("type")
    names: list[object] = (
        cast(list[object], types) if isinstance(types, list) else [] if types is None else [types]
    )
    for name in names:
        if name not in TYPES:
            raise SchemaError(f"{where}: unknown type {name!r}")
    for key in ("properties", "$defs"):
        if key in schema:
            for name, sub in _as_schema(schema[key], f"{where}/{key}").items():
                check_schema(_as_schema(sub, f"{where}/{key}/{name}"), f"{where}/{key}/{name}")
    for key in ("items", "additionalProperties"):
        sub: object = schema.get(key)
        if isinstance(sub, dict):
            check_schema(_as_schema(cast(object, sub), f"{where}/{key}"), f"{where}/{key}")


class Validator:
    def __init__(self, schema: Schema) -> None:
        check_schema(schema)
        self.root = schema

    def _resolve(self, ref: str) -> Schema:
        prefix = "#/$defs/"
        if not ref.startswith(prefix):
            raise SchemaError(f"only #/$defs/<name> references are supported, not {ref!r}")
        defs = _as_schema(self.root.get("$defs", {}), "$defs")
        name = ref[len(prefix) :]
        if name not in defs:
            raise SchemaError(f"no definition {name!r}")
        return _as_schema(defs[name], ref)

    def errors(self, value: Json, schema: Schema | None = None, path: str = "$") -> list[str]:
        """Every way value breaks the schema, each with its JSON path."""
        schema = self.root if schema is None else schema
        if "$ref" in schema:
            return self.errors(value, self._resolve(str(schema["$ref"])), path)
        found: list[str] = []
        types = schema.get("type")
        if types is not None:
            names = (
                [str(t) for t in cast(list[object], types)]
                if isinstance(types, list)
                else [str(types)]
            )
            if not any(_is_type(value, name) for name in names):
                return [f"{path}: expected {' or '.join(names)}, got {type(value).__name__}"]
        if "const" in schema and value != schema["const"]:
            found.append(f"{path}: must be {schema['const']!r}")
        if "enum" in schema and value not in cast(list[object], schema["enum"]):
            found.append(f"{path}: {value!r} is not one of {schema['enum']}")
        if isinstance(value, str):
            pattern = schema.get("pattern")
            if isinstance(pattern, str) and not re.search(pattern, value):
                found.append(f"{path}: {value!r} does not match {pattern}")
            min_length = schema.get("minLength")
            if isinstance(min_length, int) and len(value) < min_length:
                found.append(f"{path}: shorter than {min_length}")
        if isinstance(value, int | float) and not isinstance(value, bool):
            low, high = schema.get("minimum"), schema.get("maximum")
            if isinstance(low, int | float) and value < low:
                found.append(f"{path}: {value} is below the minimum {low}")
            if isinstance(high, int | float) and value > high:
                found.append(f"{path}: {value} is above the maximum {high}")
        if isinstance(value, list):
            items = cast(list[object], value)
            min_items = schema.get("minItems")
            if isinstance(min_items, int) and len(items) < min_items:
                found.append(f"{path}: fewer than {min_items} items")
            if "items" in schema:
                sub = _as_schema(schema["items"], f"{path}/items")
                for i, item in enumerate(items):
                    found.extend(self.errors(item, sub, f"{path}[{i}]"))
        if isinstance(value, dict):
            obj = {str(k): v for k, v in cast(dict[object, object], value).items()}
            for name in cast(list[object], schema.get("required", [])):
                if name not in obj:
                    found.append(f"{path}: missing {name!r}")
            properties = _as_schema(schema.get("properties", {}), f"{path}/properties")
            extra: object = schema.get("additionalProperties", True)
            for name, item in obj.items():
                if name in properties:
                    found.extend(
                        self.errors(item, _as_schema(properties[name], name), f"{path}.{name}")
                    )
                elif extra is False:
                    found.append(f"{path}: unexpected property {name!r}")
                elif isinstance(extra, dict):
                    sub = _as_schema(cast(object, extra), name)
                    found.extend(self.errors(item, sub, f"{path}.{name}"))
        return found
