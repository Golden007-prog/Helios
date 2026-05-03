# helios-corpus — Custom MCP Server (Phase 1.1)

**Status: stub.** Bob owns the implementation per docs/MCP_SETUP.md.

Read-only access to the MeridianBank synthetic corpus under
`shared/sample-corpus/MERIDIANBANK/`. Six tools exposed; each registered
with full input schema, each handler raises `NotImplementedError` with a
`BOB:` marker.

| Tool                  | Status |
|-----------------------|--------|
| `list_jcl`            | stub   |
| `read_jcl`            | stub   |
| `list_cobol`          | stub   |
| `read_cobol`          | stub   |
| `list_regions`        | stub   |
| `get_region_profile`  | stub   |

Activation: Phase 1.1, after the corpus is seeded under `shared/sample-corpus/`.
