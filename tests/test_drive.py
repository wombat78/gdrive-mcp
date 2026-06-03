from unittest.mock import MagicMock
from gdrive_mcp.tools.drive import get_parents, drive_list

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
