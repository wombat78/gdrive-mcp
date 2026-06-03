from __future__ import annotations
from typing import Any

from mcp.server.fastmcp import FastMCP

ALL_TOOL_NAMES = (
    "drive_list",
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

    register("drive_list",
             lambda folder_id=None, query=None: service.drive_list(folder_id=folder_id, query=query))
    register("docs_create",
             lambda title, folder_id: service.docs_create(title=title, folder_id=folder_id))
    register("docs_read",
             lambda file_id: service.docs_read(file_id=file_id))
    register("docs_edit",
             lambda file_id, ops=None, requests=None: service.docs_edit(file_id=file_id, ops=ops, requests=requests))
    register("sheets_create",
             lambda title, folder_id: service.sheets_create(title=title, folder_id=folder_id))
    register("sheets_read",
             lambda file_id, range: service.sheets_read(file_id=file_id, range=range))
    register("sheets_update",
             lambda file_id, range, values: service.sheets_update(file_id=file_id, range=range, values=values))
    register("sheets_append",
             lambda file_id, values: service.sheets_append(file_id=file_id, values=values))

    return mcp
