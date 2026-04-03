"""LLM client initialization with dependency injection."""

from __future__ import annotations

import os
from typing import Any

from chemistry_lab.config import DEFAULT_BASE_URL


def create_client(api_key: str | None = None, base_url: str | None = None) -> Any:
    """Create an OpenAI-compatible LLM client.

    Args:
        api_key: API key for the LLM service. Falls back to the
            ``CHEM_LAB_API_KEY`` environment variable.
        base_url: Base URL of the API endpoint. Falls back to the
            ``CHEM_LAB_BASE_URL`` environment variable, or the default
            DeepSeek endpoint.

    Returns:
        Configured ``OpenAI`` client instance.
    """
    from openai import OpenAI

    resolved_key = api_key or os.environ.get("CHEM_LAB_API_KEY", "")
    resolved_url = base_url or os.environ.get("CHEM_LAB_BASE_URL", DEFAULT_BASE_URL)
    return OpenAI(api_key=resolved_key, base_url=resolved_url)
