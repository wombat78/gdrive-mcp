from __future__ import annotations
from typing import Any

from gdrive_mcp.auth import Clients
from gdrive_mcp.scope import ScopeGuard
from gdrive_mcp.tools.drive import get_parents, get_file_meta, drive_list, list_shared_with_me
from gdrive_mcp.tools.docs import docs_create, docs_read, docs_edit
from gdrive_mcp.tools.sheets import (
    sheets_create, sheets_read, sheets_update, sheets_append,
)


class GDriveService:
    def __init__(
        self,
        clients: Clients,
        allowed_folder_ids: tuple[str, ...],
        allowed_drive_ids: tuple[str, ...] = (),
    ):
        self._clients = clients
        self._guard = ScopeGuard(
            allowed_folder_ids=allowed_folder_ids,
            allowed_drive_ids=allowed_drive_ids,
            get_parents=lambda fid: get_parents(self._clients.drive, fid),
            get_drive_id=lambda fid: get_file_meta(self._clients.drive, fid)["driveId"],
        )

    # --- Drive ---
    def drive_list(self, folder_id: str | None = None, query: str | None = None) -> list[dict]:
        if folder_id:
            self._guard.assert_folder_allowed(folder_id)
            return drive_list(self._clients.drive, folder_id, query)
        results: list[dict] = []
        for f in self._guard.allowed_ids:              # explicit folders
            results.extend(drive_list(self._clients.drive, f, query))
        if self._guard.allowed_drive_ids:              # trusted drives: dynamic discovery
            results.extend(list_shared_with_me(self._clients.drive, tuple(self._guard.allowed_drive_ids)))
        return results

    # --- Docs ---
    def docs_create(self, title: str, folder_id: str) -> dict:
        self._guard.assert_folder_allowed(folder_id)
        return docs_create(self._clients.drive, title, folder_id)

    def docs_read(self, file_id: str) -> dict:
        self._guard.assert_in_scope(file_id)
        return docs_read(self._clients.docs, file_id)

    def docs_edit(self, file_id: str, ops: list[dict] | None = None, requests: list[dict] | None = None) -> dict:
        self._guard.assert_in_scope(file_id)
        return docs_edit(self._clients.docs, file_id, ops=ops, requests=requests)

    # --- Sheets ---
    def sheets_create(self, title: str, folder_id: str) -> dict:
        self._guard.assert_folder_allowed(folder_id)
        return sheets_create(self._clients.sheets, title, folder_id)

    def sheets_read(self, file_id: str, range: str) -> dict:
        self._guard.assert_in_scope(file_id)
        return sheets_read(self._clients.sheets, file_id, range)

    def sheets_update(self, file_id: str, range: str, values: list[list]) -> dict:
        self._guard.assert_in_scope(file_id)
        return sheets_update(self._clients.sheets, file_id, range, values)

    def sheets_append(self, file_id: str, range: str, values: list[list]) -> dict:
        self._guard.assert_in_scope(file_id)
        return sheets_append(self._clients.sheets, file_id, range, values)
