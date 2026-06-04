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
    g = ScopeGuard(allowed_folder_ids=("M",), allowed_drive_ids=(), get_parents=get_parents, get_drive_id=lambda _id: None)
    g.assert_in_scope("M")  # no raise

def test_direct_child_in_scope():
    g = ScopeGuard(allowed_folder_ids=("M",), allowed_drive_ids=(), get_parents=get_parents, get_drive_id=lambda _id: None)
    g.assert_in_scope("file_in_M")

def test_deep_descendant_in_scope():
    g = ScopeGuard(allowed_folder_ids=("M",), allowed_drive_ids=(), get_parents=get_parents, get_drive_id=lambda _id: None)
    g.assert_in_scope("file1")

def test_unrelated_file_out_of_scope():
    g = ScopeGuard(allowed_folder_ids=("M",), allowed_drive_ids=(), get_parents=get_parents, get_drive_id=lambda _id: None)
    with pytest.raises(OutOfScopeError, match="not within the allowed folders"):
        g.assert_in_scope("x_file")

def test_folder_target_must_be_allowed_for_creation():
    g = ScopeGuard(allowed_folder_ids=("M",), allowed_drive_ids=(), get_parents=get_parents, get_drive_id=lambda _id: None)
    g.assert_folder_allowed("M")          # ok
    g.assert_folder_allowed("sub")        # descendant of M, ok
    with pytest.raises(OutOfScopeError):
        g.assert_folder_allowed("X")


# FIX 7 tests

def test_allowed_ids_property_returns_frozenset():
    g = ScopeGuard(allowed_folder_ids=("M", "N"), allowed_drive_ids=(), get_parents=get_parents, get_drive_id=lambda _id: None)
    ids = g.allowed_ids
    assert isinstance(ids, frozenset)
    assert ids == frozenset({"M", "N"})


def test_allowed_ids_property_is_public_not_private():
    """allowed_ids must be accessible as a property; _allowed remains internal."""
    g = ScopeGuard(allowed_folder_ids=("M",), allowed_drive_ids=(), get_parents=get_parents, get_drive_id=lambda _id: None)
    assert hasattr(g, "allowed_ids")
    assert g.allowed_ids == frozenset({"M"})


def test_get_parents_not_called_twice_for_same_node():
    """Each node's parents are fetched at most once (seen check before fetch)."""
    call_counts: dict = {}
    def counting_parents(fid):
        call_counts[fid] = call_counts.get(fid, 0) + 1
        return PARENTS.get(fid, [])

    g = ScopeGuard(allowed_folder_ids=("M",), allowed_drive_ids=(), get_parents=counting_parents, get_drive_id=lambda _id: None)
    g.assert_in_scope("file1")
    # sub and file1 should each be fetched exactly once
    for node in ("file1", "sub"):
        assert call_counts.get(node, 0) <= 1, \
            f"get_parents called {call_counts[node]} times for {node!r}"


# Task 3 — driveId rule tests

# get_drive_id stub alongside the existing get_parents fixture
DRIVE_OF = {"file1": "D1", "x_file": "DX", "file_in_M": None}
def get_drive_id(fid): return DRIVE_OF.get(fid)

def test_item_in_allowed_drive_is_in_scope():
    g = ScopeGuard(allowed_folder_ids=(), allowed_drive_ids=("D1",),
                   get_parents=get_parents, get_drive_id=get_drive_id)
    g.assert_in_scope("file1")  # driveId D1 → allowed, no raise

def test_item_in_other_drive_out_of_scope():
    g = ScopeGuard(allowed_folder_ids=(), allowed_drive_ids=("D1",),
                   get_parents=get_parents, get_drive_id=get_drive_id)
    with pytest.raises(OutOfScopeError):
        g.assert_in_scope("x_file")  # driveId DX → rejected

def test_folder_rule_still_works_alongside_drive_rule():
    g = ScopeGuard(allowed_folder_ids=("M",), allowed_drive_ids=("D1",),
                   get_parents=get_parents, get_drive_id=get_drive_id)
    g.assert_in_scope("file_in_M")  # ancestor M allowed (driveId None)

def test_drive_id_none_with_no_folder_ancestor_rejected():
    """driveId=None (personal My Drive share) with no allowed-folder ancestor must be rejected."""
    g = ScopeGuard(allowed_folder_ids=(), allowed_drive_ids=("D1",),
                   get_parents=get_parents, get_drive_id=lambda _id: None)
    with pytest.raises(OutOfScopeError):
        g.assert_in_scope("x_file")  # driveId None, no ancestor in allowed drives/folders

def test_empty_allowed_drives_never_matches():
    """Empty allowed-drives set must never allow any file, even with driveId set."""
    g = ScopeGuard(allowed_folder_ids=("M",), allowed_drive_ids=(),
                   get_parents=get_parents, get_drive_id=lambda _id: "D1")
    # driveId is D1, but allowed_drives is empty — must fall through to folder rule
    with pytest.raises(OutOfScopeError):
        g.assert_in_scope("x_file")  # not under M either
