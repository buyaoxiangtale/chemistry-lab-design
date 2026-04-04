"""Utilities for extracting and parsing JSON from LLM responses."""

from __future__ import annotations

import json
import re


def extract_json_from_text(text: str) -> str | None:
    """Extract the first complete JSON object or array from *text*.

    First attempts ``json.JSONDecoder.raw_decode()`` for standards-compliant
    extraction.  Falls back to a bracket-matching heuristic when raw_decode
    cannot locate a JSON value.

    Args:
        text: Raw text potentially containing JSON.

    Returns:
        The extracted JSON string, or ``None`` if nothing was found.
    """
    # --- Fast path: raw_decode -------------------------------------------
    decoder = json.JSONDecoder()
    # Strip markdown fences that LLMs commonly wrap JSON in.
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"\s*```", "", cleaned)

    for match in re.finditer(r"[{\[]", cleaned):
        pos = match.start()
        try:
            obj, end = decoder.raw_decode(cleaned, idx=pos)
            return cleaned[pos:end]
        except json.JSONDecodeError:
            continue

    # --- Fallback: bracket-matching heuristic ----------------------------
    starts = [(m.start(), m.group()) for m in re.finditer(r"[{\[]", text)]
    if not starts:
        return None
    for pos, _ch in starts:
        stack: list[str] = []
        end: int | None = None
        in_string = False
        escape = False
        for i in range(pos, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"' and not in_string:
                in_string = True
                continue
            if c == '"' and in_string:
                in_string = False
                continue
            if in_string:
                continue
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
