"""Request parsing utilities."""

from typing import Any
from urllib.parse import parse_qs

import orjson

from pykour import json as pykour_json
from pykour.schema.errors import ErrorDetail, ValidationError
from pykour.schema.fields import FieldInfo
from pykour.schema.types import coerce_value


def parse_query_string(query_string: bytes) -> dict[str, Any]:
    """Parse query string bytes to dictionary."""
    if not query_string:
        return {}

    try:
        decoded = query_string.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValidationError(
            [
                ErrorDetail(
                    loc=("query",),
                    msg=f"Invalid UTF-8 encoding: {e.reason}",
                    type="value_error.encoding",
                )
            ]
        ) from e
    parsed = parse_qs(decoded, keep_blank_values=True)

    # Convert single-value lists to single values
    result: dict[str, Any] = {}
    for key, values in parsed.items():
        if len(values) == 1:
            result[key] = values[0]
        else:
            result[key] = values

    return result


def parse_json_body(body: bytes) -> dict[str, Any]:
    """Parse JSON body bytes to dictionary."""
    if not body:
        return {}

    try:
        data = pykour_json.loads(body)
        if not isinstance(data, dict):
            raise ValidationError(
                [
                    ErrorDetail(
                        loc=("body",),
                        msg="Request body must be a JSON object",
                        type="type_error.dict",
                    )
                ]
            )
        return data
    except orjson.JSONDecodeError as e:
        raise ValidationError(
            [
                ErrorDetail(
                    loc=("body",),
                    msg=f"Invalid JSON: {e}",
                    type="value_error.json_decode",
                )
            ]
        ) from e


def coerce_path_param(
    value: str,
    param_name: str,
    target_type: type,
) -> Any:
    """Coerce a path parameter to target type."""
    try:
        return coerce_value(value, target_type)
    except (TypeError, ValueError) as e:
        raise ValidationError(
            [
                ErrorDetail(
                    loc=("path", param_name),
                    msg=str(e),
                    type="type_error",
                    input=value,
                )
            ]
        ) from e


def coerce_query_param(
    value: Any,
    param_name: str,
    target_type: type,
    field_info: FieldInfo,
) -> Any:
    """Coerce a query parameter to target type with validation."""
    try:
        coerced = coerce_value(value, target_type)
    except (TypeError, ValueError) as e:
        raise ValidationError(
            [
                ErrorDetail(
                    loc=("query", param_name),
                    msg=str(e),
                    type="type_error",
                    input=value,
                )
            ]
        ) from e

    # Apply constraints
    errors: list[ErrorDetail] = []
    for constraint in field_info.get_constraints():
        try:
            constraint.validate(coerced, param_name)
        except ValueError as e:
            errors.append(
                ErrorDetail(
                    loc=("query", param_name),
                    msg=str(e),
                    type=f"value_error.{constraint.__class__.__name__.lower()}",
                    input=value,
                )
            )

    if errors:
        raise ValidationError(errors)

    return coerced
