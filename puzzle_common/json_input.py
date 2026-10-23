"""Consistent JSON decoding failures at both puzzle input boundaries."""

import json


def decode_json(text: str, error_type: type[Exception], source: str = "JSON") -> object:
    if not isinstance(text, str):
        raise TypeError(f"{source} 입력은 문자열이어야 합니다.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise error_type(
            f"{source}이 올바른 JSON이 아닙니다: {error.msg} "
            f"(줄 {error.lineno}, 열 {error.colno})"
        ) from error
    except (RecursionError, ValueError) as error:
        raise error_type(
            f"{source}이 너무 복잡하거나 지원하지 않는 값이 있습니다."
        ) from error
