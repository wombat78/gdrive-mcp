# gdrive-mcp — Trusted-Shared-Drive Scoping (ALLOWED_DRIVE_IDS) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Let the server scope access to one or more whole Shared Drives via a new `ALLOWED_DRIVE_IDS` env, so an agent dynamically sees any folder shared with its SA *inside* a trusted Shared Drive, while anything outside it (personal My Drive, other orgs) is rejected — closing the external-share / prompt-injection vector while removing the need to hardcode every folder ID.

**Architecture:** Extend the existing scope guard with a second, OR'd rule: an item is in scope if its `driveId` ∈ `ALLOWED_DRIVE_IDS` **or** an ancestor folder ∈ `ALLOWED_FOLDER_IDS` (existing). Add a `sharedWithMe`-based discovery path so `drive_list` with no folder returns the folders shared with the SA within the allowed drive(s). Fail closed on everything else. Backward compatible: `ALLOWED_FOLDER_IDS` still works; at least one of the two must be set.

**Tech Stack:** Python ≥3.11, google-api-python-client, gspread, mcp, pytest. Repo `qianqin/gdrive-mcp`, branch `feat/drive-id-scoping`. Use `.venv/bin/pytest` (uv not installed; the existing `.venv` has the deps). Google clients are always injected and mocked in unit tests.

Spec context: `docs/specs/2026-06-03-gdrive-mcp-server-design.md` (§8 security model). This plan extends it.

---

### Task 0: Branch + sanity baseline

- [ ] **Step 1:** `cd /Users/qian/development/gdrive-mcp && git checkout master && git checkout -b feat/drive-id-scoping`
- [ ] **Step 2:** Baseline green: `.venv/bin/pytest -q` → expect the existing suite (≈61 passed, 1 skipped). If red, report before continuing.
- [ ] **Step 3:** Commit the plan: `git add docs/plans/2026-06-04-allowed-drive-ids.md && git commit -m "docs: plan for ALLOWED_DRIVE_IDS scoping"`

---

### Task 1: Config — add `ALLOWED_DRIVE_IDS`, relax requirement

**Files:** Modify `src/gdrive_mcp/config.py`; Test `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_config.py`:
```python
def test_allowed_drive_ids_parsed():
    cfg = Config.from_env({"SERVICE_ACCOUNT_JSON": "{}", "ALLOWED_DRIVE_IDS": "D1, D2"})
    assert cfg.allowed_drive_ids == ("D1", "D2")
    assert cfg.allowed_folder_ids == ()  # folders optional when drives given

def test_folders_optional_when_drives_present():
    cfg = Config.from_env({"SERVICE_ACCOUNT_JSON": "{}", "ALLOWED_DRIVE_IDS": "D1"})
    assert cfg.allowed_drive_ids == ("D1",)

def test_requires_at_least_one_scope():
    import pytest
    with pytest.raises(ConfigError, match="ALLOWED_FOLDER_IDS or ALLOWED_DRIVE_IDS"):
        Config.from_env({"SERVICE_ACCOUNT_JSON": "{}"})

def test_folders_only_still_valid():
    cfg = Config.from_env({"SERVICE_ACCOUNT_JSON": "{}", "ALLOWED_FOLDER_IDS": "F1"})
    assert cfg.allowed_folder_ids == ("F1",)
    assert cfg.allowed_drive_ids == ()
```
Also update the existing `test_missing_folders_raises` test: it currently expects `ALLOWED_FOLDER_IDS` required with no drives — keep it but match the new message (`ALLOWED_FOLDER_IDS or ALLOWED_DRIVE_IDS`).

- [ ] **Step 2:** Run: `.venv/bin/pytest tests/test_config.py -v` → FAIL.

- [ ] **Step 3: Implement** in `src/gdrive_mcp/config.py`:
- Add field `allowed_drive_ids: tuple[str, ...] = ()` to the `Config` dataclass.
- In `from_env`, after parsing `folders`, parse drives the same way:
```python
raw_drives = env.get("ALLOWED_DRIVE_IDS", "").strip()
drives = tuple(d.strip() for d in raw_drives.split(",") if d.strip())
if not folders and not drives:
    raise ConfigError("ALLOWED_FOLDER_IDS or ALLOWED_DRIVE_IDS is required")
```
- Remove the old `if not folders:` hard-raise (folders alone OR drives alone is valid; but if `ALLOWED_FOLDER_IDS` is set yet yields no valid ids AND no drives, the combined check above still raises). Pass `allowed_drive_ids=drives` to the constructor.

- [ ] **Step 4:** Run: `.venv/bin/pytest tests/test_config.py -v` → PASS.
- [ ] **Step 5:** `git add -A && git commit -m "feat(config): ALLOWED_DRIVE_IDS + relax scope requirement"`

---

### Task 2: Drive helpers — file metadata (driveId) + shared-with-me listing

**Files:** Modify `src/gdrive_mcp/tools/drive.py`; Test `tests/test_drive.py`

- [ ] **Step 1: Write failing tests** (add to `tests/test_drive.py`):
```python
from gdrive_mcp.tools.drive import get_file_meta, list_shared_with_me

def test_get_file_meta_returns_parents_and_drive_id():
    drive = MagicMock()
    drive.files.return_value.get.return_value.execute.return_value = {"parents": ["P"], "driveId": "D1"}
    meta = get_file_meta(drive, "f1")
    assert meta == {"parents": ["P"], "driveId": "D1"}
    kw = drive.files.return_value.get.call_args.kwargs
    assert kw["fileId"] == "f1"
    assert kw["fields"] == "parents, driveId"
    assert kw["supportsAllDrives"] is True

def test_get_file_meta_missing_keys_defaults():
    drive = MagicMock()
    drive.files.return_value.get.return_value.execute.return_value = {}
    assert get_file_meta(drive, "f1") == {"parents": [], "driveId": None}

def test_list_shared_with_me_filters_to_allowed_drives():
    drive = MagicMock()
    drive.files.return_value.list.return_value.execute.return_value = {"files": [
        {"id": "a", "name": "InDrive", "mimeType": "application/vnd.google-apps.folder", "modifiedTime": "t", "driveId": "D1"},
        {"id": "b", "name": "Foreign", "mimeType": "application/vnd.google-apps.folder", "modifiedTime": "t", "driveId": "DX"},
        {"id": "c", "name": "MyDriveShare", "mimeType": "application/pdf", "modifiedTime": "t"},  # no driveId
    ]}
    out = list_shared_with_me(drive, allowed_drive_ids=("D1",))
    assert [f["id"] for f in out] == ["a"]   # only the one in D1
    q = drive.files.return_value.list.call_args.kwargs["q"]
    assert "sharedWithMe = true" in q and "trashed = false" in q
    assert drive.files.return_value.list.call_args.kwargs["includeItemsFromAllDrives"] is True
```

- [ ] **Step 2:** Run: `.venv/bin/pytest tests/test_drive.py -v` → FAIL.

- [ ] **Step 3: Implement** in `src/gdrive_mcp/tools/drive.py`:
```python
def get_file_meta(drive: Any, file_id: str) -> dict:
    m = (drive.files().get(fileId=file_id, fields="parents, driveId", supportsAllDrives=True).execute())
    return {"parents": m.get("parents", []), "driveId": m.get("driveId")}

def list_shared_with_me(drive: Any, allowed_drive_ids: tuple) -> list[dict]:
    resp = (drive.files().list(
        q="sharedWithMe = true and trashed = false",
        fields="files(id, name, mimeType, modifiedTime, driveId)",
        supportsAllDrives=True, includeItemsFromAllDrives=True, pageSize=200,
    ).execute())
    allowed = set(allowed_drive_ids)
    return [
        {k: f.get(k) for k in ("id", "name", "mimeType", "modifiedTime")}
        for f in resp.get("files", []) if f.get("driveId") in allowed
    ]
```
Keep the existing `get_parents` (used by the scope walk). Note: `get_file_meta` and `get_parents` can both exist; `get_parents` may be re-expressed as `get_file_meta(...)["parents"]` to avoid a second API shape, but keeping both is fine.

- [ ] **Step 4:** Run: `.venv/bin/pytest tests/test_drive.py -v` → PASS.
- [ ] **Step 5:** `git add -A && git commit -m "feat(drive): get_file_meta + list_shared_with_me"`

---

### Task 3: Scope guard — OR in the driveId rule

**Files:** Modify `src/gdrive_mcp/scope.py`; Test `tests/test_scope.py`

- [ ] **Step 1: Write failing tests** (add to `tests/test_scope.py`):
```python
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
```
Update the EXISTING `ScopeGuard(...)` constructions in `test_scope.py` to the new signature (`allowed_folder_ids=`, `allowed_drive_ids=()`, `get_parents=`, `get_drive_id=lambda _id: None`). Keep the existing folder-scope assertions intact.

- [ ] **Step 2:** Run: `.venv/bin/pytest tests/test_scope.py -v` → FAIL.

- [ ] **Step 3: Implement** in `src/gdrive_mcp/scope.py`:
- Constructor signature → `__init__(self, allowed_folder_ids, allowed_drive_ids, get_parents, get_drive_id)`. Store `self._allowed_folders=set(...)`, `self._allowed_drives=set(...)`, both callables. Keep `allowed_ids` property returning the folder set (rename internal use accordingly) and add `allowed_drive_ids` property returning the drive set.
- `_is_in_scope(file_id)`: first `if self._get_drive_id(file_id) in self._allowed_drives and self._allowed_drives: return True`. Otherwise the existing ancestor walk against `self._allowed_folders`.
- `assert_in_scope` / `assert_folder_allowed` unchanged in behavior (still call `_is_in_scope`). Note: rename the old `self._allowed` references to `self._allowed_folders` throughout.

- [ ] **Step 4:** Run: `.venv/bin/pytest tests/test_scope.py -v` → PASS.
- [ ] **Step 5:** `git add -A && git commit -m "feat(scope): allow items in trusted Shared Drives (driveId rule)"`

---

### Task 4: Service — wire driveId scoping + dynamic drive_list

**Files:** Modify `src/gdrive_mcp/service.py`; Test `tests/test_service.py`

- [ ] **Step 1: Write failing tests** (add to `tests/test_service.py`):
```python
from unittest.mock import patch
def _svc_drives(allowed_drives=("D1",), drive_of=None, parents=None):
    drive_of = drive_of or {"in": "D1", "out": "DX"}
    clients = MagicMock()
    svc = GDriveService(clients, allowed_folder_ids=(), allowed_drive_ids=allowed_drives)
    svc._guard._get_drive_id = lambda fid: drive_of.get(fid)
    svc._guard._get_parents = lambda fid: (parents or {}).get(fid, [])
    return svc, clients

def test_read_in_allowed_drive_ok():
    svc, _ = _svc_drives()
    with patch("gdrive_mcp.service.docs_read", return_value={"title":"t","text":"x"}) as mk:
        svc.docs_read(file_id="in")
    mk.assert_called_once()

def test_read_in_foreign_drive_blocked():
    svc, _ = _svc_drives()
    with patch("gdrive_mcp.service.docs_read") as mk:
        with pytest.raises(OutOfScopeError):
            svc.docs_read(file_id="out")
    mk.assert_not_called()

def test_drive_list_none_returns_shared_within_allowed_drive():
    svc, clients = _svc_drives()
    with patch("gdrive_mcp.service.list_shared_with_me", return_value=[{"id":"a","name":"Go-to-Market"}]) as mk:
        out = svc.drive_list(folder_id=None)
    mk.assert_called_once_with(clients.drive, ("D1",))
    assert out == [{"id":"a","name":"Go-to-Market"}]
```

- [ ] **Step 2:** Run: `.venv/bin/pytest tests/test_service.py -v` → FAIL.

- [ ] **Step 3: Implement** in `src/gdrive_mcp/service.py`:
- `__init__(self, clients, allowed_folder_ids, allowed_drive_ids=())`: build the guard with both rule sets and both lookups:
```python
self._guard = ScopeGuard(
    allowed_folder_ids=allowed_folder_ids,
    allowed_drive_ids=allowed_drive_ids,
    get_parents=lambda fid: get_parents(self._clients.drive, fid),
    get_drive_id=lambda fid: get_file_meta(self._clients.drive, fid)["driveId"],
)
```
- Update imports: `from gdrive_mcp.tools.drive import get_parents, get_file_meta, drive_list, list_shared_with_me`.
- `drive_list(self, folder_id=None, query=None)`:
```python
if folder_id:
    self._guard.assert_folder_allowed(folder_id)
    return drive_list(self._clients.drive, folder_id, query)
results = []
for f in self._guard.allowed_ids:                      # explicit folders
    results.extend(drive_list(self._clients.drive, f, query))
if self._guard.allowed_drive_ids:                      # trusted drives: dynamic discovery
    results.extend(list_shared_with_me(self._clients.drive, tuple(self._guard.allowed_drive_ids)))
return results
```
- All other methods unchanged (they already call `assert_in_scope` / `assert_folder_allowed`, which now also honor the drive rule).

- [ ] **Step 4:** Run: `.venv/bin/pytest tests/test_service.py -v` → PASS.
- [ ] **Step 5:** `git add -A && git commit -m "feat(service): driveId scoping + dynamic drive_list discovery"`

---

### Task 5: Entry point + README

**Files:** Modify `src/gdrive_mcp/__main__.py`, `README.md`

- [ ] **Step 1:** In `__main__.py`, pass the new config through:
`service = GDriveService(clients, cfg.allowed_folder_ids, cfg.allowed_drive_ids)`
- [ ] **Step 2:** README: document `ALLOWED_DRIVE_IDS` (comma-separated Shared Drive IDs; at least one of `ALLOWED_FOLDER_IDS`/`ALLOWED_DRIVE_IDS` required). Add a sentence: "When `ALLOWED_DRIVE_IDS` is set, the SA may access any item shared with it that resides in those Shared Drives; anything outside (personal My Drive, other orgs) is rejected — the anti-injection boundary."
- [ ] **Step 3:** Full suite: `.venv/bin/pytest -v` → all green (plus the 1 integration skip).
- [ ] **Step 4:** `git add -A && git commit -m "feat: wire ALLOWED_DRIVE_IDS through entry point + docs"`

---

### Task 6: Final review pass

- [ ] **Step 1:** `.venv/bin/pytest -v` green.
- [ ] **Step 2:** Confirm fail-closed: re-read `scope.py` — an item with `driveId=None` and no allowed-folder ancestor must be **rejected** (not allowed). The `and self._allowed_drives` guard prevents an empty allowed-drives set from ever matching `None`.
- [ ] **Step 3:** `git log --oneline` shows the Task 1–5 commits on `feat/drive-id-scoping`. Tree clean.

## Notes for the implementer
- Do NOT expose a raw "list everything shared with me" MCP tool — `drive_list` must always filter to allowed drives/folders. The whole point is that out-of-scope shares are unreadable (anti-injection).
- Backward compatibility: existing folder-only configs keep working (`allowed_drive_ids=()`), and the driveId rule is skipped when the allowed-drives set is empty.
- Fail closed everywhere: unknown driveId / None / API error → not in scope.
