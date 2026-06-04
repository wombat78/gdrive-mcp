# gdrive-mcp

Service-account-native MCP server for Google Drive, Docs, and Sheets. No domain-wide delegation — access is granted by sharing folders with the service account.

See `docs/specs/` for the design and `docs/plans/` for the build plan.

## Configuration

| Env var | Required | Meaning |
|---|---|---|
| `SERVICE_ACCOUNT_JSON` / `SERVICE_ACCOUNT_PATH` | yes (one) | Service-account credentials (inline JSON or file path) |
| `ALLOWED_FOLDER_IDS` | one of the two | Comma-separated Drive folder IDs the server may operate within |
| `ALLOWED_DRIVE_IDS` | one of the two | Comma-separated Shared Drive IDs; the SA may access any item shared with it that resides in those drives |
| `GDRIVE_MCP_PORT` | no (8080) | HTTP listen port |
| `GDRIVE_MCP_HOST` | no (0.0.0.0) | Bind address |
| `ENABLED_TOOLS` | no (all) | Comma-separated allow-list of tool names |

At least one of `ALLOWED_FOLDER_IDS` or `ALLOWED_DRIVE_IDS` must be set. Both may be set together.

When `ALLOWED_DRIVE_IDS` is set, the SA may access any item shared with it that resides in those Shared Drives; anything outside (personal My Drive, other orgs) is rejected — the anti-injection boundary.

Grant access by sharing the target folder(s) with the service account's email
(`client_email` in the JSON) as **Contributor** on the Shared Drive. No
domain-wide delegation required.

## Tools

| Tool | Description |
|------|-------------|
| `drive_list` | List files in an allowed folder or shared drive |
| `drive_read_file` | Read native/uploaded files (`.md`, `.txt`, `.json`, `.csv`, `.yaml`, etc.) or export Google-native types (Docs→Markdown, Sheets→CSV, Slides→plain text) |
| `docs_create` | Create a new Google Doc in an allowed folder |
| `docs_read` | Read a Google Doc via the Docs API |
| `docs_edit` | Edit a Google Doc (find/replace, insert) |
| `sheets_create` | Create a new Google Sheet in an allowed folder |
| `sheets_read` | Read values from a Sheet range |
| `sheets_update` | Write values to a Sheet range |
| `sheets_append` | Append rows to a Sheet range |

## Run

```bash
SERVICE_ACCOUNT_PATH=./sa.json ALLOWED_FOLDER_IDS=<folder-id> gdrive-mcp
# or, using a trusted Shared Drive:
SERVICE_ACCOUNT_PATH=./sa.json ALLOWED_DRIVE_IDS=<drive-id> gdrive-mcp
# serves MCP over streamable-HTTP at http://localhost:8080/mcp
```

## Security / network model

The MCP endpoint is **unauthenticated HTTP**. This server is designed to run as a
**per-agent sidecar** on a private, isolated network — each agent gets its own
instance and no other agent can reach it. That **network isolation is the access
control**; the server itself does not authenticate callers.

**Do not expose the port publicly.** Running the server on a routable address
without a network perimeter (firewall, VPN, service-mesh policy) would allow any
caller to invoke all enabled tools against the configured Google account.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
