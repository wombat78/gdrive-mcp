import pytest
from gdrive_mcp.scope import ScopeGuard, OutOfScopeError

# Tree: allowed root "M" -> "sub" -> "file1"; "X" is unrelated.
PARENTS = {
    "sub": ["M"],
    "file1": ["sub"],
    "file_in_M": ["M"],
    "x_file": ["X"],
}

def get_parents(file_id):
    return PARENTS.get(file_id, [])

def test_allowed_folder_itself_in_scope():
    g = ScopeGuard(allowed=("M",), get_parents=get_parents)
    g.assert_in_scope("M")  # no raise

def test_direct_child_in_scope():
    g = ScopeGuard(allowed=("M",), get_parents=get_parents)
    g.assert_in_scope("file_in_M")

def test_deep_descendant_in_scope():
    g = ScopeGuard(allowed=("M",), get_parents=get_parents)
    g.assert_in_scope("file1")

def test_unrelated_file_out_of_scope():
    g = ScopeGuard(allowed=("M",), get_parents=get_parents)
    with pytest.raises(OutOfScopeError, match="not within the allowed folders"):
        g.assert_in_scope("x_file")

def test_folder_target_must_be_allowed_for_creation():
    g = ScopeGuard(allowed=("M",), get_parents=get_parents)
    g.assert_folder_allowed("M")          # ok
    g.assert_folder_allowed("sub")        # descendant of M, ok
    with pytest.raises(OutOfScopeError):
        g.assert_folder_allowed("X")


# FIX 7 tests

def test_allowed_ids_property_returns_frozenset():
    g = ScopeGuard(allowed=("M", "N"), get_parents=get_parents)
    ids = g.allowed_ids
    assert isinstance(ids, frozenset)
    assert ids == frozenset({"M", "N"})


def test_allowed_ids_property_is_public_not_private():
    """allowed_ids must be accessible as a property; _allowed remains internal."""
    g = ScopeGuard(allowed=("M",), get_parents=get_parents)
    assert hasattr(g, "allowed_ids")
    assert g.allowed_ids == frozenset({"M"})


def test_get_parents_not_called_twice_for_same_node():
    """Each node's parents are fetched at most once (seen check before fetch)."""
    call_counts: dict = {}
    def counting_parents(fid):
        call_counts[fid] = call_counts.get(fid, 0) + 1
        return PARENTS.get(fid, [])

    g = ScopeGuard(allowed=("M",), get_parents=counting_parents)
    g.assert_in_scope("file1")
    # sub and file1 should each be fetched exactly once
    for node in ("file1", "sub"):
        assert call_counts.get(node, 0) <= 1, \
            f"get_parents called {call_counts[node]} times for {node!r}"
