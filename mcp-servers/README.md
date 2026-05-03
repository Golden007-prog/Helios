# Helios — Custom MCP Servers

Four custom Model Context Protocol servers that expose Helios-specific
operations to Bob IDE (and to Claude Code via the same `.bob/mcp.json`).
See [`docs/MCP_SETUP.md`](../docs/MCP_SETUP.md) for the architecture.

## Layout

```
mcp-servers/
├── pyproject.toml          # one package, 4 server entrypoints
├── _shared/                # tiny tool-registration shim
├── cloudant/               # read-only Cloudant queries  (active: Phase 1.1)
├── ibm_cloud/              # read-only IBM Cloud metadata (active: Phase 1.6)
├── helios_corpus/          # MeridianBank synthetic corpus (active: Phase 1.1)
├── watsonx_server/         # Granite prompt templates    (active: Phase 1.4)
└── tests/                  # boot + tool-list smoke tests
```

| Server         | Status                              | Implements                                   |
|----------------|-------------------------------------|----------------------------------------------|
| `cloudant`     | **Implemented** — plumbing          | `list_collections`, `find_documents`, `get_document`, `count_documents` |
| `ibm_cloud`    | **Implemented** — read-only         | `list_code_engine_apps`, `get_app_logs`, `list_cloudant_instances` |
| `helios_corpus`| Stub — Bob, Phase 1.1               | `list_jcl`, `read_jcl`, `list_cobol`, `read_cobol`, `list_regions`, `get_region_profile` |
| `watsonx_server`| Stub — Bob, Phase 1.4              | `granite_summarize_paragraph`, `granite_explain_field` |

## Running locally

```bash
pip install -e mcp-servers
python -m cloudant.server --list-tools     # boot + print registered tools, exit 0
python -m cloudant.server                  # full stdio MCP loop (when mcp SDK present)
```

## Activating in Bob IDE

The four custom servers are listed as `disabled: true` in
[`.bob/mcp.json`](../.bob/mcp.json) by default. Flip a server to
`disabled: false` only when (a) its phase is reached and (b) every
`alwaysAllow` operation is read-only.

## Development

Smoke tests exercise the boot path and assert each server registers the
expected tool names. They do **not** exercise the JSON-RPC stdio protocol
(that responsibility lives in the `mcp` Python SDK).

```bash
cd mcp-servers
pip install -e ".[dev]"
pytest
```

The shared registry shim (`_shared/tool_registry.py`) lets tools be defined
once and surfaced both to the JSON-RPC stdio transport and to a `--list-tools`
introspection mode used by the smoke tests.
