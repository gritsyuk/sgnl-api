import re
from typing import Dict, List, Any, TypeVar, Optional
from functools import lru_cache

T = TypeVar('T', Dict, List, Any)


@lru_cache(maxsize=128)
def camel_to_snake(string: str) -> str:
    """
    Конвертирует строку из camelCase в snake_case.
    Args:
        string: Строка в формате camelCase
    Returns:
        Строка в формате snake_case
    Examples:
        >>> camel_to_snake("camelCase")
        'camel_case'
        >>> camel_to_snake("HTTPResponse")
        'http_response'
    """
    string = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', string)
    string = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', string)
    return string.lower()


def keys_to_snake_case(data: T, max_depth: Optional[int] = None, _current_depth: int = 0) -> T:
    if max_depth is not None and _current_depth > max_depth:
        raise ValueError(f"Maximum depth exceeded: {max_depth}")

    if isinstance(data, dict):
        return {
            camel_to_snake(str(key)): keys_to_snake_case(value, max_depth, _current_depth + 1)
            if isinstance(value, (dict, list))
            else value
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [
            keys_to_snake_case(item, max_depth, _current_depth + 1)
            if isinstance(item, (dict, list))
            else item
            for item in data
        ]
    return data
