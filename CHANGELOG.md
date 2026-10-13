# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-13

### Added
- FastAPI backend with health check endpoints (`/api/healthz`, `/api/health`)
- React + TypeScript + Vite frontend with health status dashboard
- Docker Compose orchestration for backend and frontend
- SQLite persistence with SQLAlchemy async
- Comprehensive test suite (pytest + Vitest)
- Typed API client derived from backend schemas
- Responsive professional UI with dark/light mode support
- CORS configuration for local development
- Environment-based configuration with Pydantic Settings
- Health checks for both services in Docker

### Infrastructure
- Backend Dockerfile (multi-stage, non-root user)
- Frontend Dockerfile (nginx static serve, non-root user)
- docker-compose.yaml with health checks and persistent volumes
- .env.example with all configuration options
- .gitignore for Python, Node, Docker, IDE, and local metadata

### Documentation
- README.md with architecture diagram, install/run/test instructions, API reference
- PLAN.md with feature roadmap
- feature-plan.json for incremental development tracking
- PORTFOLIO.json for portfolio metadata

### Security
- Demo mode restricted to localhost bind
- No hardcoded secrets or credentials
- OIDC configuration ready for Keycloak integration
- Server-side only LLM API key handling

---

## [Unreleased]

### Planned
- pstack skill/playbook registry with CRUD API
- Multi-agent configuration generator (Claude, Codex, Copilot, Pi, OpenCode, Gemini, Prime Agent)
- Hook effectiveness analyzer for session log analysis
- OIDC authentication with Keycloak (roles: viewer/operator/admin)
- SAML identity broker documentation
- LLM integration for advisory explanations
- Backup/restore tooling
- API rate limiting