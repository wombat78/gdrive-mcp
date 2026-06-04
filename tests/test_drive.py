from unittest.mock import MagicMock, call
import pytest
from gdrive_mcp.tools.drive import get_parents, drive_list, is_valid_drive_id, validate_drive_id, get_file_meta, list_shared_with_me, read_file

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


def test_get_file_meta_returns_parents_and_drive_id():
    drive = MagicMock()
    drive.files.return_value.get.return_value.execute.return_value = {"parents": ["P"], "driveId": "D1"}
    meta = get_file_meta(drive, "f1")
    assert meta == {"parents": ["P"], "driveId": "D1"}
    kw = drive.files.return_value.get.call_args.kwargs
    assert kw["fileId"] == "f1"
    assert kw["fields"] == "parents, driveId"
    assert kw["supportsAllDrives"] is True

def test_get_file_meta_missing_keys_defaults():
    drive = MagicMock()
    drive.files.return_value.get.return_value.execute.return_value = {}
    assert get_file_meta(drive, "f1") == {"parents": [], "driveId": None}

def test_list_shared_with_me_filters_to_allowed_drives():
    drive = MagicMock()
    drive.files.return_value.list.return_value.execute.return_value = {"files": [
        {"id": "a", "name": "InDrive", "mimeType": "application/vnd.google-apps.folder", "modifiedTime": "t", "driveId": "D1"},
        {"id": "b", "name": "Foreign", "mimeType": "application/vnd.google-apps.folder", "modifiedTime": "t", "driveId": "DX"},
        {"id": "c", "name": "MyDriveShare", "mimeType": "application/pdf", "modifiedTime": "t"},  # no driveId
    ]}
    out = list_shared_with_me(drive, allowed_drive_ids=("D1",))
    assert [f["id"] for f in out] == ["a"]   # only the one in D1
    q = drive.files.return_value.list.call_args.kwargs["q"]
    assert "sharedWithMe = true" in q and "trashed = false" in q
    assert drive.files.return_value.list.call_args.kwargs["includeItemsFromAllDrives"] is True


# ── read_file tests ──────────────────────────────────────────────────────────

def _drive_read_file_mock(mime_type: str, file_name: str, content, *, is_google=False):
    """Build a mock Drive client for read_file tests.

    content should be bytes (for get_media) or bytes (for export_media).
    """
    drive = MagicMock()
    # files().get() → meta
    drive.files.return_value.get.return_value.execute.return_value = {
        "id": "FILE1",
        "name": file_name,
        "mimeType": mime_type,
    }
    if is_google:
        drive.files.return_value.export_media.return_value.execute.return_value = content
    else:
        drive.files.return_value.get_media.return_value.execute.return_value = content
    return drive


def test_read_file_native_markdown_returns_text():
    """A native .md file (text/markdown mimeType) is downloaded via get_media and decoded."""
    drive = _drive_read_file_mock("text/markdown", "notes.md", b"# Brand Book\nhello")
    result = read_file(drive, "FILE1")
    assert result["id"] == "FILE1"
    assert result["name"] == "notes.md"
    assert result["mimeType"] == "text/markdown"
    assert "# Brand Book" in result["text"]
    assert "hello" in result["text"]
    # Should have called get_media, not export_media
    drive.files.return_value.get_media.assert_called_once()
    drive.files.return_value.export_media.assert_not_called()


def test_read_file_native_json_via_extension():
    """A file with application/octet-stream mimeType but .json extension is decoded as text."""
    drive = _drive_read_file_mock("application/octet-stream", "config.json", b'{"key": "value"}')
    result = read_file(drive, "FILE1")
    assert result["text"] == '{"key": "value"}'


def test_read_file_native_json_mime():
    """A file with application/json mimeType is decoded as text."""
    drive = _drive_read_file_mock("application/json", "config.json", b'{"key": "value"}')
    result = read_file(drive, "FILE1")
    assert '{"key": "value"}' in result["text"]


def test_read_file_google_doc_exports_markdown():
    """A Google Doc is exported via export_media with mimeType text/markdown."""
    drive = _drive_read_file_mock(
        "application/vnd.google-apps.document",
        "My Doc",
        b"# Heading\nBody text",
        is_google=True,
    )
    result = read_file(drive, "FILE1")
    assert "# Heading" in result["text"]
    assert "Body text" in result["text"]
    # Must use export_media, not get_media
    drive.files.return_value.export_media.assert_called_once()
    kw = drive.files.return_value.export_media.call_args.kwargs
    assert kw["fileId"] == "FILE1"
    assert kw["mimeType"] == "text/markdown"
    drive.files.return_value.get_media.assert_not_called()


def test_read_file_google_spreadsheet_exports_csv():
    """A Google Spreadsheet is exported as text/csv."""
    drive = _drive_read_file_mock(
        "application/vnd.google-apps.spreadsheet",
        "Budget",
        b"col1,col2\n1,2",
        is_google=True,
    )
    result = read_file(drive, "FILE1")
    assert "col1,col2" in result["text"]
    kw = drive.files.return_value.export_media.call_args.kwargs
    assert kw["mimeType"] == "text/csv"


def test_read_file_google_presentation_exports_plain():
    """A Google Presentation is exported as text/plain."""
    drive = _drive_read_file_mock(
        "application/vnd.google-apps.presentation",
        "Deck",
        b"Slide 1 text",
        is_google=True,
    )
    result = read_file(drive, "FILE1")
    assert "Slide 1 text" in result["text"]
    kw = drive.files.return_value.export_media.call_args.kwargs
    assert kw["mimeType"] == "text/plain"


def test_read_file_google_unsupported_type_raises():
    """An unsupported Google-native type (e.g. form) raises ValueError."""
    drive = _drive_read_file_mock(
        "application/vnd.google-apps.form",
        "Survey",
        b"",
        is_google=True,
    )
    with pytest.raises(ValueError, match="unsupported Google type"):
        read_file(drive, "FILE1")


def test_read_file_binary_raises():
    """A binary file (image/png, non-text name) raises ValueError."""
    drive = _drive_read_file_mock("image/png", "photo.png", b"\x89PNG\r\n\x1a\n")
    with pytest.raises(ValueError, match="binary file not readable as text"):
        read_file(drive, "FILE1")


def test_read_file_text_returned_as_str_not_re_decoded():
    """If get_media returns str instead of bytes, it should be returned directly."""
    drive = _drive_read_file_mock("text/plain", "notes.txt", "already a string")
    result = read_file(drive, "FILE1")
    assert result["text"] == "already a string"


def test_read_file_truncates_at_1_million_chars():
    """Text longer than 1_000_000 chars is truncated with a note."""
    big = b"x" * 1_100_000
    drive = _drive_read_file_mock("text/plain", "big.txt", big)
    result = read_file(drive, "FILE1")
    assert len(result["text"]) <= 1_000_100  # cap + note fits
    assert "[truncated]" in result["text"] or len(result["text"]) == 1_000_000 or "truncated" in result["text"]
