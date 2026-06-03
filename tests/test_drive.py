from unittest.mock import MagicMock
import pytest
from gdrive_mcp.tools.drive import get_parents, drive_list, is_valid_drive_id, validate_drive_id

def _drive_with_get(result):
    drive = MagicMock()
    drive.files.return_value.get.return_value.execute.return_value = result
    return drive

def test_get_parents_returns_parent_list():
    drive = _drive_with_get({"parents": ["P1", "P2"]})
    assert get_parents(drive, "f1") == ["P1", "P2"]
    drive.files.return_value.get.assert_called_once()
    kwargs = drive.files.return_value.get.call_args.kwargs
    assert kwargs["fileId"] == "f1"
    assert kwargs["fields"] == "parents"
    assert kwargs["supportsAllDrives"] is True

def test_get_parents_missing_key_returns_empty():
    drive = _drive_with_get({})
    assert get_parents(drive, "root") == []

def test_drive_list_maps_files_and_scopes_query():
    drive = MagicMock()
    drive.files.return_value.list.return_value.execute.return_value = {
        "files": [{"id": "1", "name": "a", "mimeType": "m", "modifiedTime": "t"}]
    }
    out = drive_list(drive, folder_id="M", query="budget")
    assert out == [{"id": "1", "name": "a", "mimeType": "m", "modifiedTime": "t"}]
    kwargs = drive.files.return_value.list.call_args.kwargs
    assert "'M' in parents" in kwargs["q"]
    assert "name contains 'budget'" in kwargs["q"]
    assert kwargs["supportsAllDrives"] is True
    assert kwargs["includeItemsFromAllDrives"] is True


# FIX 1 tests — injection escape and drive-ID guard

def test_query_backslash_quote_payload_is_double_escaped():
    """A backslash+quote payload must have both chars escaped; no raw injection survives."""
    import re as _re
    drive = MagicMock()
    drive.files.return_value.list.return_value.execute.return_value = {"files": []}
    # Craft a payload that, without backslash-first escaping, would break out of
    # the name contains '...' literal: \' terminates the string without our fix.
    payload = "foo\\' or 'EVIL_ID' in parents and 'x"
    drive_list(drive, folder_id="ValidFolder123", query=payload)
    kwargs = drive.files.return_value.list.call_args.kwargs
    q = kwargs["q"]
    # The escaped form must contain the doubly-escaped backslash+quote sequence.
    assert "\\\\'" in q, f"expected escaped backslash+quote in: {q!r}"
    # Extract only the name-contains fragment and assert no UNESCAPED (bare) quote
    # appears before " in parents" — an unescaped quote would allow injection.
    # A bare ' is any ' not preceded by \. We check the filter fragment for the
    # pattern [^\\]' in parents (or ^' in parents at start).
    parts = q.split("name contains '", 1)
    assert len(parts) == 2, "expected 'name contains' clause"
    filter_part = parts[1]
    # Look for unescaped single-quote followed by " in parents"
    assert not _re.search(r"(?<!\\)' in parents", filter_part), \
        f"unescaped injection appeared in name-contains fragment: {filter_part!r}"


def test_drive_list_invalid_folder_id_raises_before_api():
    """A malformed folder_id containing special chars raises ValueError without calling the API."""
    drive = MagicMock()
    with pytest.raises(ValueError, match="Invalid Drive ID"):
        drive_list(drive, folder_id="abc' or '1")
    drive.files.return_value.list.assert_not_called()


def test_is_valid_drive_id_accepts_valid():
    assert is_valid_drive_id("abc123") is True
    assert is_valid_drive_id("A_b-C") is True
    assert is_valid_drive_id("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms") is True


def test_is_valid_drive_id_rejects_invalid():
    assert is_valid_drive_id("abc' or '1") is False
    assert is_valid_drive_id("has space") is False
    assert is_valid_drive_id("") is False


def test_validate_drive_id_raises_on_bad_input():
    with pytest.raises(ValueError, match="Invalid Drive ID"):
        validate_drive_id("abc' or '1")
