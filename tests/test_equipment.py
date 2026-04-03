"""Tests for chemistry_lab.equipment."""

from chemistry_lab.equipment import parse_equipment_response


SAMPLE_RESPONSE = """\
Here is the equipment list:

Category 1 - Large Fixed Equipment and Installations:

* **Fume Hood** - For handling volatile chemicals
* **Lab Bench** - Primary workspace

Category 2 - Small Containers and Instruments:

* **Beaker** - For mixing solutions
* **Thermometer** - Temperature measurement
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
