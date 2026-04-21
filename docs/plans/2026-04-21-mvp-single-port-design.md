# MVP Single-Port Design

## Context

The repository currently contains requirements documents only: `prd.md`, `spec.md`, and `trd.md`. The MVP will start from the TRD stack: FastAPI backend, vanilla JavaScript frontend, SQLAlchemy data model, SQLite for local development, and MySQL-compatible configuration for later production use.

The user selected the MVP scaffold approach and requested that the full application run on one port.

## Recommended Approach

Use a single FastAPI application to serve both API endpoints and frontend static files.

- `/api/*` routes provide backend JSON APIs.
- `/` serves `frontend/index.html`.
- `/css`, `/js`, and `/assets` serve frontend static files.
- Local execution uses one command: `uvicorn backend.main:app --reload --port 8000`.

This keeps the initial workflow simple while matching the documented FastAPI plus vanilla JavaScript architecture.

## Initial Scope

The MVP scaffold will include:

- `backend/` with app startup, configuration, database session handling, SQLAlchemy models, routers, services, schemas, and tests.
- `frontend/` with a usable vanilla JavaScript shell: mock login/role selection, inputter spreadsheet view, detail modal, approver queue, and admin dashboard cards.
- `docker/` with a basic Dockerfile and compose file.
- SQLite as the default database.
- Seed/sample data for local UI and API verification.

## Backend Design

The backend will expose initial route groups for:

- Health: `/api/health`
- Auth: mock `/api/auth/me`
- Organizations
- Tasks
- Questions
- Approvals
- Dashboard

AD SSO and SMTP will be stubbed in the MVP. The code should keep clear service boundaries so real SSO and email integration can replace the stubs later.

## Frontend Design

The frontend will be framework-free and organized under `frontend/js/` by responsibility:

- `api.js` for API calls
- `auth.js` for mock user/role state
- `spreadsheet.js` for inputter task entry
- `form.js` for row detail modal
- `approval.js` for approver views
- `dashboard.js` for admin summary
- `app.js` for routing and initialization

The UI should follow the requirements: neutral styling, dense spreadsheet-like input, status badges, and role-based navigation.

## Data And Business Logic

Implement the core domain rules first:

- Confidential classification is true if any question answer includes an option other than `해당 없음`.
- National core technology classification uses the same rule.
- Approval paths are derived from `org_type`: `NORMAL`, `TEAM_DIRECT`, or `DIV_DIRECT`.
- Task validation blocks submission when required fields are missing.

## Testing

Use `pytest` with SQLite. Initial tests should cover:

- App health endpoint
- Database initialization
- Confidential/national-tech classification logic
- Approval path calculation
- Basic task validation

## Deferred Items

The MVP will include UI/API placeholders but defer full implementations for:

- Real AD SSO integration
- Real SMTP delivery
- Excel import/export file generation
- Production MySQL deployment tuning

## Git Note

This workspace is not currently a Git repository, so the design document cannot be committed until Git is initialized or the folder is moved into a repository.
