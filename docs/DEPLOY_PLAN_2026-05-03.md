# Helios Deployment Plan — 2026-05-03

## PRE-FLIGHT CONFIRMATION

### Deployment Targets
- **IBM Cloud Region**: `us-south`
- **Code Engine Project**: `helios-prod`
- **ICR Namespace**: `icr.io/helios/`
- **Backend App Name**: `helios-backend`
- **GitHub Pages URL**: `https://golden007-prog.github.io/Helios`

### Hard Constraints Acknowledged
✅ Use Plan mode before each execution cycle
✅ No AI co-author trailers (AGENTS.md rule 1)
✅ No Bob/Claude/Granite references in source (AGENTS.md rule 2)
✅ Audit chain integrity must remain intact
✅ Never print secret values — only secret names
✅ Do not touch frontend/ source files (Sayan's territory)
✅ Do not run git commit/push (Golden runs git)
✅ Stop at every CHECKPOINT for Golden's review

### MCP Server Status
⚠️ MCP servers (ibm-cloud, cloudant, watsonx) not exposing tools via stdio protocol
📋 Workaround: Use `ibmcloud` CLI commands directly via execute_command for live state probing

### Current Configuration Review

**Backend Dockerfile** (`backend/Dockerfile`):
- Base: `python:3.11-slim`
- Port: 8080
- User: non-root (helios:1001)
- Entrypoint: tini + uvicorn
- Build args: HELIOS_GIT_SHA, HELIOS_BUILD_TIME, HELIOS_IMAGE_TAG

**Code Engine Spec** (`backend/deploy/code-engine.yaml`):
- Image: `icr.io/helios/helios-backend:${IMAGE_TAG:-latest}`
- Scale: min=0, max=4, concurrency=80
- Resources: 1 CPU, 1G memory, 512M ephemeral storage
- Timeout: 60s
- Probes: /healthz (liveness), /readyz (readiness)
- Secrets: `helios-env` (env-from)
- CORS: `https://golden007-prog.github.io`

**Frontend Config** (`frontend/next.config.mjs`):
- Output: `export` (static)
- Base path: `/Helios` (when GITHUB_PAGES=true)
- Images: unoptimized
- Trailing slash: true

**Existing Workflows**:
- `backend-deploy.yml`: Build → push ICR → deploy Code Engine (manual approval)
- `frontend-deploy.yml`: Build → upload artifact → deploy Pages

---

## CYCLE 1 — Backend Container + IBM Code Engine Deploy

### Coin Budget: 4 (of 9 total)

### Phase 1: Pre-Deploy Validation

**Objective**: Confirm the build is shippable before deploying

**Steps**:
1. Run database migrations: `make migrate`
   - Applies Cloudant indexes from `backend/migrations/cloudant_indexes.json`
   - Expected: All indexes created successfully

2. Seed demo corpus: `make seed`
   - Seeds regions, abend patterns, demo JCL
   - Expected: 7 regions, hero JCL, abend patterns loaded

3. Verify corpus integrity: `make verify-corpus`
   - Validates SHA-256 checksums of seeded data
   - Expected: All checksums match

4. Run backend tests: `make test-backend`
   - Runs pytest suite
   - Expected: All tests pass (or known xfails for Bob stubs)

**Abort Criteria**: If any validation step fails, STOP and surface the failure. Do not deploy a broken build.

### Phase 2: Docker Build + Local Validation

**Objective**: Build container image and verify it works locally

**Steps**:
1. Build image:
   ```bash
   docker build \
     --build-arg HELIOS_GIT_SHA=$(git rev-parse --short HEAD) \
     --build-arg HELIOS_BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
     --build-arg HELIOS_IMAGE_TAG=$(date +%Y%m%d-%H%M%S) \
     -t helios-backend:local \
     -f backend/Dockerfile .
   ```
   - Context: repo root (to include shared/)
   - Expected: Image size < 500 MB

2. Test image locally:
   ```bash
   docker run --rm -d \
     --name helios-test \
     -p 8081:8080 \
     --env-file .env \
     helios-backend:local
   ```

3. Smoke test local container:
   - `curl http://localhost:8081/healthz` → 200 OK
   - `curl http://localhost:8081/readyz` → 200 OK (or 503 if deps unavailable)
   - `curl http://localhost:8081/version` → JSON with git SHA

4. Stop test container:
   ```bash
   docker stop helios-test
   ```

**CHECKPOINT 1B**: Show Golden:
- Image tag and size
- Local smoke test results
- Wait for "continue"

### Phase 3: IBM Container Registry Push

**Objective**: Push image to ICR for Code Engine deployment

**Steps**:
1. Login to IBM Cloud:
   ```bash
   ibmcloud login --apikey $IBM_CLOUD_API_KEY -r us-south
   ```

2. Login to ICR:
   ```bash
   ibmcloud cr login
   ```

3. Tag for ICR:
   ```bash
   TIMESTAMP=$(date +%Y%m%d-%H%M%S)
   docker tag helios-backend:local us.icr.io/helios/helios-backend:$TIMESTAMP
   docker tag helios-backend:local us.icr.io/helios/helios-backend:latest
   ```

4. Push images:
   ```bash
   docker push us.icr.io/helios/helios-backend:$TIMESTAMP
   docker push us.icr.io/helios/helios-backend:latest
   ```

5. Verify push:
   ```bash
   ibmcloud cr image-list --restrict helios/helios-backend
   ```
   - Expected: Both tags visible

### Phase 4: Code Engine Secrets Verification

**Objective**: Ensure required secrets exist without exposing values

**Required Secrets**:
The Code Engine app expects a single secret named `helios-env` with these keys:
- `CLOUDANT_URL`
- `CLOUDANT_APIKEY`
- `WATSONX_URL`
- `WATSONX_PROJECT_ID`
- `WATSONX_APIKEY`
- `JWT_SECRET`

**Steps**:
1. Select Code Engine project:
   ```bash
   ibmcloud ce project select --name helios-prod
   ```

2. List existing secrets:
   ```bash
   ibmcloud ce secret list
   ```

3. Check if `helios-env` exists:
   ```bash
   ibmcloud ce secret get --name helios-env
   ```

4. **If secret does NOT exist**, create it:
   ```bash
   # Create a temporary env file with only the required keys
   grep -E '^(CLOUDANT_URL|CLOUDANT_APIKEY|WATSONX_URL|WATSONX_PROJECT_ID|WATSONX_APIKEY|JWT_SECRET)=' .env > .env.ce-secrets
   
   ibmcloud ce secret create \
     --name helios-env \
     --from-env-file .env.ce-secrets
   
   # Clean up temp file
   rm .env.ce-secrets
   ```

5. **If secret exists**, verify it has all required keys:
   ```bash
   ibmcloud ce secret get --name helios-env --output json | jq '.data | keys'
   ```
   - Expected: All 6 keys present

**Security Note**: Never echo secret values. Use `--from-env-file` to avoid exposing values in command history.

### Phase 5: Code Engine App Deployment

**Objective**: Deploy or update the helios-backend app

**Decision Point**: Create vs Update
1. Check if app exists:
   ```bash
   ibmcloud ce app get --name helios-backend
   ```

2. **If app does NOT exist** (exit code != 0):
   ```bash
   ibmcloud ce app create \
     --name helios-backend \
     --image us.icr.io/helios/helios-backend:$TIMESTAMP \
     --port 8080 \
     --cpu 1 \
     --memory 2G \
     --ephemeral-storage 512M \
     --min-scale 0 \
     --max-scale 3 \
     --concurrency 50 \
     --request-timeout 120 \
     --env ENVIRONMENT=production \
     --env LOG_LEVEL=INFO \
     --env LOG_FORMAT=json \
     --env CORS_ORIGINS=https://golden007-prog.github.io \
     --env-from-secret helios-env
   ```

3. **If app exists**:
   ```bash
   ibmcloud ce app update \
     --name helios-backend \
     --image us.icr.io/helios/helios-backend:$TIMESTAMP \
     --cpu 1 \
     --memory 2G \
     --min-scale 0 \
     --max-scale 3 \
     --concurrency 50 \
     --request-timeout 120 \
     --env CORS_ORIGINS=https://golden007-prog.github.io
   ```

4. Wait for deployment to complete:
   ```bash
   ibmcloud ce app get --name helios-backend --output json | jq '.status'
   ```
   - Expected: `"Ready"`

5. Capture production URL:
   ```bash
   BACKEND_URL=$(ibmcloud ce app get --name helios-backend --output url)
   echo "Backend deployed at: $BACKEND_URL"
   ```

### Phase 6: Production Smoke Tests

**Objective**: Verify the deployed app is functional

**Tests**:
1. Health check:
   ```bash
   curl -f $BACKEND_URL/healthz
   ```
   - Expected: 200 OK

2. Readiness check:
   ```bash
   curl -f $BACKEND_URL/readyz
   ```
   - Expected: 200 OK (or 503 if Cloudant/watsonx unreachable)

3. Version endpoint:
   ```bash
   curl -s $BACKEND_URL/version | jq
   ```
   - Expected: JSON with git SHA matching $TIMESTAMP

4. Regions API:
   ```bash
   curl -s $BACKEND_URL/api/regions | jq '.regions | length'
   ```
   - Expected: 7 (from seeded corpus)

5. CORS preflight:
   ```bash
   curl -I \
     -H "Origin: https://golden007-prog.github.io" \
     -H "Access-Control-Request-Method: GET" \
     $BACKEND_URL/api/regions
   ```
   - Expected: `Access-Control-Allow-Origin: https://golden007-prog.github.io` header present

6. OpenAPI docs (if not production):
   ```bash
   curl -s $BACKEND_URL/docs
   ```
   - Expected: 404 (docs disabled in production per config.py)

**Failure Handling**: If any smoke test fails, prepare rollback command:
```bash
# Get previous image tag from ICR
PREVIOUS_TAG=$(ibmcloud cr image-list --restrict helios/helios-backend --format json | jq -r '.[1].RepoTags[0]' | cut -d: -f2)

# Rollback command (DO NOT RUN without Golden's approval)
ibmcloud ce app update \
  --name helios-backend \
  --image us.icr.io/helios/helios-backend:$PREVIOUS_TAG
```

### Phase 7: Documentation Update

**Objective**: Record deployment details for future reference

**Updates to `docs/RUNBOOK.md`**:
```markdown
## Production URLs

- **Backend**: $BACKEND_URL
- **Frontend**: (to be deployed in Cycle 2)

## Last Deploy

- **Date**: 2026-05-03
- **Image**: us.icr.io/helios/helios-backend:$TIMESTAMP
- **Git SHA**: $(git rev-parse --short HEAD)
- **Deployed by**: Golden

## Rollback

If the current deployment fails:
```bash
ibmcloud ce app update \
  --name helios-backend \
  --image us.icr.io/helios/helios-backend:$PREVIOUS_TAG
```

## Cost Notes

Code Engine free tier:
- 100K requests/month
- 4M vCPU-seconds/month
- 8M GB-seconds/month

Current config: min-scale=0 (scale to zero when idle)
```

**CHECKPOINT 1C**: Show Golden:
- Production URL: $BACKEND_URL
- All smoke test results (PASS/FAIL)
- Suggested commit message:
  ```
  feat(deploy): code engine app for helios-backend with secret-bound config
  
  - Image: us.icr.io/helios/helios-backend:$TIMESTAMP
  - Scale: 0-3 instances, 1 CPU, 2G memory
  - Secrets: helios-env (Cloudant + watsonx + JWT)
  - CORS: https://golden007-prog.github.io
  - Probes: /healthz, /readyz
  ```
- Wait for "continue" before Cycle 2

---

## Rollback Strategy

If deployment fails at any phase:

1. **Phase 1-2 (Pre-deploy/Build)**: No rollback needed; fix locally and retry
2. **Phase 3 (ICR Push)**: Delete bad image tags if needed
3. **Phase 4 (Secrets)**: Update secret with correct values
4. **Phase 5-6 (Deploy/Smoke)**: Roll back to previous image:
   ```bash
   ibmcloud ce app update \
     --name helios-backend \
     --image us.icr.io/helios/helios-backend:$PREVIOUS_TAG
   ```

## Success Criteria

- [ ] All pre-deploy validations pass
- [ ] Docker image builds successfully (< 500 MB)
- [ ] Local smoke tests pass
- [ ] Image pushed to ICR
- [ ] Code Engine secrets verified
- [ ] App deployed (create or update)
- [ ] Production smoke tests pass
- [ ] RUNBOOK.md updated with production URL
- [ ] No secrets exposed in logs or command history

---

## Next: Cycle 2 — Frontend to GitHub Pages

After Cycle 1 completes and Golden approves, proceed with frontend deployment plan.