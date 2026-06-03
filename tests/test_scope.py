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
