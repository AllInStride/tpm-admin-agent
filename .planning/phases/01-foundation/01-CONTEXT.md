# Phase 1: Foundation - Context

**Gathered:** 2025-01-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the architectural foundation so all subsequent phases have reliable infrastructure. Deliverables: event bus, canonical data models, event store, FastAPI skeleton, test harness. No user-facing features — pure infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Development Environment
- Direct Python execution (no Docker for dev)
- uv as package manager (fast, modern, replaces pip + venv)
- Python 3.12+ required — check and install if needed
- Auto-reload on save during development (FastAPI --reload)

### Deployment Target
- Fly.io for production deployment
- Turso (edge SQLite) for database — matches existing Momentum stack
- .env file for local secrets, Fly secrets for production
- Localhost only during dev — no ngrok/tunnel needed initially

### Testing Approach
- Test critical paths, not 100% coverage
- pytest as test framework
- Pre-commit hooks to run tests before commits
- Real LLM calls with caching (realistic tests, controlled costs)

### Claude's Discretion
- Project structure and package layout
- Module organization
- Code style and formatting choices
- Event schema design details
- Pydantic model field specifics

</decisions>

<specifics>
## Specific Ideas

- User is **not a developer** — building this together with Claude
- Working directory is `/Users/gabrielguenette/projects/tpm-admin-agent`
- Want to go as far as possible in building, not just planning
- This will be developed with Cursor assistance

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2025-01-17*
