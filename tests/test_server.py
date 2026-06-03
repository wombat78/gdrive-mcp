from unittest.mock import MagicMock
from gdrive_mcp.server import build_mcp, ALL_TOOL_NAMES

def test_all_eight_tools_registered_by_default():
    svc = MagicMock()
    mcp = build_mcp(svc, enabled_tools=None)
    names = {t.name for t in mcp._tool_manager.list_tools()}
    assert names == set(ALL_TOOL_NAMES)
    assert len(ALL_TOOL_NAMES) == 8

def test_enabled_tools_filters_registration():
    svc = MagicMock()
    mcp = build_mcp(svc, enabled_tools=("docs_read", "sheets_read"))
    names = {t.name for t in mcp._tool_manager.list_tools()}
    assert names == {"docs_read", "sheets_read"}

def test_tool_delegates_to_service():
    svc = MagicMock()
    svc.docs_read.return_value = {"title": "T", "text": "x"}
    mcp = build_mcp(svc, enabled_tools=("docs_read",))
    tool = mcp._tool_manager.get_tool("docs_read")
    result = tool.fn(file_id="D1")
    svc.docs_read.assert_called_once_with(file_id="D1")
    assert result["text"] == "x"
