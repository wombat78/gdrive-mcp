from __future__ import annotations
import re
from typing import Any

_FIELDS = "files(id, name, mimeType, modifiedTime)"
_DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def is_valid_drive_id(s: str) -> bool:
    """Return True iff *s* matches the Drive ID character set."""
    return bool(s and _DRIVE_ID_RE.match(s))


def validate_drive_id(s: str) -> None:
    """Raise ValueError if *s* is not a valid Drive ID."""
    if not is_valid_drive_id(s):
        raise ValueError(f"Invalid Drive ID: {s!r}")


def get_parents(drive: Any, file_id: str) -> list[str]:
    meta = (
        drive.files()
        .get(fileId=file_id, fields="parents", supportsAllDrives=True)
        .execute()
    )
    return meta.get("parents", [])


def drive_list(drive: Any, folder_id: str, query: str | None = None) -> list[dict]:
    validate_drive_id(folder_id)
    q = f"'{folder_id}' in parents and trashed = false"
    if query:
        # Escape backslash BEFORE quote to prevent injection.
        safe = query.replace("\\", "\\\\").replace("'", "\\'")
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
