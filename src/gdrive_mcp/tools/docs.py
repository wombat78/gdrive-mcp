from __future__ import annotations
from typing import Any

from gdrive_mcp.docs_ops import expand_ops

_DOC_MIME = "application/vnd.google-apps.document"


def docs_create(drive: Any, title: str, folder_id: str) -> dict:
    meta = (
        drive.files()
        .create(
            body={"name": title, "mimeType": _DOC_MIME, "parents": [folder_id]},
            fields="id",
            supportsAllDrives=True,
        )
        .execute()
    )
    doc_id = meta["id"]
    return {"id": doc_id, "url": f"https://docs.google.com/document/d/{doc_id}/edit"}


def docs_read(docs: Any, file_id: str) -> dict:
    doc = docs.documents().get(documentId=file_id).execute()
    parts: list[str] = []
    for element in doc.get("body", {}).get("content", []):
        para = element.get("paragraph")
        if not para:
            continue
        for run in para.get("elements", []):
            text_run = run.get("textRun")
            if text_run:
                parts.append(text_run.get("content", ""))
    return {"title": doc.get("title", ""), "text": "".join(parts)}


def docs_edit(
    docs: Any,
    file_id: str,
    ops: list[dict] | None = None,
    requests: list[dict] | None = None,
) -> dict:
    if not ops and not requests:
        raise ValueError("docs_edit requires at least one of ops or requests")
    payload: list[dict] = []
    if ops:
        payload.extend(expand_ops(ops))
    if requests:
        payload.extend(requests)
    docs.documents().batchUpdate(
        documentId=file_id, body={"requests": payload}
    ).execute()
    return {"applied": len(payload)}
