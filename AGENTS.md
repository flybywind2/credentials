# Repository Guidelines

## Project Structure & Module Organization

This repository contains a single-port MVP for the confidential work classification system. The top-level `prd.md`, `spec.md`, and `trd.md` remain the source requirements.

- `backend/`: FastAPI app, SQLAlchemy models, routers, services, schemas, seed data, and `backend/tests/`.
- `frontend/`: vanilla JavaScript UI served by FastAPI from `index.html`, `css/`, `js/`, and `assets/`.
- `docker/`: container files, including `Dockerfile` and `docker-compose.yml`.
- `docs/plans/`: approved design and implementation plans.

Keep implementation files aligned with `trd.md`; update the requirements documents when architecture or behavior changes.

## Build, Test, and Development Commands

- `python -m venv .venv`: create a local Python environment.
- `pip install -r backend/requirements.txt`: install backend dependencies.
- `uvicorn backend.main:app --reload --port 8000`: run API and frontend on one local port.
- `pytest backend/tests -p no:cacheprovider`: run backend tests against SQLite without pytest cache files.
- `docker compose -f docker/docker-compose.yml up --build`: build and run the containerized stack.

## Coding Style & Naming Conventions

Use 4-space indentation for Python and 2-space indentation for JavaScript, CSS, HTML, YAML, and JSON. Prefer `snake_case` for Python modules, functions, and variables; use `PascalCase` for classes and SQLAlchemy/Pydantic models. Use `camelCase` for JavaScript variables and functions. Preserve domain terms from the requirements, including Korean labels and enum-like statuses such as `DRAFT`, `SUBMITTED`, `APPROVED`, and `REJECTED`.

No formatter or linter configuration is committed yet. Add and document tooling before enforcing style in CI.

## Testing Guidelines

The technical design calls for `pytest` with SQLite for local and automated tests. Prioritize tests for API endpoints, confidential/national-tech classification rules, approval path selection, CSV/Excel import validation, and submission blocking. Name tests by behavior, for example `test_classifies_confidential_when_any_option_selected`.

## Commit & Pull Request Guidelines

This checkout has no `.git` history, so no existing commit convention can be inferred. Use concise, imperative commits, preferably with a conventional prefix such as `docs:`, `feat:`, `fix:`, or `test:`.

Pull requests should include a short summary, linked issue or request, changed requirements documents, test evidence, and screenshots for UI changes.

## Security & Configuration Tips

Do not commit real employee IDs, SSO secrets, SMTP credentials, database passwords, or production exports. Keep environment-specific values in local environment files or secret storage, and provide sanitized examples only.
