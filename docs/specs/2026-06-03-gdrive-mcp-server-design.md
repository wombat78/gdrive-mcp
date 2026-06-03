# gdrive-mcp — Service-Account-Native Google Drive/Docs/Sheets MCP Server

**Date:** 2026-06-03
**Status:** Design — pending review
**Project:** A of 2 (server). Project B = "Sarah" agent integration, specced separately, depends on this.
**Target repo:** dedicated new repo (e.g. `qianqin/gdrive-mcp`). This spec lives in `solarmatrix/agents` during planning and moves to the new repo at implementation time.

---

## 1. Purpose

A standalone MCP server that lets AI agents read, create, and edit Google **Docs**, **Sheets**, and **Drive** files using a **Google Cloud service account** — authenticated by **sharing specific folders with the service account**, with **no domain-wide delegation (DWD)**.

It exists because no popular off-the-shelf MCP server does headless service-account Docs+Sheets without DWD:
- The SA-native ones (e.g. `xing5/mcp-google-sheets`) are Sheets-only.
- The Docs-capable ones (e.g. `piotr-agier/google-drive-mcp`) are OAuth/browser-based or require DWD.

First consumer is the SolarMatrix agent fleet (the "Sarah" sales/marketing agent), but the server is intended to be general-purpose and grow toward broad Google Drive API coverage.

## 2. Scope

**MVP (this spec) — ~8 tools** sufficient for an agent that authors and revises copy:

| Tool | Purpose |
|---|---|
| `drive_list` | List/search files & folders within an allowed folder |
| `docs_create` | Create a Google Doc in an allowed folder |
| `docs_read` | Read full text (and structure) of a Doc |
| `docs_edit` | Edit an existing Doc (insert/replace text via `batchUpdate`) |
| `sheets_create` | Create a Google Sheet in an allowed folder |
| `sheets_read` | Read a cell range |
| `sheets_update` | Update a cell range |
| `sheets_append` | Append rows |

**Post-MVP (future, incremental):** richer Docs formatting (tables, styles), Slides, copy/move *within* allowed scope, broader Drive search — growing toward "full Drive API." Each increment is additive; MVP tools are the stable core.

## 3. Non-goals

- **No domain-wide delegation.** Ever. Access is granted only by sharing folders with the SA email.
- **No destructive/sharing tools in MVP:** no delete/trash, no move-out-of-scope, no permission/sharing changes. (Enforced at three layers — see §8.)
- **No user-context services:** Gmail and personal Google Calendar are explicitly out — a bare service account has no mailbox and no personal calendar; those fundamentally require OAuth or DWD.
- **Not a general file sync / large binary up/download tool** in MVP.

## 4. Architecture

```
AI agent (MCP client)
   │  MCP over HTTP/SSE  (http://<host>:8080/mcp)
   ▼
gdrive-mcp  (Python)
   ├─ MCP layer        — official MCP Python SDK; registers the ~8 tools
   ├─ Auth             — service_account.Credentials from JSON; no DWD
   ├─ Google clients   — google-api-python-client (Drive v3, Docs v1) + gspread (Sheets)
   └─ Scope guard      — every op validated against ALLOWED_FOLDER_IDS before any API call
   │
   ▼  Google REST APIs (Drive / Docs / Sheets)
```

- **Language/runtime:** Python (≥3.11). Matches the fleet's existing Python MCP tooling (`mcp/claude-mcp/` SSE wrappers).
- **Libraries:** `google-api-python-client`, `google-auth`, `gspread` (Sheets ergonomics), official `mcp` SDK.
- **Transport:** HTTP/SSE on a configurable port (default 8080), endpoint `/mcp` — so a hermes container connects exactly as it does to `claude-mcp` today (`mcp_servers: { gdrive: { url: http://gdrive-mcp-<agent>:8080/mcp } }`).
- **Single process**, stateless between requests apart from cached Google client objects.

### Module layout (target repo)
```
gdrive-mcp/
├── pyproject.toml            # package + console entry point `gdrive-mcp`
├── README.md
├── Dockerfile                # python-slim + pip install . ; CMD runs the server
├── src/gdrive_mcp/
│   ├── __main__.py           # entry: parse env, build clients, start MCP HTTP/SSE server
│   ├── auth.py               # load SA creds, build Drive/Docs/Sheets services
│   ├── scope.py              # ALLOWED_FOLDER_IDS guard + descendant resolution
│   ├── tools/
│   │   ├── drive.py          # drive_list
│   │   ├── docs.py           # docs_create / docs_read / docs_edit
│   │   └── sheets.py         # sheets_create / sheets_read / sheets_update / sheets_append
│   └── errors.py             # uniform error → MCP error mapping
└── tests/                    # see §10
```

## 5. Authentication & configuration

Auth is a service-account JSON key; access comes from **folder sharing**, not from the key's roles. Scopes requested: `drive`, `documents`, `spreadsheets`.

**Environment variables:**

| Var | Required | Meaning |
|---|---|---|
| `SERVICE_ACCOUNT_JSON` or `SERVICE_ACCOUNT_PATH` | yes (one) | SA credentials, inline JSON or file path |
| `ALLOWED_FOLDER_IDS` | yes | Comma-separated Drive folder IDs the server may operate within |
| `GDRIVE_MCP_PORT` | no (default 8080) | HTTP/SSE listen port |
| `GDRIVE_MCP_HOST` | no (default 0.0.0.0) | bind address |
| `ENABLED_TOOLS` | no (default: all MVP read+write, no destructive) | explicit allow-list of tool names |

No OAuth client, no token file, no consent flow.

## 6. Tool contracts (MVP)

All tools return structured JSON; all accept/return Drive file IDs (not paths) as the canonical handle. `drive_list` is how an agent discovers IDs.

- `drive_list(folder_id?, query?) -> [{id, name, mimeType, modifiedTime}]`
  Lists items within an allowed folder (or all allowed folders if omitted). `query` is an optional name/full-text filter. **Rejects** `folder_id` outside allowed scope.
- `docs_create(title, folder_id) -> {id, url}`
  Creates a Doc inside an allowed folder.
- `docs_read(file_id) -> {title, text, structure?}`
  Returns full document text; `structure` (paragraph/index map) optional, used to compute edit positions.
- `docs_edit(file_id, ops?, requests?) -> {applied: n}`
  Applies edits via Docs `batchUpdate`. Exposes **both** levels, because both suit MCP/LLM callers:
  - `ops` — friendly high-level operations (`{find, replace}`, `{insert_at, text}`) for the common copy-revision case; the server expands them into correct `batchUpdate` payloads so callers needn't compute index ranges.
  - `requests` — **raw `batchUpdate` request passthrough** for full Docs API power (tables, styling, named ranges, etc.) without waiting for new dedicated tools. An LLM agent can construct these directly.
  At least one of `ops`/`requests` is required; if both given, `ops` are expanded and concatenated before `requests`. Raw requests are still subject to the §8 scope guard (the target `file_id` must be in an allowed folder).
- `sheets_create(title, folder_id) -> {id, url}`
- `sheets_read(file_id, range) -> {values: [[...]]}`
- `sheets_update(file_id, range, values) -> {updatedCells}`
- `sheets_append(file_id, range, values) -> {updates}`

## 7. Error handling

- **Out-of-scope access** → deny *before* any API call, with a clear message naming the allowed folders. (Scope guard in `scope.py`.)
- **Google API errors** (404/403/429/5xx) → mapped to uniform MCP errors with the Google reason surfaced; 429/5xx are retried with bounded exponential backoff.
- **Auth failure at startup** (bad/missing SA JSON, API not enabled) → fail fast with an actionable message; server does not start.
- **Partial batch edits** → report how many requests applied and which failed.

## 8. Security model — least privilege, three layers

1. **API enablement:** only Drive/Docs/Sheets APIs enabled on the SA's project → Gmail/Calendar capabilities don't exist.
2. **Drive permission:** the SA is shared into folders as **Contributor** (create/edit, *not* trash/move/share). Even a misbehaving or compromised server physically cannot delete or re-share.
3. **Tool surface:** no delete/move/share tools exposed; `ALLOWED_FOLDER_IDS` + scope guard reject any operation targeting files outside the shared folders.

No DWD anywhere → the credential can never impersonate a domain user.

## 9. Packaging & deployment

- `pip install`-able with a console entry point `gdrive-mcp`.
- `Dockerfile` (python-slim) builds an image the consuming fleet packages as a per-agent sidecar (`mcp/gdrive-mcp/` in solarmatrix/agents installs/runs it — Project B).
- Versioned releases; consumers pin a version. (This is the cost the dedicated-repo decision accepts in exchange for a clean product boundary.)

## 10. Testing strategy

- **Unit:** scope guard (in/out of allowed folders), `docs_edit` request builder (find/replace + insert → correct `batchUpdate` payloads), env/config parsing, error mapping. Google clients mocked.
- **Contract:** each tool's input/output schema validated.
- **Integration (opt-in, gated on creds):** against a real throwaway Shared Drive folder + test SA — create/read/edit a Doc and a Sheet end-to-end. Skipped in CI without secrets.
- TDD: write the failing test per tool before implementing it.

## 11. Incremental growth path

MVP tools are the stable core. Additive increments (each its own small spec/PR): richer Docs formatting → Slides → in-scope copy/move → broader search → eventually full Drive API surface. The auth model, scope guard, and transport stay constant as the tool set grows.

## 12. Open questions

1. **Repo name/owner** — default assumption `qianqin/gdrive-mcp` (mirrors `qianqin/claude-agents-mcp`). Confirm.
2. **MCP HTTP/SSE serving** — use the official MCP Python SDK's built-in HTTP transport if it cleanly serves `/mcp`, else a thin SSE wrapper mirroring `mcp/claude-mcp/`. Decide at implementation time; does not affect tool contracts.

**Resolved:** `docs_edit` exposes both friendly `ops` and raw `batchUpdate` `requests` passthrough (see §6).
