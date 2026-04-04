"""LLM client initialization with dependency injection and retry support."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from chemistry_lab.config import DEFAULT_BASE_URL

logger = logging.getLogger(__name__)


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


def call_with_retry(
    client: Any,
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2000,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> str:
    """Call the chat completions endpoint with exponential-backoff retry.

    Args:
        client: An ``OpenAI``-compatible client.
        model: Model identifier.
        messages: Chat messages.
        temperature: Sampling temperature.
        max_tokens: Maximum response tokens.
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds (doubles each retry).

    Returns:
        The assistant's response text.

    Raises:
        RuntimeError: If all retries are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            return response.choices[0].message.content
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "API call failed (attempt %d/%d): %s – retrying in %.1fs",
                    attempt,
                    max_retries,
                    exc,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "API call failed after %d attempts: %s", max_retries, exc
                )
    raise RuntimeError(f"All {max_retries} retries exhausted: {last_exc}") from last_exc
