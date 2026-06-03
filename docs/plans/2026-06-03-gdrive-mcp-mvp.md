# gdrive-mcp MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a service-account-native MCP server that lets an AI agent list Drive files and create/read/edit Google Docs and Sheets within explicitly-shared folders, with no domain-wide delegation.

**Architecture:** A Python package `gdrive_mcp` exposing tools through the official MCP SDK (`FastMCP`) over streamable-HTTP at `/mcp`. Auth is a service-account JSON key (`google.oauth2.service_account`); the Google Drive v3 + Docs v1 clients come from `google-api-python-client`, Sheets via `gspread`. A scope guard rejects any operation whose target is not inside `ALLOWED_FOLDER_IDS` before any API call runs.

**Tech Stack:** Python ≥3.11, `mcp`, `google-api-python-client`, `google-auth`, `gspread`, `pytest`, `uv`.

Spec: `docs/specs/2026-06-03-gdrive-mcp-server-design.md`.

**Conventions for every task:** all Drive/Docs API calls pass `supportsAllDrives=True` (and `includeItemsFromAllDrives=True` on list) so Shared Drives work. Google clients are always injected into functions/classes (never constructed inside the unit under test) so tests mock them with `unittest.mock.MagicMock`. No network in unit tests.

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/gdrive_mcp/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Write the failing test**

`tests/test_smoke.py`:
```python
def test_package_imports():
    import gdrive_mcp
    assert gdrive_mcp.__version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gdrive_mcp'`

- [ ] **Step 3: Write minimal implementation**

`pyproject.toml`:
```toml
[project]
name = "gdrive-mcp"
version = "0.1.0"
description = "Service-account-native MCP server for Google Drive, Docs, and Sheets"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.2.0",
    "google-api-python-client>=2.120.0",
    "google-auth>=2.28.0",
    "gspread>=6.0.0",
]

[project.scripts]
gdrive-mcp = "gdrive_mcp.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/gdrive_mcp"]

[dependency-groups]
dev = ["pytest>=8.0.0"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

`src/gdrive_mcp/__init__.py`:
```python
__version__ = "0.1.0"
```

`tests/__init__.py`: empty file.

`.gitignore`:
```
__pycache__/
*.pyc
.venv/
.pytest_cache/
*.egg-info/
dist/
service-account*.json
```

`README.md`:
```markdown
# gdrive-mcp

Service-account-native MCP server for Google Drive, Docs, and Sheets. No domain-wide delegation — access is granted by sharing folders with the service account.

See `docs/specs/` for the design and `docs/plans/` for the build plan.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src tests .gitignore README.md
git commit -m "chore: scaffold gdrive-mcp package"
```

---

### Task 2: Config parsing

Parse environment into a frozen `Config`. Supports `SERVICE_ACCOUNT_JSON` (inline) or `SERVICE_ACCOUNT_PATH` (file); requires `ALLOWED_FOLDER_IDS`.

**Files:**
- Create: `src/gdrive_mcp/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
import json
import pytest
from gdrive_mcp.config import Config, ConfigError

def test_inline_json_and_folders():
    cfg = Config.from_env({
        "SERVICE_ACCOUNT_JSON": '{"type": "service_account"}',
        "ALLOWED_FOLDER_IDS": "abc, def",
    })
    assert cfg.service_account_info == {"type": "service_account"}
    assert cfg.allowed_folder_ids == ("abc", "def")
    assert cfg.port == 8080
    assert cfg.host == "0.0.0.0"

def test_path_is_read(tmp_path):
    p = tmp_path / "sa.json"
    p.write_text(json.dumps({"type": "service_account", "k": 1}))
    cfg = Config.from_env({
        "SERVICE_ACCOUNT_PATH": str(p),
        "ALLOWED_FOLDER_IDS": "abc",
        "GDRIVE_MCP_PORT": "9000",
    })
    assert cfg.service_account_info["k"] == 1
    assert cfg.port == 9000

def test_missing_creds_raises():
    with pytest.raises(ConfigError, match="SERVICE_ACCOUNT"):
        Config.from_env({"ALLOWED_FOLDER_IDS": "abc"})

def test_missing_folders_raises():
    with pytest.raises(ConfigError, match="ALLOWED_FOLDER_IDS"):
        Config.from_env({"SERVICE_ACCOUNT_JSON": "{}"})

def test_enabled_tools_default_none_means_all():
    cfg = Config.from_env({"SERVICE_ACCOUNT_JSON": "{}", "ALLOWED_FOLDER_IDS": "a"})
    assert cfg.enabled_tools is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gdrive_mcp.config'`

- [ ] **Step 3: Write minimal implementation**

`src/gdrive_mcp/config.py`:
```python
from __future__ import annotations
import json
import os
from dataclasses import dataclass


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    service_account_info: dict
    allowed_folder_ids: tuple[str, ...]
    host: str = "0.0.0.0"
    port: int = 8080
    enabled_tools: tuple[str, ...] | None = None

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Config":
        env = dict(os.environ if env is None else env)

        if env.get("SERVICE_ACCOUNT_JSON"):
            info = json.loads(env["SERVICE_ACCOUNT_JSON"])
        elif env.get("SERVICE_ACCOUNT_PATH"):
            with open(env["SERVICE_ACCOUNT_PATH"], encoding="utf-8") as fh:
                info = json.load(fh)
        else:
            raise ConfigError("SERVICE_ACCOUNT_JSON or SERVICE_ACCOUNT_PATH is required")

        raw_folders = env.get("ALLOWED_FOLDER_IDS", "").strip()
        if not raw_folders:
            raise ConfigError("ALLOWED_FOLDER_IDS is required")
        folders = tuple(f.strip() for f in raw_folders.split(",") if f.strip())

        tools_raw = env.get("ENABLED_TOOLS", "").strip()
        enabled = tuple(t.strip() for t in tools_raw.split(",") if t.strip()) or None

        return cls(
            service_account_info=info,
            allowed_folder_ids=folders,
            host=env.get("GDRIVE_MCP_HOST", "0.0.0.0"),
            port=int(env.get("GDRIVE_MCP_PORT", "8080")),
            enabled_tools=enabled,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/gdrive_mcp/config.py tests/test_config.py
git commit -m "feat: env-based config parsing"
```

---

### Task 3: Auth — build Google service clients

Load SA credentials and build Drive/Docs clients + a gspread client. Pure factory with no network (the Google libs don't hit the network until a request is made).

**Files:**
- Create: `src/gdrive_mcp/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write the failing test**

`tests/test_auth.py`:
```python
from unittest.mock import patch, MagicMock
from gdrive_mcp.auth import SCOPES, build_clients

def test_build_clients_uses_scopes_and_returns_three():
    fake_creds = MagicMock()
    with patch("gdrive_mcp.auth.service_account.Credentials.from_service_account_info",
               return_value=fake_creds) as mk_creds, \
         patch("gdrive_mcp.auth.build") as mk_build, \
         patch("gdrive_mcp.auth.gspread.authorize") as mk_gspread:
        clients = build_clients({"type": "service_account"})

        mk_creds.assert_called_once()
        assert mk_creds.call_args.kwargs["scopes"] == list(SCOPES)
        assert mk_build.call_args_list[0].args == ("drive", "v3")
        assert mk_build.call_args_list[1].args == ("docs", "v1")
        mk_gspread.assert_called_once_with(fake_creds)
        assert clients.drive is not None
        assert clients.docs is not None
        assert clients.sheets is not None

def test_scopes_are_the_three_expected():
    assert SCOPES == (
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/spreadsheets",
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gdrive_mcp.auth'`

- [ ] **Step 3: Write minimal implementation**

`src/gdrive_mcp/auth.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = (
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
)


@dataclass(frozen=True)
class Clients:
    drive: Any
    docs: Any
    sheets: Any  # gspread.Client


def build_clients(service_account_info: dict) -> Clients:
    creds = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=list(SCOPES)
    )
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    docs = build("docs", "v1", credentials=creds, cache_discovery=False)
    sheets = gspread.authorize(creds)
    return Clients(drive=drive, docs=docs, sheets=sheets)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_auth.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/gdrive_mcp/auth.py tests/test_auth.py
git commit -m "feat: service-account client factory"
```

---

### Task 4: Scope guard

Reject any file/folder outside the allowed folders. Ancestry is resolved via an injected `get_parents(file_id) -> list[str]` callable (the real one calls Drive `files.get`), keeping the logic unit-testable without network.

**Files:**
- Create: `src/gdrive_mcp/scope.py`
- Test: `tests/test_scope.py`

- [ ] **Step 1: Write the failing test**

`tests/test_scope.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_scope.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gdrive_mcp.scope'`

- [ ] **Step 3: Write minimal implementation**

`src/gdrive_mcp/scope.py`:
```python
from __future__ import annotations
from typing import Callable, Iterable


class OutOfScopeError(Exception):
    """Raised when a target file/folder is outside the allowed folders."""


class ScopeGuard:
    def __init__(self, allowed: Iterable[str], get_parents: Callable[[str], list[str]]):
        self._allowed = set(allowed)
        self._get_parents = get_parents

    def _is_in_scope(self, file_id: str) -> bool:
        # BFS up the parent chain; cap depth to avoid cycles/runaways.
        seen: set[str] = set()
        frontier = [file_id]
        for _ in range(50):
            if not frontier:
                break
            node = frontier.pop()
            if node in self._allowed:
                return True
            if node in seen:
                continue
            seen.add(node)
            frontier.extend(self._get_parents(node))
        return False

    def assert_in_scope(self, file_id: str) -> None:
        if not self._is_in_scope(file_id):
            raise OutOfScopeError(
                f"'{file_id}' is not within the allowed folders {sorted(self._allowed)}"
            )

    # Creation target: the destination folder must itself be in scope.
    assert_folder_allowed = assert_in_scope
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_scope.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/gdrive_mcp/scope.py tests/test_scope.py
git commit -m "feat: folder scope guard"
```

---

### Task 5: docs_edit op expansion (pure logic)

Convert friendly `ops` into raw Docs `batchUpdate` requests. This is the trickiest pure logic, so it gets its own task before any tool wiring.

**Files:**
- Create: `src/gdrive_mcp/docs_ops.py`
- Test: `tests/test_docs_ops.py`

- [ ] **Step 1: Write the failing test**

`tests/test_docs_ops.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_docs_ops.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gdrive_mcp.docs_ops'`

- [ ] **Step 3: Write minimal implementation**

`src/gdrive_mcp/docs_ops.py`:
```python
from __future__ import annotations


class DocsOpError(Exception):
    """Raised when a friendly op cannot be expanded."""


def expand_ops(ops: list[dict]) -> list[dict]:
    requests: list[dict] = []
    for op in ops:
        if "find" in op and "replace" in op:
            requests.append({
                "replaceAllText": {
                    "containsText": {"text": op["find"], "matchCase": True},
                    "replaceText": op["replace"],
                }
            })
        elif "insert_at" in op and "text" in op:
            requests.append({
                "insertText": {
                    "location": {"index": op["insert_at"]},
                    "text": op["text"],
                }
            })
        else:
            raise DocsOpError(f"unrecognized op: {op!r}")
    return requests
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_docs_ops.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/gdrive_mcp/docs_ops.py tests/test_docs_ops.py
git commit -m "feat: docs_edit friendly-op expansion"
```

---

### Task 6: Drive service helpers (parents + drive_list)

Real `get_parents` (wraps Drive `files.get`) and `drive_list`. Drive client is injected and mocked in tests.

**Files:**
- Create: `src/gdrive_mcp/tools/__init__.py` (empty)
- Create: `src/gdrive_mcp/tools/drive.py`
- Test: `tests/test_drive.py`

- [ ] **Step 1: Write the failing test**

`tests/test_drive.py`:
```python
from unittest.mock import MagicMock
from gdrive_mcp.tools.drive import get_parents, drive_list

def _drive_with_get(result):
    drive = MagicMock()
    drive.files.return_value.get.return_value.execute.return_value = result
    return drive

def test_get_parents_returns_parent_list():
    drive = _drive_with_get({"parents": ["P1", "P2"]})
    assert get_parents(drive, "f1") == ["P1", "P2"]
    drive.files.return_value.get.assert_called_once()
    kwargs = drive.files.return_value.get.call_args.kwargs
    assert kwargs["fileId"] == "f1"
    assert kwargs["fields"] == "parents"
    assert kwargs["supportsAllDrives"] is True

def test_get_parents_missing_key_returns_empty():
    drive = _drive_with_get({})
    assert get_parents(drive, "root") == []

def test_drive_list_maps_files_and_scopes_query():
    drive = MagicMock()
    drive.files.return_value.list.return_value.execute.return_value = {
        "files": [{"id": "1", "name": "a", "mimeType": "m", "modifiedTime": "t"}]
    }
    out = drive_list(drive, folder_id="M", query="budget")
    assert out == [{"id": "1", "name": "a", "mimeType": "m", "modifiedTime": "t"}]
    kwargs = drive.files.return_value.list.call_args.kwargs
    assert "'M' in parents" in kwargs["q"]
    assert "name contains 'budget'" in kwargs["q"]
    assert kwargs["supportsAllDrives"] is True
    assert kwargs["includeItemsFromAllDrives"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_drive.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gdrive_mcp.tools.drive'`

- [ ] **Step 3: Write minimal implementation**

`src/gdrive_mcp/tools/__init__.py`: empty file.

`src/gdrive_mcp/tools/drive.py`:
```python
from __future__ import annotations
from typing import Any

_FIELDS = "files(id, name, mimeType, modifiedTime)"


def get_parents(drive: Any, file_id: str) -> list[str]:
    meta = (
        drive.files()
        .get(fileId=file_id, fields="parents", supportsAllDrives=True)
        .execute()
    )
    return meta.get("parents", [])


def drive_list(drive: Any, folder_id: str, query: str | None = None) -> list[dict]:
    q = f"'{folder_id}' in parents and trashed = false"
    if query:
        safe = query.replace("'", "\\'")
        q += f" and name contains '{safe}'"
    resp = (
        drive.files()
        .list(
            q=q,
            fields=_FIELDS,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=100,
        )
        .execute()
    )
    return resp.get("files", [])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_drive.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/gdrive_mcp/tools/__init__.py src/gdrive_mcp/tools/drive.py tests/test_drive.py
git commit -m "feat: drive get_parents + drive_list"
```

---

### Task 7: Docs tools (create / read / edit)

**Files:**
- Create: `src/gdrive_mcp/tools/docs.py`
- Test: `tests/test_docs.py`

- [ ] **Step 1: Write the failing test**

`tests/test_docs.py`:
```python
from unittest.mock import MagicMock
import pytest
from gdrive_mcp.tools.docs import docs_create, docs_read, docs_edit
from gdrive_mcp.docs_ops import DocsOpError

def test_docs_create_uses_drive_files_create_in_folder():
    drive = MagicMock()
    drive.files.return_value.create.return_value.execute.return_value = {"id": "D1"}
    out = docs_create(drive, title="Plan", folder_id="M")
    body = drive.files.return_value.create.call_args.kwargs["body"]
    assert body["name"] == "Plan"
    assert body["mimeType"] == "application/vnd.google-apps.document"
    assert body["parents"] == ["M"]
    assert out == {"id": "D1", "url": "https://docs.google.com/document/d/D1/edit"}

def test_docs_read_concatenates_paragraph_text():
    docs = MagicMock()
    docs.documents.return_value.get.return_value.execute.return_value = {
        "title": "T",
        "body": {"content": [
            {"paragraph": {"elements": [
                {"textRun": {"content": "Hello "}},
                {"textRun": {"content": "world"}},
            ]}},
        ]},
    }
    out = docs_read(docs, "D1")
    assert out["title"] == "T"
    assert out["text"] == "Hello world"

def test_docs_edit_expands_ops_and_calls_batch_update():
    docs = MagicMock()
    docs.documents.return_value.batchUpdate.return_value.execute.return_value = {}
    out = docs_edit(docs, "D1", ops=[{"find": "a", "replace": "b"}], requests=None)
    kwargs = docs.documents.return_value.batchUpdate.call_args.kwargs
    assert kwargs["documentId"] == "D1"
    assert kwargs["body"]["requests"][0]["replaceAllText"]["replaceText"] == "b"
    assert out == {"applied": 1}

def test_docs_edit_passes_raw_requests_after_ops():
    docs = MagicMock()
    docs.documents.return_value.batchUpdate.return_value.execute.return_value = {}
    raw = [{"insertText": {"location": {"index": 1}, "text": "z"}}]
    out = docs_edit(docs, "D1", ops=[{"find": "a", "replace": "b"}], requests=raw)
    reqs = docs.documents.return_value.batchUpdate.call_args.kwargs["body"]["requests"]
    assert len(reqs) == 2
    assert "replaceAllText" in reqs[0]
    assert "insertText" in reqs[1]
    assert out == {"applied": 2}

def test_docs_edit_requires_at_least_one():
    docs = MagicMock()
    with pytest.raises(ValueError, match="ops or requests"):
        docs_edit(docs, "D1", ops=None, requests=None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_docs.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gdrive_mcp.tools.docs'`

- [ ] **Step 3: Write minimal implementation**

`src/gdrive_mcp/tools/docs.py`:
```python
from __future__ import annotations
from typing import Any

from gdrive_mcp.docs_ops import expand_ops

_DOC_MIME = "application/vnd.google-apps.document"


def docs_create(drive: Any, title: str, folder_id: str) -> dict:
    meta = (
        drive.files()
        .create(
            body={"name": title, "mimeType": _DOC_MIME, "parents": [folder_id]},
            fields="id",
            supportsAllDrives=True,
        )
        .execute()
    )
    doc_id = meta["id"]
    return {"id": doc_id, "url": f"https://docs.google.com/document/d/{doc_id}/edit"}


def docs_read(docs: Any, file_id: str) -> dict:
    doc = docs.documents().get(documentId=file_id).execute()
    parts: list[str] = []
    for element in doc.get("body", {}).get("content", []):
        para = element.get("paragraph")
        if not para:
            continue
        for run in para.get("elements", []):
            text_run = run.get("textRun")
            if text_run:
                parts.append(text_run.get("content", ""))
    return {"title": doc.get("title", ""), "text": "".join(parts)}


def docs_edit(
    docs: Any,
    file_id: str,
    ops: list[dict] | None = None,
    requests: list[dict] | None = None,
) -> dict:
    if not ops and not requests:
        raise ValueError("docs_edit requires at least one of ops or requests")
    payload: list[dict] = []
    if ops:
        payload.extend(expand_ops(ops))
    if requests:
        payload.extend(requests)
    docs.documents().batchUpdate(
        documentId=file_id, body={"requests": payload}
    ).execute()
    return {"applied": len(payload)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_docs.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/gdrive_mcp/tools/docs.py tests/test_docs.py
git commit -m "feat: docs create/read/edit tools"
```

---

### Task 8: Sheets tools (create / read / update / append)

Uses `gspread`. The gspread client and spreadsheet objects are injected/mocked.

**Files:**
- Create: `src/gdrive_mcp/tools/sheets.py`
- Test: `tests/test_sheets.py`

- [ ] **Step 1: Write the failing test**

`tests/test_sheets.py`:
```python
from unittest.mock import MagicMock
from gdrive_mcp.tools.sheets import sheets_create, sheets_read, sheets_update, sheets_append

def test_sheets_create_in_folder_returns_id_and_url():
    gc = MagicMock()
    gc.create.return_value.id = "S1"
    out = sheets_create(gc, title="Q1", folder_id="M")
    gc.create.assert_called_once_with("Q1", folder_id="M")
    assert out == {"id": "S1", "url": "https://docs.google.com/spreadsheets/d/S1/edit"}

def test_sheets_read_returns_values():
    gc = MagicMock()
    ws = gc.open_by_key.return_value.sheet1
    ws.get.return_value = [["a", "b"], ["1", "2"]]
    out = sheets_read(gc, "S1", "A1:B2")
    gc.open_by_key.assert_called_once_with("S1")
    ws.get.assert_called_once_with("A1:B2")
    assert out == {"values": [["a", "b"], ["1", "2"]]}

def test_sheets_update_writes_range():
    gc = MagicMock()
    ws = gc.open_by_key.return_value.sheet1
    ws.update.return_value = {"updatedCells": 4}
    out = sheets_update(gc, "S1", "A1:B2", [["a", "b"], ["1", "2"]])
    ws.update.assert_called_once_with("A1:B2", [["a", "b"], ["1", "2"]])
    assert out == {"updatedCells": 4}

def test_sheets_append_adds_rows():
    gc = MagicMock()
    ws = gc.open_by_key.return_value.sheet1
    ws.append_rows.return_value = {"updates": {"updatedRows": 2}}
    out = sheets_append(gc, "S1", [["x"], ["y"]])
    ws.append_rows.assert_called_once_with([["x"], ["y"]])
    assert out == {"updates": {"updatedRows": 2}}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sheets.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gdrive_mcp.tools.sheets'`

- [ ] **Step 3: Write minimal implementation**

`src/gdrive_mcp/tools/sheets.py`:
```python
from __future__ import annotations
from typing import Any


def _url(sheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"


def sheets_create(gc: Any, title: str, folder_id: str) -> dict:
    spreadsheet = gc.create(title, folder_id=folder_id)
    return {"id": spreadsheet.id, "url": _url(spreadsheet.id)}


def sheets_read(gc: Any, file_id: str, range: str) -> dict:
    ws = gc.open_by_key(file_id).sheet1
    return {"values": ws.get(range)}


def sheets_update(gc: Any, file_id: str, range: str, values: list[list]) -> dict:
    ws = gc.open_by_key(file_id).sheet1
    result = ws.update(range, values)
    return {"updatedCells": result.get("updatedCells")}


def sheets_append(gc: Any, file_id: str, values: list[list]) -> dict:
    ws = gc.open_by_key(file_id).sheet1
    result = ws.append_rows(values)
    return {"updates": result.get("updates")}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sheets.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/gdrive_mcp/tools/sheets.py tests/test_sheets.py
git commit -m "feat: sheets create/read/update/append tools"
```

---

### Task 9: Service layer — wire scope guard into every tool

A `GDriveService` holds `Clients` + `ScopeGuard` and is the single entry point the MCP layer calls. It enforces scope before delegating to the tool functions. This is where create-target and existing-file checks live.

**Files:**
- Create: `src/gdrive_mcp/service.py`
- Test: `tests/test_service.py`

- [ ] **Step 1: Write the failing test**

`tests/test_service.py`:
```python
from unittest.mock import MagicMock, patch
import pytest
from gdrive_mcp.service import GDriveService
from gdrive_mcp.scope import OutOfScopeError

def _service(allowed=("M",), parents=None):
    parents = parents or {"D_in": ["M"], "D_out": ["X"]}
    clients = MagicMock()
    svc = GDriveService(clients, allowed_folder_ids=allowed)
    # stub parent resolution used by the scope guard
    svc._guard._get_parents = lambda fid: parents.get(fid, [])
    return svc, clients

def test_create_into_allowed_folder_ok():
    svc, clients = _service()
    with patch("gdrive_mcp.service.docs_create", return_value={"id": "D1", "url": "u"}) as mk:
        out = svc.docs_create(title="t", folder_id="M")
    mk.assert_called_once()
    assert out["id"] == "D1"

def test_create_into_foreign_folder_blocked():
    svc, _ = _service()
    with pytest.raises(OutOfScopeError):
        svc.docs_create(title="t", folder_id="X")

def test_edit_existing_out_of_scope_blocked_before_api():
    svc, clients = _service()
    with patch("gdrive_mcp.service.docs_edit") as mk:
        with pytest.raises(OutOfScopeError):
            svc.docs_edit(file_id="D_out", ops=[{"find": "a", "replace": "b"}])
    mk.assert_not_called()

def test_edit_existing_in_scope_calls_tool():
    svc, clients = _service()
    with patch("gdrive_mcp.service.docs_edit", return_value={"applied": 1}) as mk:
        out = svc.docs_edit(file_id="D_in", ops=[{"find": "a", "replace": "b"}])
    mk.assert_called_once()
    assert out == {"applied": 1}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gdrive_mcp.service'`

- [ ] **Step 3: Write minimal implementation**

`src/gdrive_mcp/service.py`:
```python
from __future__ import annotations
from typing import Any

from gdrive_mcp.auth import Clients
from gdrive_mcp.scope import ScopeGuard
from gdrive_mcp.tools.drive import get_parents, drive_list
from gdrive_mcp.tools.docs import docs_create, docs_read, docs_edit
from gdrive_mcp.tools.sheets import (
    sheets_create, sheets_read, sheets_update, sheets_append,
)


class GDriveService:
    def __init__(self, clients: Clients, allowed_folder_ids: tuple[str, ...]):
        self._clients = clients
        self._guard = ScopeGuard(
            allowed=allowed_folder_ids,
            get_parents=lambda fid: get_parents(self._clients.drive, fid),
        )

    # --- Drive ---
    def drive_list(self, folder_id: str | None = None, query: str | None = None) -> list[dict]:
        folders = [folder_id] if folder_id else list(self._guard._allowed)
        results: list[dict] = []
        for f in folders:
            self._guard.assert_folder_allowed(f)
            results.extend(drive_list(self._clients.drive, f, query))
        return results

    # --- Docs ---
    def docs_create(self, title: str, folder_id: str) -> dict:
        self._guard.assert_folder_allowed(folder_id)
        return docs_create(self._clients.drive, title, folder_id)

    def docs_read(self, file_id: str) -> dict:
        self._guard.assert_in_scope(file_id)
        return docs_read(self._clients.docs, file_id)

    def docs_edit(self, file_id: str, ops=None, requests=None) -> dict:
        self._guard.assert_in_scope(file_id)
        return docs_edit(self._clients.docs, file_id, ops=ops, requests=requests)

    # --- Sheets ---
    def sheets_create(self, title: str, folder_id: str) -> dict:
        self._guard.assert_folder_allowed(folder_id)
        return sheets_create(self._clients.sheets, title, folder_id)

    def sheets_read(self, file_id: str, range: str) -> dict:
        self._guard.assert_in_scope(file_id)
        return sheets_read(self._clients.sheets, file_id, range)

    def sheets_update(self, file_id: str, range: str, values: list[list]) -> dict:
        self._guard.assert_in_scope(file_id)
        return sheets_update(self._clients.sheets, file_id, range, values)

    def sheets_append(self, file_id: str, values: list[list]) -> dict:
        self._guard.assert_in_scope(file_id)
        return sheets_append(self._clients.sheets, file_id, values)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_service.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/gdrive_mcp/service.py tests/test_service.py
git commit -m "feat: GDriveService enforces scope on every op"
```

---

### Task 10: MCP server wiring + entry point

Register the 8 tools on a `FastMCP` instance, honoring `ENABLED_TOOLS`, and run over streamable-HTTP at `/mcp`. The registration function is unit-tested by inspecting registered tool names; `main()` is thin.

**Files:**
- Create: `src/gdrive_mcp/server.py`
- Create: `src/gdrive_mcp/__main__.py`
- Test: `tests/test_server.py`

- [ ] **Step 1: Write the failing test**

`tests/test_server.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_server.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gdrive_mcp.server'`

- [ ] **Step 3: Write minimal implementation**

`src/gdrive_mcp/server.py`:
```python
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
```

`src/gdrive_mcp/__main__.py`:
```python
from __future__ import annotations

from gdrive_mcp.config import Config
from gdrive_mcp.auth import build_clients
from gdrive_mcp.service import GDriveService
from gdrive_mcp.server import build_mcp


def main() -> None:
    cfg = Config.from_env()
    clients = build_clients(cfg.service_account_info)
    service = GDriveService(clients, cfg.allowed_folder_ids)
    mcp = build_mcp(service, cfg.enabled_tools, host=cfg.host, port=cfg.port)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_server.py -v`
Expected: PASS (3 tests)

> If the installed `mcp` version exposes a different internal accessor than `_tool_manager.list_tools()` / `get_tool()`, adjust the test to the available public API (e.g. `await mcp.list_tools()`), keeping the same assertions about tool names and delegation. Do not change `server.py` to satisfy a private API.

- [ ] **Step 5: Commit**

```bash
git add src/gdrive_mcp/server.py src/gdrive_mcp/__main__.py tests/test_server.py
git commit -m "feat: MCP tool registration + entry point"
```

---

### Task 11: Full suite + Dockerfile + README usage

**Files:**
- Create: `Dockerfile`
- Modify: `README.md`

- [ ] **Step 1: Run the whole suite green**

Run: `uv run pytest -v`
Expected: PASS — all tests from Tasks 1–10.

- [ ] **Step 2: Write the Dockerfile**

`Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8080
# Config via env: SERVICE_ACCOUNT_JSON|SERVICE_ACCOUNT_PATH, ALLOWED_FOLDER_IDS, GDRIVE_MCP_PORT
CMD ["gdrive-mcp"]
```

- [ ] **Step 3: Verify the image builds**

Run: `docker build -t gdrive-mcp:dev .`
Expected: build succeeds; final image present in `docker images`.

- [ ] **Step 4: Expand the README**

Append to `README.md`:
```markdown
## Configuration

| Env var | Required | Meaning |
|---|---|---|
| `SERVICE_ACCOUNT_JSON` / `SERVICE_ACCOUNT_PATH` | yes (one) | Service-account credentials (inline JSON or file path) |
| `ALLOWED_FOLDER_IDS` | yes | Comma-separated Drive folder IDs the server may operate within |
| `GDRIVE_MCP_PORT` | no (8080) | HTTP listen port |
| `GDRIVE_MCP_HOST` | no (0.0.0.0) | Bind address |
| `ENABLED_TOOLS` | no (all) | Comma-separated allow-list of tool names |

Grant access by sharing the target folder(s) with the service account's email
(`client_email` in the JSON) as **Contributor** on the Shared Drive. No
domain-wide delegation required.

## Tools

`drive_list`, `docs_create`, `docs_read`, `docs_edit`, `sheets_create`,
`sheets_read`, `sheets_update`, `sheets_append`.

## Run

```bash
SERVICE_ACCOUNT_PATH=./sa.json ALLOWED_FOLDER_IDS=<folder-id> gdrive-mcp
# serves MCP over streamable-HTTP at http://localhost:8080/mcp
```
```

- [ ] **Step 5: Commit**

```bash
git add Dockerfile README.md
git commit -m "chore: Dockerfile + usage docs"
```

---

### Task 12: Integration test (opt-in, gated on creds)

A single end-to-end test, skipped unless real credentials are present, that creates+reads+edits a Doc and a Sheet in a real test folder.

**Files:**
- Create: `tests/integration/test_live.py`

- [ ] **Step 1: Write the gated test**

`tests/integration/test_live.py`:
```python
import os
import pytest

pytestmark = pytest.mark.skipif(
    not (os.getenv("GDRIVE_TEST_SA_PATH") and os.getenv("GDRIVE_TEST_FOLDER_ID")),
    reason="set GDRIVE_TEST_SA_PATH and GDRIVE_TEST_FOLDER_ID to run live integration",
)

def test_doc_and_sheet_roundtrip():
    import json
    from gdrive_mcp.auth import build_clients
    from gdrive_mcp.service import GDriveService

    info = json.load(open(os.environ["GDRIVE_TEST_SA_PATH"]))
    folder = os.environ["GDRIVE_TEST_FOLDER_ID"]
    svc = GDriveService(build_clients(info), (folder,))

    doc = svc.docs_create(title="gdrive-mcp itest", folder_id=folder)
    svc.docs_edit(file_id=doc["id"], ops=[{"insert_at": 1, "text": "hello"}])
    assert "hello" in svc.docs_read(file_id=doc["id"])["text"]

    sheet = svc.sheets_create(title="gdrive-mcp itest", folder_id=folder)
    svc.sheets_update(file_id=sheet["id"], range="A1:B1", values=[["a", "b"]])
    assert svc.sheets_read(file_id=sheet["id"], range="A1:B1")["values"] == [["a", "b"]]
```

- [ ] **Step 2: Verify it skips cleanly without creds**

Run: `uv run pytest tests/integration -v`
Expected: SKIPPED (reason shown). No failure.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_live.py
git commit -m "test: opt-in live integration roundtrip"
```

---

## Notes for the implementer

- Use `uv` for everything (`uv run pytest`, `uv sync`). If `uv` is unavailable, fall back to a venv + `pip install -e ".[dev]"` and plain `pytest`.
- Never construct Google clients inside a unit-tested function — they're always passed in, so tests stay offline.
- The scope guard is the security boundary; never bypass it in the service layer. Every method that takes a `file_id` calls `assert_in_scope` first; every create takes a `folder_id` and calls `assert_folder_allowed` first.
- `range` shadows no behavior we rely on; it mirrors the Sheets API naming. Keep it.

## Deliberately deferred (relative to spec §7)

Spec §7 calls for uniform Google-API error mapping with retry/backoff on 429/5xx. The MVP **defers** this: `ConfigError`, `OutOfScopeError`, and `DocsOpError` are raised with clear messages (covered by tasks), and raw `googleapiclient.errors.HttpError` propagates with its Google reason intact (still actionable). A `errors.py` with a `with_retry`/`map_google_errors` decorator wrapping the service-layer calls is the first fast-follow task after MVP — valuable because rate-limited APIs + retrying agents can otherwise storm. Tracked, not forgotten.
