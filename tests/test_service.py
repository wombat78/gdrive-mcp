from unittest.mock import MagicMock, patch
import pytest
from gdrive_mcp.service import GDriveService
from gdrive_mcp.scope import OutOfScopeError

def _service(allowed=("M",), parents=None):
    parents = parents or {"D_in": ["M"], "D_out": ["X"]}
    clients = MagicMock()
    svc = GDriveService(clients, allowed_folder_ids=allowed, allowed_drive_ids=())
    # stub parent resolution used by the scope guard
    svc._guard._get_parents = lambda fid: parents.get(fid, [])
    svc._guard._get_drive_id = lambda fid: None
    return svc, clients


def _svc_drives(allowed_drives=("D1",), drive_of=None, parents=None):
    drive_of = drive_of or {"in": "D1", "out": "DX"}
    clients = MagicMock()
    svc = GDriveService(clients, allowed_folder_ids=(), allowed_drive_ids=allowed_drives)
    svc._guard._get_drive_id = lambda fid: drive_of.get(fid)
    svc._guard._get_parents = lambda fid: (parents or {}).get(fid, [])
    return svc, clients

def test_create_into_allowed_folder_ok():
    svc, clients = _service()
    with patch("gdrive_mcp.service.docs_create", return_value={"id": "D1", "url": "u"}) as mk:
        out = svc.docs_create(title="t", folder_id="M")
    mk.assert_called_once()
    assert out["id"] == "D1"

def test_create_into_foreign_folder_blocked():
    svc, _ = _service()
    with pytest.raises(OutOfScopeError):
        svc.docs_create(title="t", folder_id="X")

def test_edit_existing_out_of_scope_blocked_before_api():
    svc, clients = _service()
    with patch("gdrive_mcp.service.docs_edit") as mk:
        with pytest.raises(OutOfScopeError):
            svc.docs_edit(file_id="D_out", ops=[{"find": "a", "replace": "b"}])
    mk.assert_not_called()

def test_edit_existing_in_scope_calls_tool():
    svc, clients = _service()
    with patch("gdrive_mcp.service.docs_edit", return_value={"applied": 1}) as mk:
        out = svc.docs_edit(file_id="D_in", ops=[{"find": "a", "replace": "b"}])
    mk.assert_called_once()
    assert out == {"applied": 1}


# --- FIX 6: scope coverage for all previously-untested service methods ---

# drive_list
def test_drive_list_out_of_scope_blocked_before_api():
    svc, _ = _service()
    with patch("gdrive_mcp.service.drive_list") as mk:
        with pytest.raises(OutOfScopeError):
            svc.drive_list(folder_id="X")
    mk.assert_not_called()

def test_drive_list_in_scope_delegates():
    svc, _ = _service()
    with patch("gdrive_mcp.service.drive_list", return_value=[{"id": "f1"}]) as mk:
        out = svc.drive_list(folder_id="M")
    mk.assert_called_once()
    assert out == [{"id": "f1"}]

# docs_read
def test_docs_read_out_of_scope_blocked_before_api():
    svc, _ = _service()
    with patch("gdrive_mcp.service.docs_read") as mk:
        with pytest.raises(OutOfScopeError):
            svc.docs_read(file_id="D_out")
    mk.assert_not_called()

def test_docs_read_in_scope_delegates():
    svc, _ = _service()
    with patch("gdrive_mcp.service.docs_read", return_value={"title": "t", "text": "x"}) as mk:
        out = svc.docs_read(file_id="D_in")
    mk.assert_called_once()
    assert out["title"] == "t"

# sheets_create
def test_sheets_create_out_of_scope_blocked_before_api():
    svc, _ = _service()
    with patch("gdrive_mcp.service.sheets_create") as mk:
        with pytest.raises(OutOfScopeError):
            svc.sheets_create(title="s", folder_id="X")
    mk.assert_not_called()

def test_sheets_create_in_scope_delegates():
    svc, _ = _service()
    with patch("gdrive_mcp.service.sheets_create", return_value={"id": "S1", "url": "u"}) as mk:
        out = svc.sheets_create(title="s", folder_id="M")
    mk.assert_called_once()
    assert out["id"] == "S1"

# sheets_read
def test_sheets_read_out_of_scope_blocked_before_api():
    svc, _ = _service()
    with patch("gdrive_mcp.service.sheets_read") as mk:
        with pytest.raises(OutOfScopeError):
            svc.sheets_read(file_id="D_out", range="A1")
    mk.assert_not_called()

def test_sheets_read_in_scope_delegates():
    svc, _ = _service()
    with patch("gdrive_mcp.service.sheets_read", return_value={"values": [["v"]]}) as mk:
        out = svc.sheets_read(file_id="D_in", range="A1")
    mk.assert_called_once()
    assert out["values"] == [["v"]]

# sheets_update
def test_sheets_update_out_of_scope_blocked_before_api():
    svc, _ = _service()
    with patch("gdrive_mcp.service.sheets_update") as mk:
        with pytest.raises(OutOfScopeError):
            svc.sheets_update(file_id="D_out", range="A1", values=[["x"]])
    mk.assert_not_called()

def test_sheets_update_in_scope_delegates():
    svc, _ = _service()
    with patch("gdrive_mcp.service.sheets_update", return_value={"updatedCells": 1}) as mk:
        out = svc.sheets_update(file_id="D_in", range="A1", values=[["x"]])
    mk.assert_called_once()
    assert out["updatedCells"] == 1

# sheets_append — also covers FIX 2 (range parameter propagated)
def test_sheets_append_out_of_scope_blocked_before_api():
    svc, _ = _service()
    with patch("gdrive_mcp.service.sheets_append") as mk:
        with pytest.raises(OutOfScopeError):
            svc.sheets_append(file_id="D_out", range="A1", values=[["x"]])
    mk.assert_not_called()

def test_sheets_append_in_scope_delegates_with_range():
    svc, _ = _service()
    with patch("gdrive_mcp.service.sheets_append", return_value={"updates": {}}) as mk:
        out = svc.sheets_append(file_id="D_in", range="A1", values=[["x"]])
    mk.assert_called_once_with(svc._clients.sheets, "D_in", "A1", [["x"]], None)
    assert out == {"updates": {}}


# Task 4 — driveId scoping in service

def test_read_in_allowed_drive_ok():
    svc, _ = _svc_drives()
    with patch("gdrive_mcp.service.docs_read", return_value={"title": "t", "text": "x"}) as mk:
        svc.docs_read(file_id="in")
    mk.assert_called_once()

def test_read_in_foreign_drive_blocked():
    svc, _ = _svc_drives()
    with patch("gdrive_mcp.service.docs_read") as mk:
        with pytest.raises(OutOfScopeError):
            svc.docs_read(file_id="out")
    mk.assert_not_called()

def test_drive_list_none_returns_shared_within_allowed_drive():
    svc, clients = _svc_drives()
    with patch("gdrive_mcp.service.list_shared_with_me", return_value=[{"id": "a", "name": "Go-to-Market"}]) as mk:
        out = svc.drive_list(folder_id=None)
    mk.assert_called_once_with(clients.drive, ("D1",))
    assert out == [{"id": "a", "name": "Go-to-Market"}]


# ── drive_read_file scope tests ───────────────────────────────────────────────

def test_drive_read_file_out_of_scope_blocked_before_api():
    """Out-of-scope file_id raises OutOfScopeError; read_file is never called."""
    svc, _ = _service()
    with patch("gdrive_mcp.service.read_file") as mk:
        with pytest.raises(OutOfScopeError):
            svc.drive_read_file(file_id="D_out")
    mk.assert_not_called()


def test_drive_read_file_in_scope_delegates():
    """In-scope file_id calls through to read_file and returns its result."""
    svc, clients = _service()
    expected = {"id": "D_in", "name": "notes.md", "mimeType": "text/markdown", "text": "# hi"}
    with patch("gdrive_mcp.service.read_file", return_value=expected) as mk:
        out = svc.drive_read_file(file_id="D_in")
    mk.assert_called_once_with(clients.drive, "D_in")
    assert out == expected
