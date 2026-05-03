# helios-ibm-cloud — Custom MCP Server (Phase 1.6)

Read-only IBM Cloud metadata for the deploy phase. Bob uses this to verify
Code Engine state, tail app logs, and confirm Cloudant instance health
without leaving the IDE.

## Tools

| Name                       | Description                                  |
|----------------------------|----------------------------------------------|
| `list_code_engine_apps`    | Apps under the configured Code Engine project |
| `get_app_logs`             | Tail of recent logs for one app               |
| `list_cloudant_instances`  | Cloudant resource instances visible to the key |

All read-only.

## Activation

Phase 1.6 (deployment). Required env: `IBM_CLOUD_API_KEY`,
`IBM_CLOUD_REGION`, `CODE_ENGINE_PROJECT_ID`.
