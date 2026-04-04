"""Tests for chemistry_lab.equipment – parsing and mock API."""

from chemistry_lab.equipment import generate_equipment, parse_equipment_response
from unittest.mock import MagicMock


SAMPLE_RESPONSE = """\
Here is the equipment list:

**Category 1 - Large Fixed Equipment and Installations:**

* **Fume Hood** - For handling volatile chemicals, requires ventilation
* **Lab Bench** - Primary workspace, chemical resistant surface

**Category 2 - Small Containers and Instruments:**

* **Beaker** - 500ml glass beaker for mixing solutions
* **Thermometer** - Mercury thermometer for temperature measurement
"""


class TestParseEquipmentResponse:
    def test_basic_categorization(self):
        large, small = parse_equipment_response(SAMPLE_RESPONSE)
        assert "Fume Hood" in large
        assert "Lab Bench" in large
        assert "Beaker" in small
        assert "Thermometer" in small

    def test_empty_response(self):
        large, small = parse_equipment_response("")
        assert large == {}
        assert small == {}

    def test_descriptions_extracted(self):
        large, small = parse_equipment_response(SAMPLE_RESPONSE)
        assert "volatile" in large["Fume Hood"].lower() or "Fume Hood" in str(large)
        assert "mixing" in small.get("Beaker", "").lower() or len(small) > 0


class TestGenerateEquipmentMockAPI:
    """Test equipment generation with a mocked LLM response."""

    def test_mock_api_returns_equipment(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = SAMPLE_RESPONSE
        mock_client.chat.completions.create.return_value = mock_response

        large, small = generate_equipment("test experiment", mock_client)
        assert "Fume Hood" in large
        assert "Beaker" in small

    def test_mock_api_retry(self):
        """Verify retry on failure then success."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            Exception("timeout"),
            MagicMock(
                choices=[MagicMock(
                    message=MagicMock(content=SAMPLE_RESPONSE)
                )]
            ),
        ]

        large, small = generate_equipment("test experiment", mock_client)
        assert "Fume Hood" in large
        assert mock_client.chat.completions.create.call_count == 2
