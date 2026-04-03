"""Tests for chemistry_lab.parser."""

import json

from chemistry_lab.parser import extract_json_from_text, parse_json


class TestExtractJsonFromText:
    def test_simple_object(self):
        text = 'Here is some text {"key": "value"} and more.'
        assert extract_json_from_text(text) == '{"key": "value"}'

    def test_nested_object(self):
        obj = {"a": {"b": [1, 2, 3]}}
        text = f"prefix {json.dumps(obj)} suffix"
        assert json.loads(extract_json_from_text(text)) == obj

    def test_array(self):
        text = "result: [1, 2, 3]"
        assert extract_json_from_text(text) == "[1, 2, 3]"

    def test_no_json(self):
        assert extract_json_from_text("no json here") is None

    def test_json_with_noise(self):
        text = '```json\n{"room": {"width": 6}}\n```'
        result = extract_json_from_text(text)
        assert result is not None
        assert json.loads(result) == {"room": {"width": 6}}


class TestParseJson:
    def test_valid(self):
        assert parse_json('{"x": 1}') == {"x": 1}

    def test_invalid_json_str(self):
        assert parse_json("nothing to see") is None

    def test_array(self):
        assert parse_json("[1, 2]") == [1, 2]
