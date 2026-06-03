from __future__ import annotations
from typing import Any


def _url(sheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"


def sheets_create(gc: Any, title: str, folder_id: str) -> dict:
    spreadsheet = gc.create(title, folder_id=folder_id)
    return {"id": spreadsheet.id, "url": _url(spreadsheet.id)}


def sheets_read(gc: Any, file_id: str, range: str) -> dict:
    ws = gc.open_by_key(file_id).sheet1
    return {"values": ws.get(range)}


def sheets_update(gc: Any, file_id: str, range: str, values: list[list]) -> dict:
    ws = gc.open_by_key(file_id).sheet1
    result = ws.update(range, values)
    return {"updatedCells": result.get("updatedCells")}


def sheets_append(gc: Any, file_id: str, values: list[list]) -> dict:
    ws = gc.open_by_key(file_id).sheet1
    result = ws.append_rows(values)
    return {"updates": result.get("updates")}
