# MVP Single-Port Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an MVP scaffold where FastAPI serves both JSON APIs and the vanilla JavaScript frontend from one port.

**Architecture:** FastAPI owns `/api/*` routes and serves `frontend/index.html` plus static assets for all browser routes. SQLAlchemy uses SQLite locally through `DATABASE_URL`, with service modules isolating classification and approval logic for later MySQL, broker SSO, and mail API integration.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Pydantic, pytest, SQLite, vanilla JavaScript, CSS, Docker.

---

### Task 1: Backend Package And Health Endpoint

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/main.py`
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/health.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/requirements.txt`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from backend.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_health.py -v`

Expected: FAIL before the app and route exist.

**Step 3: Write minimal implementation**

Add `backend/main.py` with a FastAPI app and include a router from `backend/routers/health.py` that returns `{"status": "ok"}`.

**Step 4: Install and test**

Run: `pip install -r backend/requirements.txt`

Run: `pytest backend/tests/test_health.py -v`

Expected: PASS.

**Step 5: Commit**

Skip until this folder is initialized as a Git repository.

### Task 2: Configuration And Database Session

**Files:**
- Create: `backend/config.py`
- Create: `backend/database.py`
- Create: `backend/tests/test_database.py`

**Step 1: Write the failing test**

```python
from backend.database import Base, engine


def test_database_metadata_can_create_tables():
    Base.metadata.create_all(bind=engine)
    assert Base.metadata.tables == {}
```

**Step 2: Run test**

Run: `pytest backend/tests/test_database.py -v`

Expected: FAIL before database helpers exist.

**Step 3: Implement minimal database module**

Use `DATABASE_URL` from environment, defaulting to `sqlite:///./dev.db`. Configure `connect_args={"check_same_thread": False}` only for SQLite. Export `Base`, `engine`, `SessionLocal`, and `get_db()`.

**Step 4: Run test**

Run: `pytest backend/tests/test_database.py -v`

Expected: PASS.

### Task 3: Domain Models And Schemas

**Files:**
- Create: `backend/models/__init__.py`
- Create: `backend/models/organization.py`
- Create: `backend/models/task.py`
- Create: `backend/models/question.py`
- Create: `backend/models/approval.py`
- Create: `backend/models/user.py`
- Create: `backend/schemas/__init__.py`
- Create: `backend/schemas/common.py`
- Create: `backend/tests/test_models.py`

**Step 1: Write model creation test**

```python
from backend.database import Base, engine
import backend.models  # noqa: F401


def test_model_tables_are_registered():
    Base.metadata.create_all(bind=engine)
    assert "organizations" in Base.metadata.tables
    assert "task_entries" in Base.metadata.tables
    assert "approval_requests" in Base.metadata.tables
```

**Step 2: Run test**

Run: `pytest backend/tests/test_models.py -v`

Expected: FAIL until models are registered.

**Step 3: Implement models**

Add SQLAlchemy tables from `trd.md`: organizations, users, task_entries, confidential_questions, national_tech_questions, task_question_checks, approval_requests, approval_steps, and tooltips/settings where needed for MVP.

**Step 4: Run test**

Run: `pytest backend/tests/test_models.py -v`

Expected: PASS.

### Task 4: Classification Service

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/classification.py`
- Create: `backend/tests/test_classification.py`

**Step 1: Write failing tests**

```python
from backend.services.classification import classify_from_answers


def test_classifies_false_when_all_answers_are_none_option():
    answers = [["해당 없음"], ["해당 없음"]]
    assert classify_from_answers(answers) is False


def test_classifies_true_when_any_answer_has_real_option():
    answers = [["해당 없음"], ["설계 자료"]]
    assert classify_from_answers(answers) is True
```

**Step 2: Run test**

Run: `pytest backend/tests/test_classification.py -v`

Expected: FAIL before service exists.

**Step 3: Implement service**

`classify_from_answers()` returns true when any selected option is not exactly `해당 없음`.

**Step 4: Run test**

Run: `pytest backend/tests/test_classification.py -v`

Expected: PASS.

### Task 5: Approval Flow Service

**Files:**
- Create: `backend/services/approval_flow.py`
- Create: `backend/tests/test_approval_flow.py`

**Step 1: Write failing tests**

```python
from backend.services.approval_flow import build_approval_path


def test_normal_path_has_group_team_division_heads():
    org = {
        "org_type": "NORMAL",
        "group_head_id": "g1",
        "team_head_id": "t1",
        "division_head_id": "d1",
    }
    assert build_approval_path(org) == ["g1", "t1", "d1"]
```

**Step 2: Add TEAM_DIRECT and DIV_DIRECT tests**

Expect `["t1", "d1"]` and `["d1"]`.

**Step 3: Implement service**

Map `NORMAL`, `TEAM_DIRECT`, and `DIV_DIRECT` to the documented approval chains. Raise `ValueError` for unsupported `org_type`.

**Step 4: Run test**

Run: `pytest backend/tests/test_approval_flow.py -v`

Expected: PASS.

### Task 6: API Router Skeletons And Seed Data

**Files:**
- Create: `backend/seed.py`
- Create: `backend/routers/auth.py`
- Create: `backend/routers/organization.py`
- Create: `backend/routers/task.py`
- Create: `backend/routers/question.py`
- Create: `backend/routers/approval.py`
- Create: `backend/routers/dashboard.py`
- Create: `backend/tests/test_api_skeleton.py`

**Step 1: Write API smoke tests**

Use `TestClient` to call `/api/auth/me`, `/api/organizations`, `/api/tasks`, `/api/questions`, `/api/approvals/pending`, and `/api/dashboard/summary`.

**Step 2: Implement skeleton routes**

Return stable sample JSON from seed helpers. Keep response shapes close to PRD/TRD fields.

**Step 3: Run tests**

Run: `pytest backend/tests/test_api_skeleton.py -v`

Expected: PASS.

### Task 7: Single-Port Frontend Serving

**Files:**
- Modify: `backend/main.py`
- Create: `frontend/index.html`
- Create: `frontend/css/style.css`
- Create: `frontend/js/api.js`
- Create: `frontend/js/auth.js`
- Create: `frontend/js/app.js`
- Create: `backend/tests/test_static_frontend.py`

**Step 1: Write failing static test**

```python
from fastapi.testclient import TestClient
from backend.main import app


def test_root_serves_frontend_html():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "기밀분류시스템" in response.text
```

**Step 2: Implement static serving**

Mount `/css`, `/js`, and `/assets` with `StaticFiles`. Add a root route returning `frontend/index.html`.

**Step 3: Run test**

Run: `pytest backend/tests/test_static_frontend.py -v`

Expected: PASS.

### Task 8: MVP UI Views

**Files:**
- Create: `frontend/js/spreadsheet.js`
- Create: `frontend/js/form.js`
- Create: `frontend/js/approval.js`
- Create: `frontend/js/dashboard.js`
- Modify: `frontend/js/app.js`
- Modify: `frontend/css/style.css`

**Step 1: Implement role navigation**

Create tabs or buttons for 입력자, 승인자, 관리자 mock views.

**Step 2: Implement inputter view**

Render a spreadsheet-like task table. Row click opens a detail modal. Show status badges for 기밀, 국가핵심기술, Compliance.

**Step 3: Implement approver and admin views**

Render pending approval list and dashboard summary cards using API responses.

**Step 4: Manual check**

Run: `uvicorn backend.main:app --reload --port 8000`

Open: `http://127.0.0.1:8000`

Expected: UI loads from the same port and API calls hit `/api/*`.

### Task 9: Docker And Documentation

**Files:**
- Create: `docker/Dockerfile`
- Create: `docker/docker-compose.yml`
- Create: `.env.example`
- Modify: `AGENTS.md`

**Step 1: Add Docker files**

Create a Python container that installs `backend/requirements.txt`, copies `backend/` and `frontend/`, and runs `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.

**Step 2: Add environment example**

Include `DATABASE_URL=sqlite:///./dev.db` and placeholders for SSO and mail variables.

**Step 3: Update contributor guide**

Replace future-tense commands with actual runnable commands.

**Step 4: Verify**

Run: `pytest backend/tests -v`

Run: `uvicorn backend.main:app --port 8000`

Expected: tests pass and app runs on one port.
