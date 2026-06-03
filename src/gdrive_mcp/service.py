from __future__ import annotations
from typing import Any

from gdrive_mcp.auth import Clients
from gdrive_mcp.scope import ScopeGuard
from gdrive_mcp.tools.drive import get_parents, drive_list
from gdrive_mcp.tools.docs import docs_create, docs_read, docs_edit
from gdrive_mcp.tools.sheets import (
    sheets_create, sheets_read, sheets_update, sheets_append,
)


class GDriveService:
    def __init__(self, clients: Clients, allowed_folder_ids: tuple[str, ...]):
        self._clients = clients
        self._guard = ScopeGuard(
            allowed=allowed_folder_ids,
            get_parents=lambda fid: get_parents(self._clients.drive, fid),
        )

    # --- Drive ---
    def drive_list(self, folder_id: str | None = None, query: str | None = None) -> list[dict]:
        folders = [folder_id] if folder_id else list(self._guard._allowed)
        results: list[dict] = []
        for f in folders:
            self._guard.assert_folder_allowed(f)
            results.extend(drive_list(self._clients.drive, f, query))
        return results

    # --- Docs ---
    def docs_create(self, title: str, folder_id: str) -> dict:
        self._guard.assert_folder_allowed(folder_id)
        return docs_create(self._clients.drive, title, folder_id)

    def docs_read(self, file_id: str) -> dict:
        self._guard.assert_in_scope(file_id)
        return docs_read(self._clients.docs, file_id)

    def docs_edit(self, file_id: str, ops=None, requests=None) -> dict:
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

    def sheets_append(self, file_id: str, values: list[list]) -> dict:
        self._guard.assert_in_scope(file_id)
        return sheets_append(self._clients.sheets, file_id, values)
