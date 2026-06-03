from unittest.mock import MagicMock, patch
import pytest
from gdrive_mcp.service import GDriveService
from gdrive_mcp.scope import OutOfScopeError

def _service(allowed=("M",), parents=None):
    parents = parents or {"D_in": ["M"], "D_out": ["X"]}
    clients = MagicMock()
    svc = GDriveService(clients, allowed_folder_ids=allowed)
    # stub parent resolution used by the scope guard
    svc._guard._get_parents = lambda fid: parents.get(fid, [])
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
