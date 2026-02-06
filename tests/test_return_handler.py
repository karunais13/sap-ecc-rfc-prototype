"""Tests for BAPI return handler."""

from sap_mcp.bapi.return_handler import parse_return


class TestParseReturn:

    def test_none_returns_success(self):
        result = parse_return(None)
        assert result.success is True
        assert result.errors == []

    def test_single_success(self):
        ret = {"TYPE": "S", "ID": "MOCK", "NUMBER": "000", "MESSAGE": "All good"}
        result = parse_return(ret)
        assert result.success is True
        assert result.summary == "All good"

    def test_single_error(self):
        ret = {"TYPE": "E", "ID": "MOCK", "NUMBER": "001", "MESSAGE": "Not found"}
        result = parse_return(ret)
        assert result.success is False
        assert result.errors == ["Not found"]
        assert result.summary == "Not found"

    def test_abort_is_error(self):
        ret = {"TYPE": "A", "ID": "SY", "NUMBER": "999", "MESSAGE": "System abort"}
        result = parse_return(ret)
        assert result.success is False
        assert "System abort" in result.errors

    def test_table_with_mixed_types(self):
        table = [
            {"TYPE": "S", "ID": "MOCK", "NUMBER": "000", "MESSAGE": "OK"},
            {"TYPE": "W", "ID": "MOCK", "NUMBER": "010", "MESSAGE": "Beware"},
            {"TYPE": "I", "ID": "MOCK", "NUMBER": "020", "MESSAGE": "FYI"},
        ]
        result = parse_return(table)
        assert result.success is True
        assert result.warnings == ["Beware"]
        assert result.info == ["FYI"]
        assert result.summary == "Beware"

    def test_table_with_error(self):
        table = [
            {"TYPE": "S", "ID": "MOCK", "NUMBER": "000", "MESSAGE": "Partial"},
            {"TYPE": "E", "ID": "MOCK", "NUMBER": "001", "MESSAGE": "Bad input"},
        ]
        result = parse_return(table)
        assert result.success is False
        assert result.errors == ["Bad input"]

    def test_empty_dict(self):
        result = parse_return({})
        assert result.success is True

    def test_empty_list(self):
        result = parse_return([])
        assert result.success is True

    def test_error_without_message_uses_id_number(self):
        ret = {"TYPE": "E", "ID": "ZZ", "NUMBER": "042", "MESSAGE": ""}
        result = parse_return(ret)
        assert result.success is False
        assert result.errors == ["ZZ-042"]
