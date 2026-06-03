import os
import pytest

pytestmark = pytest.mark.skipif(
    not (os.getenv("GDRIVE_TEST_SA_PATH") and os.getenv("GDRIVE_TEST_FOLDER_ID")),
    reason="set GDRIVE_TEST_SA_PATH and GDRIVE_TEST_FOLDER_ID to run live integration",
)

def test_doc_and_sheet_roundtrip():
    import json
    from gdrive_mcp.auth import build_clients
    from gdrive_mcp.service import GDriveService

    info = json.load(open(os.environ["GDRIVE_TEST_SA_PATH"]))
    folder = os.environ["GDRIVE_TEST_FOLDER_ID"]
    svc = GDriveService(build_clients(info), (folder,))

    doc = svc.docs_create(title="gdrive-mcp itest", folder_id=folder)
    svc.docs_edit(file_id=doc["id"], ops=[{"insert_at": 1, "text": "hello"}])
    assert "hello" in svc.docs_read(file_id=doc["id"])["text"]

    sheet = svc.sheets_create(title="gdrive-mcp itest", folder_id=folder)
    svc.sheets_update(file_id=sheet["id"], range="A1:B1", values=[["a", "b"]])
    assert svc.sheets_read(file_id=sheet["id"], range="A1:B1")["values"] == [["a", "b"]]
