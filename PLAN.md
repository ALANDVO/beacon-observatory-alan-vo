# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

hook-effectiveness-analyzer

## Roadmap

### core-skeleton — FastAPI/React skeleton with health check workflow

Status: done

Acceptance:
- Backend starts and responds to GET /healthz
- Frontend builds and serves a page showing backend health status
- Docker compose brings up both services
- Backend tests pass (pytest)
- Frontend typecheck and tests pass (npm run build, npm test)

Implementation: `backend/app/main.py`, `backend/app/api/health.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/requirements.txt`, `backend/pyproject.toml`, `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/components/HealthStatus.tsx`, `frontend/src/api/client.ts`, `frontend/src/types/api.ts`, `frontend/src/index.css`, `frontend/src/App.css`, `compose.yaml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.env.example`, `README.md`

Tests: `backend/tests/test_health.py`, `frontend/tests/App.test.tsx`, `frontend/tests/setup.ts`

### pstack-registry — pstack skill/playbook registry with CRUD API

Status: done

Acceptance:
- POST /api/skills creates a skill with validation
- GET /api/skills lists skills with pagination/filtering
- GET /api/skills/{id} returns skill detail
- PUT /api/skills/{id} updates skill
- DELETE /api/skills/{id} removes skill
- Skills persisted in SQLite with UTC timestamps
- Config generation for Claude/Codex/Copilot

Implementation: `backend/app/models/skill.py`, `backend/app/api/skills.py`, `backend/app/api/__init__.py`

Tests: `backend/tests/test_skills.py`

### agent-config-generator — Agent configuration generator for Claude/Codex/Copilot/etc

Status: done

Acceptance:
- POST /api/skills/{id}/generate-config generates config for target agent
- Supports at least 3 agent types (Claude, Codex, Copilot)
- Generated config includes hooks, skills, playbooks
- Frontend form to select skills and generate config

Implementation: `backend/app/api/skills.py (generate_config endpoint)`

Tests: `backend/tests/test_skills.py (TestSkillConfigGeneration)`

### hook-effectiveness-analyzer — Hook effectiveness analyzer (addresses Issue #264)

Status: done

Acceptance:
- Ingests session logs and computes hook reach/follow-through rates
- Compares main vs subagent sessions
- Dashboard shows opens per 100 prompts by agent type
- Exports analysis as JSON/CSV

Implementation: `backend/app/models/analysis.py`, `backend/app/api/analysis.py`, `backend/tests/test_analysis.py`

Tests: `backend/tests/test_analysis.py`

### oidc-auth — OIDC authentication with Keycloak

Status: planned

Acceptance:
- Login/logout flow works with Keycloak
- Protected API endpoints require valid token
- Roles: viewer, operator, admin
- Demo mode for local development only

