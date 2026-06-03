from unittest.mock import MagicMock
import pytest
from gdrive_mcp.tools.docs import docs_create, docs_read, docs_edit
from gdrive_mcp.docs_ops import DocsOpError

def test_docs_create_uses_drive_files_create_in_folder():
    drive = MagicMock()
    drive.files.return_value.create.return_value.execute.return_value = {"id": "D1"}
    out = docs_create(drive, title="Plan", folder_id="M")
    body = drive.files.return_value.create.call_args.kwargs["body"]
    assert body["name"] == "Plan"
    assert body["mimeType"] == "application/vnd.google-apps.document"
    assert body["parents"] == ["M"]
    assert out == {"id": "D1", "url": "https://docs.google.com/document/d/D1/edit"}

def test_docs_read_concatenates_paragraph_text():
    docs = MagicMock()
    docs.documents.return_value.get.return_value.execute.return_value = {
        "title": "T",
        "body": {"content": [
            {"paragraph": {"elements": [
                {"textRun": {"content": "Hello "}},
                {"textRun": {"content": "world"}},
            ]}},
        ]},
    }
    out = docs_read(docs, "D1")
    assert out["title"] == "T"
    assert out["text"] == "Hello world"

def test_docs_edit_expands_ops_and_calls_batch_update():
    docs = MagicMock()
    docs.documents.return_value.batchUpdate.return_value.execute.return_value = {}
    out = docs_edit(docs, "D1", ops=[{"find": "a", "replace": "b"}], requests=None)
    kwargs = docs.documents.return_value.batchUpdate.call_args.kwargs
    assert kwargs["documentId"] == "D1"
    assert kwargs["body"]["requests"][0]["replaceAllText"]["replaceText"] == "b"
    assert out == {"applied": 1}

def test_docs_edit_passes_raw_requests_after_ops():
    docs = MagicMock()
    docs.documents.return_value.batchUpdate.return_value.execute.return_value = {}
    raw = [{"insertText": {"location": {"index": 1}, "text": "z"}}]
    out = docs_edit(docs, "D1", ops=[{"find": "a", "replace": "b"}], requests=raw)
    reqs = docs.documents.return_value.batchUpdate.call_args.kwargs["body"]["requests"]
    assert len(reqs) == 2
    assert "replaceAllText" in reqs[0]
    assert "insertText" in reqs[1]
    assert out == {"applied": 2}

def test_docs_edit_requires_at_least_one():
    docs = MagicMock()
    with pytest.raises(ValueError, match="ops or requests"):
        docs_edit(docs, "D1", ops=None, requests=None)
