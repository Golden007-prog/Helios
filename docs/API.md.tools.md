# docs/API.md generation

The committed `docs/API.md` is hand-written. The auto-generated companion
is `shared/schemas/api.openapi.json`, produced by:

```bash
python -m shared.codegen.dump_openapi
```

The OpenAPI dump is what the frontend's `make typegen` consumes and what
CI compares against to catch contract drift.

If you want to publish a human-readable HTML view of the OpenAPI dump:

```bash
npx @redocly/cli build-docs shared/schemas/api.openapi.json -o docs/api.html
```

`docs/api.html` is gitignored by convention — generate when needed.

## Regenerating after a model change

1. Edit a Pydantic model under `backend/app/models/`.
2. Run `make typegen` from the repo root.
3. Commit the diff under `shared/schemas/` and `frontend/src/lib/api/types.gen.ts`.
4. Update `docs/API.md` if the contract changed in a human-meaningful way
   (renamed endpoint, new request field, new error code). The OpenAPI
   dump captures the shape; `docs/API.md` captures the *story*.
