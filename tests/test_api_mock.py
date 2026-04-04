"""Mock tests for LLM API calls using unittest.mock."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from chemistry_lab.client import call_with_retry
from chemistry_lab.equipment import generate_equipment, parse_equipment_response
from chemistry_lab.layout import generate_layout


# ---------------------------------------------------------------------------
# Retry logic tests
# ---------------------------------------------------------------------------


class TestCallWithRetry:
    """Tests for the retry wrapper in client.py."""

    def test_success_on_first_try(self):
        client = MagicMock()
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ok"))]
        )
        resp = call_with_retry(client, model="test", messages=[{"role": "user", "content": "hi"}])
        assert resp == "ok"
        assert client.chat.completions.create.call_count == 1

    @patch("chemistry_lab.client.time.sleep")
    def test_success_on_second_try(self, mock_sleep):
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            Exception("transient error"),
            MagicMock(choices=[MagicMock(message=MagicMock(content="ok"))]),
        ]
        resp = call_with_retry(
            client, model="test", messages=[], max_retries=3, base_delay=1.0
        )
        assert resp == "ok"
        assert client.chat.completions.create.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

    @patch("chemistry_lab.client.time.sleep")
    def test_all_retries_exhausted(self, mock_sleep):
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("persistent error")
        with pytest.raises(RuntimeError, match="All 3 retries exhausted"):
            call_with_retry(client, model="test", messages=[], max_retries=3)
        assert client.chat.completions.create.call_count == 3


# ---------------------------------------------------------------------------
# Equipment generation mock test
# ---------------------------------------------------------------------------


class TestGenerateEquipmentMock:
    def test_generate_equipment_uses_client(self):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=(
                        "Category 1 - Large Fixed Equipment:\n"
                        "* **Fume Hood** - For ventilation\n"
                        "Category 2 - Small Equipment:\n"
                        "* **Beaker** - For mixing\n"
                    )
                )
            )
        ]
        client = MagicMock()
        client.chat.completions.create.return_value = mock_response

        large, small = generate_equipment("test experiment", client)
        assert "Fume Hood" in large
        assert "Beaker" in small
        client.chat.completions.create.assert_called_once()


# ---------------------------------------------------------------------------
# Layout generation mock test
# ---------------------------------------------------------------------------


class TestGenerateLayoutMock:
    def test_dry_run_returns_placeholder(self):
        client = MagicMock()
        result = generate_layout(
            "test",
            {"bench": {}},
            {"beaker": {}},
            {"raw": ""},
            client,
            dry_run=True,
        )
        assert result["room"]["width_m"] == 6.0
        assert any(p["item_name"] == "bench" for p in result["placements"])
        client.chat.completions.create.assert_not_called()

    def test_generate_layout_parses_response(self):
        layout_json = json.dumps({
            "room": {"width_m": 6.0, "depth_m": 4.0, "units": "m"},
            "placements": [
                {
                    "item_name": "hood",
                    "category": "large",
                    "x_m": 1.0,
                    "y_m": 1.0,
                    "orientation": "north",
                    "utilities": [],
                    "clearance_m": 0.5,
                    "justification": "wall",
                }
            ],
            "recommendations": "none",
        })
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=layout_json))
        ]
        client = MagicMock()
        client.chat.completions.create.return_value = mock_response

        result = generate_layout(
            "test", {"hood": {}}, {}, {"raw": ""}, client
        )
        assert result["placements"][0]["item_name"] == "hood"
        client.chat.completions.create.assert_called_once()
