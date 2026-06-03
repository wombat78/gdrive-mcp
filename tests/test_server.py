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


# FIX 3: verify that ops and values are typed as "array" in the generated schemas

def _prop_is_array(prop: dict) -> bool:
    """Return True if a JSON Schema property is an array type (direct or anyOf/optional)."""
    if prop.get("type") == "array":
        return True
    # Optional[list] → anyOf: [{type: array, ...}, {type: null}]
    for variant in prop.get("anyOf", []):
        if variant.get("type") == "array":
            return True
    return False


def test_docs_edit_ops_schema_is_array():
    """ops parameter must be typed as array (not string) in the FastMCP tool schema."""
    svc = MagicMock()
    mcp = build_mcp(svc, enabled_tools=("docs_edit",))
    tool = mcp._tool_manager.get_tool("docs_edit")
    schema = tool.parameters
    ops_prop = schema["properties"]["ops"]
    assert _prop_is_array(ops_prop), (
        f"Expected ops to have type 'array' (or anyOf array), got: {ops_prop!r}"
    )

def test_sheets_update_values_schema_is_array():
    """values parameter must be typed as array (not string) in the FastMCP tool schema."""
    svc = MagicMock()
    mcp = build_mcp(svc, enabled_tools=("sheets_update",))
    tool = mcp._tool_manager.get_tool("sheets_update")
    schema = tool.parameters
    values_prop = schema["properties"]["values"]
    assert _prop_is_array(values_prop), (
        f"Expected values to have type 'array' (or anyOf array), got: {values_prop!r}"
    )

def test_sheets_append_range_param_present():
    """sheets_append must expose a 'range' parameter in the MCP schema."""
    svc = MagicMock()
    mcp = build_mcp(svc, enabled_tools=("sheets_append",))
    tool = mcp._tool_manager.get_tool("sheets_append")
    schema = tool.parameters
    assert "range" in schema["properties"], (
        f"Expected 'range' in sheets_append schema, got: {list(schema['properties'])}"
    )
