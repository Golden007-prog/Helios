# Codegen

`make typegen` runs three steps from the repo root:

1. **OpenAPI dump** — `python -m shared.codegen.dump_openapi` boots the
   FastAPI app in test mode and writes `shared/schemas/api.openapi.json`.
2. **Pydantic → TypeScript** — `python -m shared.codegen.pydantic_to_typescript`
   walks every model under `backend/app/models/` and writes
   `frontend/src/lib/api/types.gen.ts`.
3. **Constants dump** — copies `shared/constants/*.json` into
   `frontend/src/lib/api/constants.gen.ts` as plain TS exports.

The generated files are committed; CI runs `make typegen` and fails if the
working tree is dirty afterwards. That guarantees the frontend always sees
exactly the contract the backend serves.

`make typegen` is idempotent — running it twice produces no diff.
