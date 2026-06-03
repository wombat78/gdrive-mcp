# gdrive-mcp

Service-account-native MCP server for Google Drive, Docs, and Sheets. No domain-wide delegation — access is granted by sharing folders with the service account.

See `docs/specs/` for the design and `docs/plans/` for the build plan.

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

## Security / network model

The MCP endpoint is **unauthenticated HTTP**. This server is designed to run as a
**per-agent sidecar** on a private, isolated network — each agent gets its own
instance and no other agent can reach it. That **network isolation is the access
control**; the server itself does not authenticate callers.

**Do not expose the port publicly.** Running the server on a routable address
without a network perimeter (firewall, VPN, service-mesh policy) would allow any
caller to invoke all enabled tools against the configured Google account.
