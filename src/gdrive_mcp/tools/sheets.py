from __future__ import annotations
from typing import Any


def _url(sheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"


def sheets_create(gc: Any, title: str, folder_id: str) -> dict:
    spreadsheet = gc.create(title, folder_id=folder_id)
    return {"id": spreadsheet.id, "url": _url(spreadsheet.id)}


def _worksheet(spreadsheet: Any, worksheet: str | None = None) -> Any:
    if worksheet is None:
        return spreadsheet.sheet1
    try:
        ws = spreadsheet.get_worksheet_by_id(int(worksheet))
        if ws is None:
            raise ValueError(f"Worksheet {worksheet!r} was not found")
        return ws
    except (ValueError, TypeError) as exc:
        if isinstance(exc, ValueError) and "was not found" in str(exc):
            raise
        return spreadsheet.worksheet(worksheet)


def sheets_add_worksheet(gc: Any, file_id: str, title: str, rows: int = 1000, cols: int = 26) -> dict:
    ws = gc.open_by_key(file_id).add_worksheet(title=title, rows=rows, cols=cols)
    return {"title": ws.title, "id": ws.id}


def sheets_list_worksheets(gc: Any, file_id: str) -> list[dict]:
    return [{"title": ws.title, "id": ws.id, "rows": ws.row_count, "cols": ws.col_count}
            for ws in gc.open_by_key(file_id).worksheets()]


def sheets_read(gc: Any, file_id: str, range: str, worksheet: str | None = None) -> dict:
    ws = _worksheet(gc.open_by_key(file_id), worksheet)
    return {"values": ws.get(range)}


def sheets_update(gc: Any, file_id: str, range: str, values: list[list], worksheet: str | None = None) -> dict:
    ws = _worksheet(gc.open_by_key(file_id), worksheet)
    # gspread 6.x: values first, range second
    result = ws.update(values, range)
    return {"updatedCells": result.get("updatedCells")}


def sheets_append(gc: Any, file_id: str, range: str, values: list[list], worksheet: str | None = None) -> dict:
    ws = _worksheet(gc.open_by_key(file_id), worksheet)
    result = ws.append_rows(values, table_range=range)
    return {"updates": result.get("updates")}
