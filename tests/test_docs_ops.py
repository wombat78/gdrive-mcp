import pytest
from gdrive_mcp.docs_ops import expand_ops, DocsOpError

def test_find_replace_expands_to_replace_all_text():
    reqs = expand_ops([{"find": "foo", "replace": "bar"}])
    assert reqs == [{
        "replaceAllText": {
            "containsText": {"text": "foo", "matchCase": True},
            "replaceText": "bar",
        }
    }]

def test_insert_at_expands_to_insert_text():
    reqs = expand_ops([{"insert_at": 1, "text": "hello"}])
    assert reqs == [{
        "insertText": {"location": {"index": 1}, "text": "hello"}
    }]

def test_multiple_ops_preserve_order():
    reqs = expand_ops([
        {"insert_at": 1, "text": "a"},
        {"find": "x", "replace": "y"},
    ])
    assert reqs[0]["insertText"]["text"] == "a"
    assert reqs[1]["replaceAllText"]["replaceText"] == "y"

def test_unknown_op_raises():
    with pytest.raises(DocsOpError, match="unrecognized op"):
        expand_ops([{"bogus": 1}])

def test_empty_ops_returns_empty():
    assert expand_ops([]) == []
