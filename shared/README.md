# shared/

Cross-language source of truth.

```
shared/
├── constants/                  # JSON enums consumed by both backend + frontend
│   ├── features.json           # Atlas / Studio / ABEND / …
│   ├── severities.json         # critical / high / medium / low / info
│   ├── statuses.json           # job + queue + finding decisions
│   └── banned_watsonx_models.json
├── schemas/                    # JSON-schema dumps from backend Pydantic
│   ├── api.openapi.json        # generated from FastAPI app
│   └── cloudant.collections.json
├── codegen/
│   ├── pydantic_to_typescript.py   # backend Pydantic → frontend types
│   └── README.md
└── sample-corpus/              # MeridianBank synthetic corpus (Bob seeds)
    └── MERIDIANBANK/.gitkeep
```

The backend Pydantic models in `backend/app/models/` are authoritative.
`shared/codegen/pydantic_to_typescript.py` walks them and emits TypeScript
into `frontend/src/lib/api/types.gen.ts`. The OpenAPI dump is produced at
the same time so the frontend's API client can be re-generated end-to-end
with `make typegen`.

Constants under `shared/constants/` are the only place where enum *values*
live. Both ecosystems load them at build time:

* Python: `from app.models.common import Severity` (mirrors `severities.json`)
* TypeScript: `import { Severity } from "@/lib/api/constants"` (mirrors the same)

Whenever you change a constant: edit the JSON, run `make typegen`, commit
both sides. CI fails if `make typegen` would produce a diff.
