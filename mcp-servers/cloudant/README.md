# helios-cloudant — Custom MCP Server (Phase 1.1)

Read-only Cloudant queries scoped to the `helios_*` collections. Used by Bob
(and Claude Code) during planning to inspect seeded state, audit log entries,
findings, and region overrides without going through the FastAPI backend.

## Tools

| Name              | Description                                       | Side effect |
|-------------------|---------------------------------------------------|-------------|
| `list_collections`| List every `helios_*` database                    | none        |
| `get_document`    | Fetch one doc by id                               | none        |
| `find_documents`  | Mango `_find` (selector, limit, fields, sort)     | none        |
| `count_documents` | Count via Mango (paginated)                       | none        |

All four are safe to add to `alwaysAllow` in `.bob/mcp.json` (read-only).

## Activation

Set in [`.bob/mcp.json`](../../.bob/mcp.json):

```json
"cloudant": { "disabled": false, ... }
```

Required env (inherited from `.env`): `CLOUDANT_URL`, `CLOUDANT_APIKEY`.

## Why scoped to `helios_*`?

The custom server enforces a database-name prefix on every call. Even if Bob
inadvertently asks for an unrelated database, this server refuses with a
structured `OUT_OF_SCOPE` error. Writes are not exposed at all — those go
through the FastAPI backend so the audit writer hash-chains them.
