# 기밀분류시스템

FastAPI와 vanilla JavaScript로 구현한 단일 포트 기밀/국가핵심기술/Compliance 업무 분류 시스템입니다. 입력자는 파트 업무를 등록하고 판정 문항에 답변하며, 승인자는 파트 단위 승인 요청을 검토하고, 관리자는 조직/문항/툴팁/마감일/전체 현황을 관리합니다.

현재 앱은 FastAPI가 API와 정적 프론트엔드를 모두 제공하는 구조입니다. 기본 실행 URL은 `http://127.0.0.1:8000`이고, API는 `/api/*` 경로를 사용합니다.

## 현재 상태

핵심 업무 흐름은 구현되어 있습니다.

- 단일 포트 FastAPI 서버
- SQLite 개발 DB와 MySQL 호환 설정
- SQLAlchemy 모델과 Alembic 마이그레이션
- 사번 기반 로그인 화면과 역할별 라우팅
- 업무 CRUD, 상세 입력 모달, TSV/Excel 미리보기 저장 흐름
- 기밀/국가핵심기술 자동 판정과 필수 입력 검증
- 조직 유형별 승인 경로 생성
- 승인/반려/재제출/승인 후 수정 요청 흐름
- 승인자의 항목별 승인/반려 체크와 의견 입력
- 입력자가 본인이 추가한 행만 삭제하는 권한
- 관리자 조직 관리, 탭/drag-and-drop 문항 관리, 툴팁 관리, 마감일 관리, 대시보드, 전체 조회
- Excel 양식 다운로드, Excel import, Excel export
- SMTP 서비스 인터페이스, HTML 알림 템플릿, 발송 실패 로깅
- Docker 실행 파일과 사내 프라이빗 클라우드용 compose 파일
- Kubernetes 기본 배포 매니페스트

P0/P1 애플리케이션 기능과 LDAP/SAML 어댑터는 구현되어 있으며, 외부 인프라가 필요한 사내 IdP 접속 검증, 191개 파트/5,000건 성능 검증, Docker 실제 기동 검증은 운영 환경에서 별도 확인해야 합니다. 최신 상태는 [tasks.md](tasks.md)를 기준으로 합니다.

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Backend | Python, FastAPI, Uvicorn |
| Database | SQLAlchemy, SQLite, MySQL 호환, PyMySQL |
| Migration | Alembic |
| Frontend | Vanilla JavaScript, HTML, CSS |
| Test | pytest, Node.js built-in test runner |
| Packaging/Run | Docker, Docker Compose |

## 저장소 구조

```text
.
├── backend/
│   ├── main.py                  # FastAPI 앱, 정적 프론트엔드 서빙, 라우터 등록
│   ├── config.py                # 환경 변수 기반 런타임 설정
│   ├── database.py              # SQLAlchemy engine/session/Base
│   ├── dependencies.py          # 사용자/권한 의존성
│   ├── seed.py                  # 개발 seed 조직, 사용자, 문항, 업무
│   ├── models/                  # SQLAlchemy 모델
│   ├── routers/                 # API 라우터
│   ├── schemas/                 # 공통 schema
│   ├── scripts/init_db.py       # DB 초기화/seed 스크립트
│   ├── services/                # 판정, 승인 경로, 이메일, SSO 등 도메인 서비스
│   ├── migrations/              # Alembic 환경 및 revision
│   └── tests/                   # backend pytest
├── frontend/
│   ├── index.html               # 앱 shell
│   ├── css/style.css            # 전체 UI 스타일
│   ├── js/                      # 화면별 vanilla JS 모듈
│   ├── tests/                   # frontend node test
│   └── assets/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.private-cloud.yml
├── k8s/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── README.md
├── docs/
│   ├── docker.md
│   ├── sso-mysql-setup.md
│   ├── plans/
│   └── verification/            # Chrome DevTools 검증 스크린샷
├── prd.md                       # 제품 요구사항
├── spec.md                      # 기능 명세
├── trd.md                       # 기술 설계
├── tasks.md                     # 구현 백로그와 현재 상태
├── AGENTS.md                    # contributor/agent 가이드
├── alembic.ini
└── .env.example
```

## 주요 화면

현재 프론트엔드는 역할별 메뉴를 통해 아래 화면을 제공합니다.

| 화면 | 설명 |
| --- | --- |
| 로그인 | 사번 ID 기반 mock SSO 로그인 |
| 입력자 | 파트 업무 입력, 행 추가/수정/삭제, 상세 모달, 붙여넣기 미리보기, 승인 요청 |
| 내 파트 현황 | 입력자 파트의 승인/입력 상태 확인 |
| 그룹 조회 | 동일 그룹 내 다른 파트 업무 읽기 전용 조회 |
| 승인자 | 내 승인 대기 목록, 승인 상세 검토, 항목별 승인/반려 의견 입력 |
| 관리자 | 대시보드, 전체 데이터 조회, 조직 관리, 문항 관리, 예시/툴팁 관리, 마감일 관리 |

브라우저에서는 로그인 화면에서 seed 사번을 입력합니다. 개발 중 API 단위 역할 검증은 `X-Employee-Id` 헤더로 수행할 수 있습니다.

## 샘플 사용자

seed 데이터는 `backend/seed.py`에 정의되어 있습니다.

| 사번 | 역할 | 이름 | 설명 |
| --- | --- | --- | --- |
| `admin001` | `ADMIN` | 관리자 | 전체 관리 기능 접근 |
| `part001` | `INPUTTER` | 최파트장 | 파트 업무 입력자 |
| `group001` | `APPROVER` | 박그룹장 | 1단계 승인자 |
| `team001` | `APPROVER` | 이팀장 | 2단계 승인자 |
| `div001` | `APPROVER` | 김실장 | 3단계 승인자 |

API 호출 예시:

```powershell
Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/api/auth/me" `
  -Headers @{ "X-Employee-Id" = "part001" } `
  -UseBasicParsing
```

## 빠른 시작

### 1. Python 가상환경 생성

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

PowerShell 실행 정책 때문에 activate가 막히면 현재 세션에서만 정책을 완화합니다.

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\Activate.ps1
```

### 2. 의존성 설치

```powershell
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

### 3. 환경 변수 준비

개발 기본값은 `.env.example`과 동일하게 SQLite, mock SSO, disabled SMTP입니다.

```powershell
Copy-Item .env.example .env
```

필수는 아니지만, 명시적으로 지정하려면 다음 값을 사용합니다.

```powershell
$env:DATABASE_URL="sqlite:///./dev.db"
$env:SSO_MODE="mock"
$env:SMTP_MODE="disabled"
```

### 4. DB 초기화

앱 시작 시 DB가 없으면 자동으로 테이블과 seed 데이터를 생성합니다. 명시적으로 초기화하거나 재생성하려면 아래 명령을 사용합니다.

```powershell
python -m backend.scripts.init_db --reset
```

### 5. 개발 서버 실행

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

접속:

- App: `http://127.0.0.1:8000`
- Health: `http://127.0.0.1:8000/api/health`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Swagger UI: `http://127.0.0.1:8000/docs`

## 테스트

전체 backend 테스트:

```powershell
python -m pytest backend/tests
```

전체 frontend 테스트:

```powershell
node --test frontend/tests/*.test.mjs
```

특정 영역만 검증:

```powershell
python -m pytest backend/tests/test_approval_actions.py
python -m pytest backend/tests/test_task_validation_api.py
node --test frontend/tests/approvalReview.test.mjs
```

현재 확인된 최신 테스트 결과:

- backend: `98 passed`
- frontend: `48 passed`

## 주요 개발 명령어

| 명령 | 설명 |
| --- | --- |
| `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload` | 로컬 개발 서버 실행 |
| `python -m backend.scripts.init_db --reset` | SQLite 개발 DB 재생성 및 seed 주입 |
| `python -m pytest backend/tests` | backend 전체 테스트 |
| `node --test frontend/tests/*.test.mjs` | frontend 전체 테스트 |
| `alembic upgrade head` | 현재 `DATABASE_URL` 대상 DB에 마이그레이션 적용 |
| `docker compose -f docker/docker-compose.yml up --build` | 로컬 컨테이너 실행 |
| `docker compose -f docker/docker-compose.private-cloud.yml up --build -d` | 프라이빗 클라우드 설정으로 컨테이너 실행 |
| `kubectl apply -k k8s` | Kubernetes 매니페스트 배포 |

## API 개요

라우터는 `backend/routers/`에 나뉘어 있습니다. 모든 API는 `/api` prefix를 사용합니다.

| 경로 | 설명 |
| --- | --- |
| `/api/health` | 서버 상태 확인 |
| `/api/auth/login` | mock/LDAP 로그인 및 bearer token 발급 |
| `/api/auth/saml/acs` | SAML assertion 검증 및 bearer token 발급 |
| `/api/auth/me` | bearer token 기반 현재 사용자 조회, mock 모드 header fallback |
| `/api/organizations` | 조직 조회 |
| `/api/admin/organizations` | 관리자 조직 추가/수정/삭제/import |
| `/api/questions` | 입력 화면용 문항 조회 |
| `/api/admin/questions/*` | 관리자 문항 추가/삭제/순서 변경 |
| `/api/tooltips`, `/api/admin/tooltips/*` | 컬럼 예시/툴팁 조회 및 수정 |
| `/api/settings/deadline`, `/api/admin/settings/deadline` | 마감일 조회/수정 |
| `/api/tasks` | 업무 조회/등록/수정/삭제 |
| `/api/tasks/validate` | 승인 요청 전 업무 검증 |
| `/api/tasks/import` | Excel 업무 import |
| `/api/tasks/template` | Excel 양식 다운로드 |
| `/api/tasks/group` | 동일 그룹 업무 읽기 전용 조회 |
| `/api/approvals/*` | 승인 요청, 승인/반려, 이력, 승인 후 수정 요청 |
| `/api/dashboard/*` | 관리자 대시보드 집계 |
| `/api/admin/tasks` | 관리자 전체 업무 조회 |
| `/api/export/excel` | 필터 반영 Excel export |

## 핵심 비즈니스 규칙

### 기밀 판정

기밀 문항의 모든 답변이 `"해당 없음"`이면 `비기밀`입니다. 한 문항이라도 `"해당 없음"` 외 선택지가 있으면 `기밀`입니다. 기밀 판정 시 데이터 유형과 소유자/사용자 입력이 필수입니다.

### 국가핵심기술 판정

기밀 판정과 동일한 방식입니다. 모든 답변이 `"해당 없음"`이면 `비해당`, 하나라도 다른 선택지가 있으면 `해당`입니다. 해당 판정 시 데이터 유형과 소유자/사용자 입력이 필수입니다.

### Compliance

Compliance 이슈 체크 시 데이터 유형과 소유자/사용자 입력이 필수입니다.

### 승인 경로

조직의 `org_type`에 따라 승인 단계가 자동 생성됩니다.

| org_type | 승인 경로 |
| --- | --- |
| `NORMAL` | 그룹장 → 팀장 → 실장 |
| `TEAM_DIRECT` | 팀장 → 실장 |
| `DIV_DIRECT` | 실장 |

승인 요청 시 `approval_requests`와 `approval_steps`가 생성되고, 대상 업무는 `SUBMITTED` 상태가 됩니다. 최종 승인 시 업무는 `APPROVED`가 되고, 반려 시 요청과 업무가 `REJECTED`가 됩니다.

## 데이터베이스

개발 기본 DB는 `dev.db`입니다. 이 파일은 로컬 런타임 산출물이므로 `.gitignore`에 포함되어 있습니다.

주요 테이블:

- `organizations`
- `users`
- `task_entries`
- `task_question_checks`
- `confidential_questions`
- `national_tech_questions`
- `approval_requests`
- `approval_steps`
- `approval_task_reviews`
- `tooltips`
- `system_settings`

MySQL 연결 및 운영 준비는 [docs/sso-mysql-setup.md](docs/sso-mysql-setup.md)를 따릅니다.

## Alembic

현재 migration 환경은 `alembic.ini`와 `backend/migrations/`에 있습니다. `DATABASE_URL`을 대상 DB로 지정한 뒤 migration을 적용합니다.

```powershell
$env:DATABASE_URL="sqlite:///./dev.db"
alembic upgrade head
```

MySQL 예시:

```powershell
$env:DATABASE_URL="mysql+pymysql://credential_user:change-me@mysql.internal:3306/credential?charset=utf8mb4"
alembic upgrade head
```

## Docker 실행

로컬 개발 컨테이너:

```powershell
docker compose -f docker/docker-compose.yml up --build
```

프라이빗 클라우드 설정:

```powershell
Copy-Item .env.example .env.private-cloud
docker compose -f docker/docker-compose.private-cloud.yml up --build -d
```

중지:

```powershell
docker compose -f docker/docker-compose.yml down
```

자세한 내용은 [docs/docker.md](docs/docker.md)를 참고합니다.

## Kubernetes 배포

Kubernetes 기본 매니페스트는 `k8s/`에 있습니다. Kustomize entrypoint는 `k8s/kustomization.yaml`입니다.

```powershell
kubectl apply -f k8s/namespace.yaml
kubectl -n credential create secret generic credential-secrets `
  --from-literal=DATABASE_URL="mysql+pymysql://credential_user:change-me@mysql.internal:3306/credential?charset=utf8mb4"
kubectl apply -k k8s
kubectl -n credential rollout status deployment/credential-app
```

기본 이미지는 `credential-classification:latest`입니다. 운영에서는 registry 경로와 불변 tag로 교체합니다. 상세 절차는 [k8s/README.md](k8s/README.md)를 참고합니다.

## SSO와 MySQL 운영 연결

운영 연결 절차는 [docs/sso-mysql-setup.md](docs/sso-mysql-setup.md)에 상세히 정리되어 있습니다.

현재 중요한 제약은 다음과 같습니다.

- 로그인 화면과 사번 기반 mock SSO 흐름은 개발용으로 유지됩니다.
- `SSO_MODE=ldap`는 `ldap3`로 AD/LDAP bind를 수행하고, `SSO_MODE=saml`은 `python3-saml`로 ACS assertion을 검증합니다.
- 인증 성공 후 백엔드는 HMAC 서명 bearer token을 발급하며 프론트엔드는 이후 API에 `Authorization: Bearer ...`를 전송합니다.
- 개발 mock 모드에서만 `/api/auth/me`가 `X-Employee-Id` fallback을 허용합니다. 운영 LDAP/SAML 모드에서는 bearer token이 필요합니다.
- 운영 전에는 사내 IdP URL, 인증서, bind DN, 사용자 속성명, 방화벽/DNS를 실제 환경에서 검증해야 합니다.

## 환경 변수

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./dev.db` | SQLAlchemy DB URL |
| `SSO_MODE` | `mock` | `mock`, `ldap`, `saml` |
| `SSO_PROVIDER_URL` | empty | LDAP/SAML provider URL |
| `SSO_CLIENT_ID` | empty | SSO client id |
| `SSO_CLIENT_SECRET` | empty | SSO client secret |
| `SSO_TOKEN_SECRET` | empty | bearer token 서명 secret. 없으면 `SSO_CLIENT_SECRET` fallback |
| `SSO_TOKEN_EXPIRE_MINUTES` | `480` | bearer token 만료 시간 |
| `SSO_ADMIN_EMPLOYEE_IDS` | `admin001` | 콤마 구분 관리자 사번 |
| `SSO_LDAP_BIND_DN_TEMPLATE` | `{employee_id}` | LDAP bind DN 템플릿 |
| `SSO_LDAP_SEARCH_BASE` | empty | LDAP 사용자 조회 base DN |
| `SSO_LDAP_SEARCH_FILTER` | `(sAMAccountName={employee_id})` | LDAP 사용자 조회 filter |
| `SSO_LDAP_EMPLOYEE_ATTR` | `sAMAccountName` | LDAP 사번 속성 |
| `SSO_LDAP_NAME_ATTR` | `displayName` | LDAP 이름 속성 |
| `SSO_SAML_SP_ENTITY_ID` | empty | SAML SP entity id |
| `SSO_SAML_ACS_URL` | empty | `/api/auth/saml/acs` 외부 URL |
| `SSO_SAML_IDP_ENTITY_ID` | empty | SAML IdP entity id |
| `SSO_SAML_SSO_URL` | empty | SAML IdP SSO URL |
| `SSO_SAML_X509_CERT` | empty | SAML IdP signing certificate |
| `SSO_SAML_EMPLOYEE_ATTR` | `employee_id` | SAML 사번 attribute |
| `SMTP_MODE` | `disabled` | `disabled` 또는 `smtp` |
| `SMTP_HOST` | empty | SMTP host |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USERNAME` | empty | SMTP username |
| `SMTP_PASSWORD` | empty | SMTP password |

`SSO_MODE=ldap|saml`이면 각 모드의 provider URL, token secret, LDAP/SAML 세부 값이 필수입니다. `SMTP_MODE=smtp`이면 SMTP 관련 값이 필수입니다. 누락 시 앱 시작 단계에서 명확한 오류를 발생시킵니다.

## 프론트엔드 개발 참고

프론트엔드는 번들러 없이 ES module로 동작합니다. `frontend/js/app.js`가 현재 사용자 정보를 가져오고 역할별 화면 모듈을 렌더링합니다.

주요 모듈:

- `spreadsheet.js`: 입력자 업무 표, 붙여넣기 미리보기, 승인 요청
- `form.js`: 상세 입력 모달과 판정 문항 UI
- `approval.js`: 승인 대기 목록과 상세 검토
- `dashboard.js`: 관리자 대시보드
- `adminTaskQuery.js`: 전체 데이터 조회
- `organizationAdmin.js`: 조직 관리
- `questionAdmin.js`: 기밀/국가핵심기술 문항 관리
- `tooltipAdmin.js`: 컬럼 예시 관리
- `deadlineAdmin.js`: 입력 마감일 관리
- `groupReadonly.js`: 동일 그룹 조회

프론트엔드 테스트는 Node.js의 built-in test runner를 사용합니다. 별도 `npm install`은 필요하지 않습니다.

## 품질 및 검증 자료

Chrome DevTools 기반 검증 스크린샷은 `docs/verification/`에 있습니다. 예시는 다음과 같습니다.

- 입력 화면 검증
- 상세 모달 검증
- 붙여넣기 미리보기 검증
- 승인 상세 검토 검증
- 관리자 대시보드 검증
- 반려 항목 필터/상단 고정 검증

자동 테스트 외에 UI 변경을 할 때는 최소한 다음을 확인합니다.

1. `python -m pytest backend/tests`
2. `node --test frontend/tests/*.test.mjs`
3. 브라우저에서 `http://127.0.0.1:8000` 접속
4. DevTools Console 에러 없음
5. 주요 API Network 응답 2xx
6. 입력자/승인자/관리자 주요 화면 레이아웃 깨짐 없음

## 알려진 미완료 항목

최신 기준은 [tasks.md](tasks.md)를 확인합니다. README 작성 시점의 핵심 미완료 항목은 다음과 같습니다.

- 사내 IdP/AD 실환경 접속 검증
- 191개 파트/5,000건 업무 기준 성능 검증
- Docker 실제 기동 검증
- 운영 환경 중앙 감사 로그 적재

## 보안 주의사항

- `.env`, `.env.private-cloud`, DB 비밀번호, SSO token/client secret, SAML 인증서, SMTP 비밀번호는 커밋하지 않습니다.
- `.env.example`만 템플릿으로 커밋합니다.
- 운영 DB 계정은 앱 DB에 필요한 권한만 부여합니다.
- 운영에서는 `SSO_MODE=ldap|saml`과 bearer token을 사용하고, mock 모드의 `X-Employee-Id` fallback을 외부에 노출하지 않습니다.
- 운영 환경에서는 HTTPS, reverse proxy header 제한, DB TLS, 접근 로그/감사 로그 정책을 적용해야 합니다.

## 문제 해결

### 서버가 시작되지 않음

환경 변수 누락을 먼저 확인합니다.

```powershell
$env:SSO_MODE
$env:DATABASE_URL
$env:SMTP_MODE
```

`SSO_MODE=ldap` 또는 `saml`인데 provider URL, token secret, LDAP/SAML 필수 값이 비어 있으면 시작 중 오류가 납니다.

### DB를 새로 만들고 싶음

개발 환경에서만 reset을 사용합니다.

```powershell
python -m backend.scripts.init_db --reset
```

운영 DB에서는 `--reset`을 사용하지 않습니다.

### 브라우저에 관리자만 표시됨

로그아웃 후 로그인 화면에서 `part001`, `group001`, `team001`, `div001`, `admin001` 중 하나를 입력합니다. API 단위로 다른 역할을 테스트하려면 `X-Employee-Id` 헤더를 사용합니다.

### Excel import/export가 실패함

업무 import는 `.xlsx` 파일을 기대합니다. export는 현재 필터 조건을 query string으로 전달합니다. 실패 시 Network 응답 코드와 `/api/tasks/import`, `/api/export/excel` 응답을 확인합니다.

### 테스트 중 캐시/DB 파일이 생김

`__pycache__/`, `.pytest_cache/`, `dev.db`, `logs/`, `output/` 등은 `.gitignore`에 포함되어 있습니다. 커밋 대상에는 포함하지 않습니다.

## 관련 문서

- [prd.md](prd.md): 제품 요구사항
- [spec.md](spec.md): 기능 명세
- [trd.md](trd.md): 기술 설계
- [tasks.md](tasks.md): 구현 백로그와 현재 상태
- [AGENTS.md](AGENTS.md): 저장소 기여 가이드
- [docs/docker.md](docs/docker.md): Docker 실행 가이드
- [docs/sso-mysql-setup.md](docs/sso-mysql-setup.md): SSO/MySQL 연결 가이드
- [docs/operations.md](docs/operations.md): 운영 정책 및 검증 가이드
- [k8s/README.md](k8s/README.md): Kubernetes 배포 가이드

## 기여 전 체크리스트

변경 전후로 다음을 확인합니다.

```powershell
python -m pytest backend/tests
node --test frontend/tests/*.test.mjs
git status --short
```

기능을 완료했다고 표시하기 전에 `tasks.md`의 해당 항목을 기준으로 요구사항과 구현을 대조합니다. 단순히 테스트가 통과해도 SPEC 항목이 빠져 있으면 완료로 표시하지 않습니다.
