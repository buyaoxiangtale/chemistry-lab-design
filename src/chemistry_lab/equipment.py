"""Equipment list generation and parsing."""

from __future__ import annotations

import re
from typing import Dict, Tuple

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI

from chemistry_lab.config import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, DEFAULT_TEMPERATURE


# ---- response parsing -------------------------------------------------------

def parse_equipment_response(response_text: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Parse an LLM response into *(large_equipment, small_equipment)* dicts.

    The parser is deliberately tolerant: it handles markdown bold headings,
    bullet lists, and a variety of category-header phrasings in both English
    and Chinese.

    Args:
        response_text: Raw text returned by the LLM.

    Returns:
        A tuple ``(large_equipment, small_equipment)`` where each value maps
        an equipment name to its description string.
    """
    large_equipment: Dict[str, str] = {}
    small_equipment: Dict[str, str] = {}

    current_category: str | None = None
    current_item: str | None = None
    current_description: list[str] = []
    saw_category = False

    lines = [l.rstrip() for l in response_text.split("\n")]
    for raw in lines:
        line = raw.strip()
        if not line or set(line).issubset({"-", "=", "#", " "}):
            continue

        low = line.lower()

        # Detect category headers
        if any(
            h in low
            for h in [
                "category 1",
                "large fixed equipment",
                "large equipment and installations",
                "category one",
            ]
        ):
            current_category = "large"
            saw_category = True
            current_item = None
            current_description = []
            continue
        if any(
            h in low
            for h in [
                "category 2",
                "small containers",
                "small equipment and instruments",
                "category two",
            ]
        ):
            current_category = "small"
            saw_category = True
            current_item = None
            current_description = []
            continue

        # Detect item headings
        m_bold = re.search(r"\*\*\s*(?P<name>[^*]+?)\s*\*\*", line)
        m_bullet_inline = re.match(
            r"^[*\-\u2022\d. ]+\s*(?P<name>[^:：\-–—]+?)\s*[:：\-–—]\s*(?P<desc>.+)$",
            line,
        )
        m_bullet_name_only = re.match(r"^[*\-\u2022\d. ]+\s*(?P<name>.+?)$", line)

        def _save_current() -> None:
            nonlocal current_item, current_description
            if current_item and current_description:
                desc = " ".join(current_description).strip()
                target = (
                    large_equipment
                    if current_category == "large"
                    else small_equipment
                )
                target[current_item] = desc

        if m_bold:
            _save_current()
            current_item = m_bold.group("name").strip()
            post = line.split(m_bold.group(0), 1)[1].strip() if m_bold.group(0) in line else ""
            if post.startswith("-") or post.startswith(":"):
                post = post.lstrip("-:： ").strip()
            current_description = [post] if post else []
            continue

        if m_bullet_inline:
            _save_current()
            current_item = m_bullet_inline.group("name").strip()
            current_description = [m_bullet_inline.group("desc").strip()]
            continue

        if m_bullet_name_only and (
            line.startswith("*") or line.startswith("-") or line[0].isdigit()
        ):
            _save_current()
            current_item = m_bullet_name_only.group("name").strip()
            current_description = []
            continue

        # Continuation line
        if current_item:
            cleaned = line.replace("*", "").strip()
            if cleaned:
                current_description.append(cleaned)

    # Save the last item
    if current_item and current_description:
        desc = " ".join(current_description).strip()
        target = large_equipment if current_category == "large" else small_equipment
        target[current_item] = desc

    # Fallback: extract bold names
    if not large_equipment and not small_equipment:
        bolds = re.findall(r"\*\*\s*([^*]+?)\s*\*\*", response_text)
        if bolds:
            parts = re.split(r"\*\*\s*([^*]+?)\s*\*\*", response_text)
            it = iter(parts)
            _ = next(it)
            for name, post in zip(it, it):
                nm = name.strip()
                desc = " ".join(
                    d.strip() for d in post.strip().split("\n")[:3] if d.strip()
                )
                lname = nm.lower()
                if any(k in lname for k in ["bench", "hood", "fume", "cabinet", "台", "柜"]):
                    large_equipment[nm] = desc
                else:
                    small_equipment[nm] = desc

    return large_equipment, small_equipment


# ---- equipment generation via LLM -------------------------------------------

_SYSTEM_MESSAGE = """\
You are an expert chemistry laboratory equipment specialist. Your primary role \
is to provide detailed categorized information about laboratory equipment and \
setups for specific chemistry experiments. When responding:

1. Always categorize equipment into two main categories:
   Category 1: Large Fixed Equipment and Installations
   - Lab benches, fume hoods, sinks
   - Storage cabinets, safety showers
   - Fixed electrical, water, or gas connections
   - Any equipment that requires permanent installation

   Category 2: Small Containers and Instruments
   - Glassware (beakers, flasks, test tubes)
   - Measuring instruments (thermometers, scales)
   - Heating/cooling equipment (hot plates, ice baths)
   - Safety equipment (goggles, gloves)
   - Tools and accessories (spatulas, tongs)

2. For each piece of equipment listed:
   - Start with "* **Equipment Name**"
   - Describe its specific purpose in the experiment
   - Mention required specifications or sizes
   - Note any safety considerations

3. Always include basic safety equipment:
   - Personal protective equipment
   - Emergency equipment
   - Waste disposal containers

Format each equipment entry as:
* **Equipment Name** - Brief description of purpose, specifications, and safety considerations\
"""


def _build_user_message(experiment_name: str) -> str:
    return (
        f"Provide a complete list of laboratory equipment needed for the "
        f"{experiment_name} experiment.\n\n"
        "Categorize ALL equipment into:\n\n"
        "1. Category 1 - Large Fixed Equipment and Installations:\n"
        "   - Laboratory infrastructure (benches, hoods, sinks)\n"
        "   - Fixed storage units and safety equipment\n"
        "   - Permanently installed utilities\n"
        "   - Support structures and mounting points\n\n"
        "2. Category 2 - Small Containers and Instruments:\n"
        "   - All glassware and containers\n"
        "   - Measuring and handling tools\n"
        "   - Portable heating/cooling equipment\n"
        "   - Safety equipment and PPE\n"
        "   - Small tools and accessories\n\n"
        "List each piece of equipment with:\n"
        "* **Equipment Name** - Purpose, specifications, and safety considerations"
    )


def generate_equipment(
    experiment_name: str,
    client: OpenAI,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Generate a categorised equipment list for *experiment_name*.

    Args:
        experiment_name: Name of the experiment.
        client: An ``OpenAI``-compatible client.
        model: Model identifier.
        temperature: Sampling temperature.
        max_tokens: Maximum response tokens.

    Returns:
        ``(large_equipment, small_equipment)`` dicts.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_MESSAGE},
                {"role": "user", "content": _build_user_message(experiment_name)},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return parse_equipment_response(response.choices[0].message.content)
    except Exception as exc:
        raise RuntimeError(f"Failed to generate equipment list: {exc}") from exc
