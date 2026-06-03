from unittest.mock import MagicMock
from gdrive_mcp.tools.sheets import sheets_create, sheets_read, sheets_update, sheets_append

def test_sheets_create_in_folder_returns_id_and_url():
    gc = MagicMock()
    gc.create.return_value.id = "S1"
    out = sheets_create(gc, title="Q1", folder_id="M")
    gc.create.assert_called_once_with("Q1", folder_id="M")
    assert out == {"id": "S1", "url": "https://docs.google.com/spreadsheets/d/S1/edit"}

def test_sheets_read_returns_values():
    gc = MagicMock()
    ws = gc.open_by_key.return_value.sheet1
    ws.get.return_value = [["a", "b"], ["1", "2"]]
    out = sheets_read(gc, "S1", "A1:B2")
    gc.open_by_key.assert_called_once_with("S1")
    ws.get.assert_called_once_with("A1:B2")
    assert out == {"values": [["a", "b"], ["1", "2"]]}

def test_sheets_update_writes_range():
    gc = MagicMock()
    ws = gc.open_by_key.return_value.sheet1
    ws.update.return_value = {"updatedCells": 4}
    out = sheets_update(gc, "S1", "A1:B2", [["a", "b"], ["1", "2"]])
    # gspread 6.x: values first, then range
    ws.update.assert_called_once_with([["a", "b"], ["1", "2"]], "A1:B2")
    assert out == {"updatedCells": 4}

def test_sheets_append_with_range():
    """sheets_append must accept a range and pass it as table_range (spec §6)."""
    gc = MagicMock()
    ws = gc.open_by_key.return_value.sheet1
    ws.append_rows.return_value = {"updates": {"updatedRows": 2}}
    out = sheets_append(gc, "S1", "A1", [["x"], ["y"]])
    ws.append_rows.assert_called_once_with([["x"], ["y"]], table_range="A1")
    assert out == {"updates": {"updatedRows": 2}}
