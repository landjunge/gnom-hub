"""Tests für SoulAG JSON-Parser-Robustheit.

Schließt den Bug wo LLM-Outputs mit trailing Content ("Extra data: line N")
als Parse-Fehler behandelt wurden und SoulAG scheinbar nicht antwortete.
raw_decode() toleriert nachgestellte prose / Kommentare.
"""
from gnom_hub.soul.soul import _parse_json_value


class TestParseJsonValue:
    """Direkt-Test des Helper-Funktion-Verhaltens."""

    def test_pure_array(self):
        obj, end = _parse_json_value('[{"a": 1}]')
        assert obj == [{"a": 1}]
        # end ist die Position NACH dem letzten JSON-Token (also nach `]`)
        assert end == 10

    def test_array_with_trailing_text(self):
        """LLM gibt JSON + Erklärung zurück. raw_decode ignoriert Rest."""
        text = '[{"a": 1}]\n\nHier ist meine Antwort: ...'
        obj, end = _parse_json_value(text)
        assert obj == [{"a": 1}]
        # end sollte immer noch auf 10 stehen (am `]`), Rest wird ignoriert
        assert end == 10
        assert "Hier ist meine Antwort" in text[end:]

    def test_array_with_leading_text(self):
        """LLM gibt prose + JSON. Wir suchen ab start_pos."""
        text = 'Hier sind die Tasks: [{"task": "x"}]'
        obj, end = _parse_json_value(text, text.find("["))
        assert obj == [{"task": "x"}]

    def test_empty_array(self):
        obj, _ = _parse_json_value('[]')
        assert obj == []

    def test_nested_objects(self):
        text = '[{"a": {"b": [1,2]}}]\nextra prose'
        obj, _ = _parse_json_value(text)
        assert obj == [{"a": {"b": [1, 2]}}]

    def test_no_array_returns_none(self):
        obj, end = _parse_json_value("Kein JSON hier.")
        assert obj is None
        assert end == -1

    def test_empty_string_returns_none(self):
        obj, end = _parse_json_value("")
        assert obj is None
        assert end == -1

    def test_garbage_json_returns_none(self):
        obj, end = _parse_json_value('[broken')
        assert obj is None
        assert end == -1

    def test_object_instead_of_array(self):
        """raw_decode ist agnostisch — funktioniert auch mit Objekten."""
        text = '{"key": "value"}'
        obj, _ = _parse_json_value(text)
        assert obj == {"key": "value"}

    def test_whitespace_before_json(self):
        text = '   \n  [{"x": 1}]'
        obj, _ = _parse_json_value(text, text.find("["))
        assert obj == [{"x": 1}]

    def test_realistic_llm_response(self):
        """Simuliert eine echte LLM-Antwort mit Markdown-Wrapping."""
        text = (
            "Hier sind die extrahierten Tasks:\n"
            "```json\n"
            '[{"task": "Fix Bug", "agent": "CoderAG"}]\n'
            "```\n"
            "Hoffe das hilft! Bei Fragen melden."
        )
        obj, _ = _parse_json_value(text, text.find("["))
        assert obj == [{"task": "Fix Bug", "agent": "CoderAG"}]