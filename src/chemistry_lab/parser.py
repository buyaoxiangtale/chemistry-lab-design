"""Utilities for extracting and parsing JSON from LLM responses."""

import json
import re


def extract_json_from_text(text: str) -> str | None:
    """Extract the first complete JSON object or array from *text*.

    Uses a simple bracket-matching approach to find balanced ``{}`` or ``[]``
    blocks.

    Args:
        text: Raw text potentially containing JSON.

    Returns:
        The extracted JSON string, or ``None`` if nothing was found.
    """
    starts = [(m.start(), m.group()) for m in re.finditer(r"[{\[]", text)]
    if not starts:
        return None
    for pos, _ch in starts:
        stack: list[str] = []
        end: int | None = None
        for i in range(pos, len(text)):
            c = text[i]
            if c in ("{", "["):
                stack.append(c)
            elif c in ("}", "]"):
                if not stack:
                    break
                opening = stack.pop()
                if (opening == "{" and c != "}") or (opening == "[" and c != "]"):
                    break
                if not stack:
                    end = i
                    break
        if end is not None:
            return text[pos : end + 1]
    return None


def parse_json(text: str) -> dict | list | None:
    """Extract and parse JSON from *text*, returning a Python object.

    Args:
        text: Raw text potentially containing JSON.

    Returns:
        Parsed JSON (dict or list), or ``None`` on failure.
    """
    json_str = extract_json_from_text(text)
    if json_str is None:
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None
