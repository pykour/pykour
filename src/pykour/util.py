import ast
import json
from typing import Any
from enum import Enum
from datetime import datetime

from pykour.logging import write_error_log


def cast(value: Any, to_type: type) -> Any:
    try:
        if to_type == int:
            return int(value)
        if to_type == float:
            return float(value)
        if to_type == bool:
            return value.lower() in ["true", "1", "yes"]
        if to_type == datetime:
            return datetime.strptime(value, "%Y-%m-%d")
        if issubclass(to_type, Enum):
            try:
                return to_type[value]
            except KeyError:
                raise ValueError(f"{value} is not a valid {to_type.__name__}")
        return value
    except Exception as e:
        write_error_log(f"Error casting value '{value}' to type '{to_type}': {e}")
        raise e


def convert_to_json_string(input_str):
    try:
        python_obj = ast.literal_eval(input_str)

        json_str = json.dumps(python_obj)
        return json_str
    except (ValueError, SyntaxError) as e:
        raise e
