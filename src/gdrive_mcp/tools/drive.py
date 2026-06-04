from __future__ import annotations
import re
from typing import Any

_FIELDS = "files(id, name, mimeType, modifiedTime)"
_DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

_MAX_TEXT_CHARS = 1_000_000

# Extensions that indicate a text-decodable file regardless of MIME type
_TEXT_EXTENSIONS = {
    ".md", ".markdown", ".txt", ".json", ".csv", ".tsv",
    ".yaml", ".yml", ".xml", ".html", ".htm",
}

# MIME types (outside text/*) that are text-decodable
_TEXT_MIMES = {
    "application/json",
    "application/xml",
    "application/x-yaml",
    "application/yaml",
    "application/markdown",
}

# Export MIME types for Google-native formats
_GOOGLE_EXPORT_MAP = {
    "application/vnd.google-apps.document": "text/markdown",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


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


def get_file_meta(drive: Any, file_id: str) -> dict:
    m = (
        drive.files()
        .get(fileId=file_id, fields="parents, driveId", supportsAllDrives=True)
        .execute()
    )
    return {"parents": m.get("parents", []), "driveId": m.get("driveId")}


def list_shared_with_me(drive: Any, allowed_drive_ids: tuple) -> list[dict]:
    resp = (
        drive.files()
        .list(
            q="sharedWithMe = true and trashed = false",
            fields="files(id, name, mimeType, modifiedTime, driveId)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=200,
        )
        .execute()
    )
    allowed = set(allowed_drive_ids)
    return [
        {k: f.get(k) for k in ("id", "name", "mimeType", "modifiedTime")}
        for f in resp.get("files", []) if f.get("driveId") in allowed
    ]


def read_file(drive: Any, file_id: str) -> dict:
    """Read a native/uploaded file or export a Google-native file to text.

    Returns a dict with keys: id, name, mimeType, text.
    """
    meta = (
        drive.files()
        .get(fileId=file_id, fields="id, name, mimeType", supportsAllDrives=True)
        .execute()
    )
    mt = meta.get("mimeType", "")
    name = meta.get("name", "")

    if mt.startswith("application/vnd.google-apps."):
        export_mime = _GOOGLE_EXPORT_MAP.get(mt)
        if export_mime is None:
            raise ValueError(f"unsupported Google type: {mt}")
        raw = (
            drive.files()
            .export_media(fileId=file_id, mimeType=export_mime)
            .execute()
        )
    else:
        raw = (
            drive.files()
            .get_media(fileId=file_id, supportsAllDrives=True)
            .execute()
        )
        # Determine if we can decode this as text
        name_lower = name.lower()
        ext = "." + name_lower.rsplit(".", 1)[-1] if "." in name_lower else ""
        is_text = (
            mt.startswith("text/")
            or mt in _TEXT_MIMES
            or ext in _TEXT_EXTENSIONS
        )
        if not is_text:
            raise ValueError(f"binary file not readable as text: {mt}")

    # raw may be bytes or str depending on the client
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="replace")
    else:
        text = raw

    if len(text) > _MAX_TEXT_CHARS:
        text = text[:_MAX_TEXT_CHARS] + "\n[truncated]"

    return {
        "id": meta.get("id", file_id),
        "name": name,
        "mimeType": mt,
        "text": text,
    }


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
