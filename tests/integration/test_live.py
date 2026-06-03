import os
import pytest

pytestmark = pytest.mark.skipif(
    not (os.getenv("GDRIVE_TEST_SA_PATH") and os.getenv("GDRIVE_TEST_FOLDER_ID")),
    reason="set GDRIVE_TEST_SA_PATH and GDRIVE_TEST_FOLDER_ID to run live integration",
)


@pytest.fixture(autouse=True)
def cleanup_live_files(request):
    """Trash any Doc/Sheet created during the test so the live folder stays clean."""
    created_ids: list = []
    yield created_ids
    if not created_ids:
        return
    import json
    from gdrive_mcp.auth import build_clients
    folder = os.environ["GDRIVE_TEST_FOLDER_ID"]
    with open(os.environ["GDRIVE_TEST_SA_PATH"]) as fh:
        info = json.load(fh)
    clients = build_clients(info)
    for file_id in created_ids:
        try:
            clients.drive.files().update(
                fileId=file_id,
                body={"trashed": True},
                supportsAllDrives=True,
            ).execute()
        except Exception:
            pass  # best-effort; don't mask the test result


def test_doc_and_sheet_roundtrip(cleanup_live_files):
    import json
    from gdrive_mcp.auth import build_clients
    from gdrive_mcp.service import GDriveService

    with open(os.environ["GDRIVE_TEST_SA_PATH"]) as fh:
        info = json.load(fh)
    folder = os.environ["GDRIVE_TEST_FOLDER_ID"]
    svc = GDriveService(build_clients(info), (folder,))

    doc = svc.docs_create(title="gdrive-mcp itest", folder_id=folder)
    cleanup_live_files.append(doc["id"])
    svc.docs_edit(file_id=doc["id"], ops=[{"insert_at": 1, "text": "hello"}])
    assert "hello" in svc.docs_read(file_id=doc["id"])["text"]

    sheet = svc.sheets_create(title="gdrive-mcp itest", folder_id=folder)
    cleanup_live_files.append(sheet["id"])
    svc.sheets_update(file_id=sheet["id"], range="A1:B1", values=[["a", "b"]])
    assert svc.sheets_read(file_id=sheet["id"], range="A1:B1")["values"] == [["a", "b"]]
