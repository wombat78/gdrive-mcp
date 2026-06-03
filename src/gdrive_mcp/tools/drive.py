from __future__ import annotations
from typing import Any

_FIELDS = "files(id, name, mimeType, modifiedTime)"


def get_parents(drive: Any, file_id: str) -> list[str]:
    meta = (
        drive.files()
        .get(fileId=file_id, fields="parents", supportsAllDrives=True)
        .execute()
    )
    return meta.get("parents", [])


def drive_list(drive: Any, folder_id: str, query: str | None = None) -> list[dict]:
    q = f"'{folder_id}' in parents and trashed = false"
    if query:
        safe = query.replace("'", "\\'")
        q += f" and name contains '{safe}'"
    resp = (
        drive.files()
        .list(
            q=q,
            fields=_FIELDS,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=100,
        )
        .execute()
    )
    return resp.get("files", [])
