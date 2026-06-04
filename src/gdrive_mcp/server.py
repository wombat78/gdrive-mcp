from __future__ import annotations
from typing import Any

from mcp.server.fastmcp import FastMCP

ALL_TOOL_NAMES = (
    "drive_list", "drive_read_file",
    "docs_create", "docs_read", "docs_edit",
    "sheets_create", "sheets_read", "sheets_update", "sheets_append",
)


def build_mcp(service: Any, enabled_tools: tuple[str, ...] | None,
              host: str = "0.0.0.0", port: int = 8080) -> FastMCP:
    mcp = FastMCP("gdrive-mcp", host=host, port=port)
    enabled = set(enabled_tools) if enabled_tools else set(ALL_TOOL_NAMES)

    def register(name, fn):
        if name in enabled:
            mcp.add_tool(fn, name=name)

    # Explicit annotated wrapper functions so FastMCP infers correct JSON Schema types
    # (lambdas have no annotations → FastMCP falls back to string for all params).

    def drive_list(
        folder_id: str | None = None,
        query: str | None = None,
    ) -> list[dict]:
        return service.drive_list(folder_id=folder_id, query=query)

    def drive_read_file(file_id: str) -> dict:
        return service.drive_read_file(file_id=file_id)

    def docs_create(title: str, folder_id: str) -> dict:
        return service.docs_create(title=title, folder_id=folder_id)

    def docs_read(file_id: str) -> dict:
        return service.docs_read(file_id=file_id)

    def docs_edit(
        file_id: str,
        ops: list[dict] | None = None,
        requests: list[dict] | None = None,
    ) -> dict:
        return service.docs_edit(file_id=file_id, ops=ops, requests=requests)

    def sheets_create(title: str, folder_id: str) -> dict:
        return service.sheets_create(title=title, folder_id=folder_id)

    def sheets_read(file_id: str, range: str) -> dict:
        return service.sheets_read(file_id=file_id, range=range)

    def sheets_update(file_id: str, range: str, values: list[list]) -> dict:
        return service.sheets_update(file_id=file_id, range=range, values=values)

    def sheets_append(file_id: str, range: str, values: list[list]) -> dict:
        return service.sheets_append(file_id=file_id, range=range, values=values)

    register("drive_list", drive_list)
    register("drive_read_file", drive_read_file)
    register("docs_create", docs_create)
    register("docs_read", docs_read)
    register("docs_edit", docs_edit)
    register("sheets_create", sheets_create)
    register("sheets_read", sheets_read)
    register("sheets_update", sheets_update)
    register("sheets_append", sheets_append)

    return mcp
