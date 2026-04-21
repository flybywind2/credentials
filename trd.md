# 📘 TRD (Technical Requirements Document)

## 1. 시스템 아키텍처

### 1.1 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| Backend | FastAPI (Python) | REST API 서버 |
| Frontend | Vanilla JavaScript | 프레임워크 미사용, 순수 JS |
| Database (Production) | MySQL | 사내 프라이빗 클라우드 |
| Database (Test) | SQLite | 로컬 개발/테스트 환경 |
| 인증 | AD SSO (LDAP/SAML) | 사내 Active Directory 연동 |
| 이메일 | SMTP | 사내 SMTP 서버, {ID}@samsung.com |
| 배포 | 사내 프라이빗 클라우드 | Docker 컨테이너 기반 권장 |

### 1.2 아키텍처 다이어그램

```
[사용자 브라우저 (Vanilla JS, 1920x1080)]
        ↕ HTTPS
[FastAPI 서버 (REST API)]
    ↕           ↕           ↕
[MySQL DB]  [AD SSO]   [SMTP 서버]
                        ({ID}@samsung.com)
```

### 1.3 프로젝트 구조

```
project-root/
├── backend/
│   ├── main.py                  # FastAPI 앱 진입점
│   ├── config.py                # 환경 설정 (DB, SMTP, SSO 등)
│   ├── database.py              # DB 연결 및 세션 관리
│   ├── models/                  # SQLAlchemy ORM 모델
│   │   ├── organization.py      # 조직 구조 모델
│   │   ├── task.py              # 업무 데이터 모델
│   │   ├── question.py          # 문항 관리 모델
│   │   ├── approval.py          # 승인 프로세스 모델
│   │   ├── user.py              # 사용자/역할 모델
│   │   └── tooltip.py           # 컬럼 예시 모델
│   ├── routers/                 # API 라우터
│   │   ├── auth.py              # 인증 관련 API
│   │   ├── organization.py      # 조직 관리 API
│   │   ├── task.py              # 업무 데이터 CRUD API
│   │   ├── approval.py          # 승인 프로세스 API
│   │   ├── admin.py             # 관리자 기능 API
│   │   ├── dashboard.py         # 대시보드 API
│   │   └── export.py            # Excel Export API
│   ├── services/                # 비즈니스 로직
│   │   ├── classification.py    # 기밀/국가핵심기술 판정 로직
│   │   ├── approval_flow.py     # 승인 경로 결정 로직
│   │   ├── email_service.py     # 이메일 발송 서비스
│   │   ├── import_service.py    # CSV/Excel Import 서비스
│   │   └── export_service.py    # Excel Export 서비스
│   ├── schemas/                 # Pydantic 스키마
│   ├── middleware/               # 인증, 권한 미들웨어
│   ├── tests/                   # 테스트 (SQLite 사용)
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css            # 무채색 기반 스타일 (1920x1080 최적화)
│   ├── js/
│   │   ├── app.js               # 메인 앱 로직
│   │   ├── api.js               # API 호출 모듈
│   │   ├── auth.js              # SSO 인증 처리
│   │   ├── spreadsheet.js       # 스프레드시트 뷰
│   │   ├── form.js              # 상세 입력 폼 팝업
│   │   ├── clipboard.js         # 클립보드 붙여넣기 처리
│   │   ├── dashboard.js         # 대시보드 차트/통계
│   │   ├── approval.js          # 승인 관련 UI
│   │   ├── admin.js             # 관리자 기능 UI
│   │   └── utils.js             # 유틸리티 함수
│   └── assets/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── docs/
    ├── PRD.md
    ├── TRD.md
    └── SPEC.md
```

---

## 2. 데이터베이스 설계

### 2.1 ER 다이어그램

```
[organizations] 1──N [task_entries]
[organizations] 1──N [approval_requests]
[users] 1──N [task_entries]
[users] 1──N [approval_requests]
[confidential_questions] N──M [task_question_checks]
[national_tech_questions] N──M [task_question_checks]
[task_entries] 1──N [task_question_checks]
[approval_requests] 1──N [approval_steps]
```

### 2.2 테이블 정의

**organizations (조직 구조) 【변경】**

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 조직 ID |
| division_name | VARCHAR(100) | NOT NULL | 실명 |
| division_head_name | VARCHAR(50) | NOT NULL | 실장명 |
| division_head_id | VARCHAR(20) | NOT NULL | 실장 사번ID |
| team_name | VARCHAR(100) | NULLABLE | 팀명 (실 직속 시 NULL) |
| team_head_name | VARCHAR(50) | NULLABLE | 팀장명 |
| team_head_id | VARCHAR(20) | NULLABLE | 팀장 사번ID |
| group_name | VARCHAR(100) | NULLABLE | 그룹명 (팀 직속 시 NULL) |
| group_head_name | VARCHAR(50) | NULLABLE | 그룹장명 |
| group_head_id | VARCHAR(20) | NULLABLE | 그룹장 사번ID |
| part_name | VARCHAR(100) | NOT NULL | 파트명 |
| part_head_name | VARCHAR(50) | NOT NULL | 파트장명 |
| part_head_id | VARCHAR(20) | NOT NULL | 파트장 사번ID |
| org_type | ENUM('NORMAL','TEAM_DIRECT','DIV_DIRECT') | NOT NULL | 조직 유형 |
| created_at | DATETIME | DEFAULT NOW() | 생성일시 |
| updated_at | DATETIME | ON UPDATE NOW() | 수정일시 |

**users (사용자) 【변경】**

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 사용자 ID |
| employee_id | VARCHAR(20) | UNIQUE, NOT NULL | 사번ID |
| name | VARCHAR(50) | NOT NULL | 이름 |
| email | VARCHAR(100) | GENERATED | {employee_id}@samsung.com (자동 생성) |
| role | ENUM('ADMIN','INPUTTER','APPROVER') | NOT NULL | 역할 |
| organization_id | INT | FK → organizations.id | 소속 조직 |
| created_at | DATETIME | DEFAULT NOW() | 생성일시 |

**task_entries (업무 데이터 - 핵심 테이블)**

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 업무 ID |
| organization_id | INT | FK → organizations.id, NOT NULL | 소속 조직 |
| created_by | INT | FK → users.id, NOT NULL | 입력자 |
| sub_part | VARCHAR(100) | | 소파트 |
| major_task | VARCHAR(200) | NOT NULL | 대업무 |
| detail_task | VARCHAR(500) | NOT NULL | 세부업무 |
| is_confidential | BOOLEAN | DEFAULT FALSE | 기밀 여부 (자동 판정) |
| conf_data_type | TEXT | NULLABLE | 기밀-데이터 유형 |
| conf_owner_user | ENUM('OWNER','USER') | NULLABLE | 기밀-소유자/사용자 |
| is_national_tech | BOOLEAN | DEFAULT FALSE | 국가핵심기술 여부 (자동 판정) |
| ntech_data_type | TEXT | NULLABLE | 국가핵심기술-데이터 유형 |
| ntech_owner_user | ENUM('OWNER','USER') | NULLABLE | 국가핵심기술-소유자/사용자 |
| is_compliance | BOOLEAN | DEFAULT FALSE | Compliance 이슈 해당 여부 |
| comp_data_type | TEXT | NULLABLE | Compliance-데이터 유형 |
| comp_owner_user | ENUM('OWNER','USER') | NULLABLE | Compliance-소유자/사용자 |
| storage_location | VARCHAR(300) | | 데이터 보관 장소 |
| related_menu | VARCHAR(300) | | 관련 메뉴 |
| share_scope | ENUM('DIVISION_BU','BUSINESS_UNIT','ORG_UNIT') | | 공유범위 (부문/사업부/실·팀·그룹) |
| status | ENUM('DRAFT','SUBMITTED','APPROVED','REJECTED') | DEFAULT 'DRAFT' | 상태 |
| created_at | DATETIME | DEFAULT NOW() | 생성일시 |
| updated_at | DATETIME | ON UPDATE NOW() | 수정일시 |

**confidential_questions (기밀 해당 문항) 【변경】**

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 문항 ID |
| question_text | VARCHAR(500) | NOT NULL | 문항 내용 |
| options | JSON | NOT NULL | 객관식 선택지 배열 ("해당 없음" 자동 포함) |
| is_active | BOOLEAN | DEFAULT TRUE | 활성 여부 |
| sort_order | INT | DEFAULT 0 | 정렬 순서 |
| created_at | DATETIME | DEFAULT NOW() | 생성일시 |

**national_tech_questions (국가핵심기술 판단 문항) 【변경】**

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 문항 ID |
| question_text | VARCHAR(500) | NOT NULL | 문항 내용 |
| options | JSON | NOT NULL | 객관식 선택지 배열 ("해당 없음" 자동 포함) |
| is_active | BOOLEAN | DEFAULT TRUE | 활성 여부 |
| sort_order | INT | DEFAULT 0 | 정렬 순서 |
| created_at | DATETIME | DEFAULT NOW() | 생성일시 |

**task_question_checks (업무-문항 체크 매핑)**

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | ID |
| task_entry_id | INT | FK → task_entries.id, NOT NULL | 업무 ID |
| question_type | ENUM('CONFIDENTIAL','NATIONAL_TECH') | NOT NULL | 문항 유형 |
| question_id | INT | NOT NULL | 문항 ID |
| selected_options | JSON | NOT NULL | 선택된 옵션 배열 |
| is_not_applicable | BOOLEAN | DEFAULT FALSE | "해당 없음"만 선택 여부 |
| created_at | DATETIME | DEFAULT NOW() | 생성일시 |

**approval_requests (승인 요청)**

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | 승인 요청 ID |
| organization_id | INT | FK → organizations.id, NOT NULL | 대상 조직 |
| requested_by | INT | FK → users.id, NOT NULL | 요청자 |
| status | ENUM('PENDING','IN_PROGRESS','APPROVED','REJECTED') | DEFAULT 'PENDING' | 전체 상태 |
| current_step | INT | DEFAULT 1 | 현재 승인 단계 |
| total_steps | INT | NOT NULL | 전체 승인 단계 수 |
| created_at | DATETIME | DEFAULT NOW() | 요청일시 |
| updated_at | DATETIME | ON UPDATE NOW() | 수정일시 |

**approval_steps (승인 단계 상세)**

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | ID |
| approval_request_id | INT | FK → approval_requests.id, NOT NULL | 승인 요청 ID |
| step_order | INT | NOT NULL | 단계 순서 |
| approver_employee_id | VARCHAR(20) | NOT NULL | 승인자 사번ID |
| approver_name | VARCHAR(50) | NOT NULL | 승인자명 |
| approver_role | VARCHAR(50) | NOT NULL | 승인자 직책 |
| status | ENUM('WAITING','APPROVED','REJECTED') | DEFAULT 'WAITING' | 단계 상태 |
| reject_reason | TEXT | NULLABLE | 반려 사유 |
| acted_at | DATETIME | NULLABLE | 처리일시 |

**column_tooltips (컬럼 예시 툴팁)**

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | ID |
| column_key | VARCHAR(100) | UNIQUE, NOT NULL | 컬럼 식별키 |
| column_name | VARCHAR(100) | NOT NULL | 컬럼 표시명 |
| tooltip_text | TEXT | | 예시/설명 텍스트 |
| updated_at | DATETIME | ON UPDATE NOW() | 수정일시 |

**deadline_settings (마감일 설정)**

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | ID |
| deadline_date | DATE | NOT NULL | 마감일 |
| description | VARCHAR(200) | | 설명 |
| is_active | BOOLEAN | DEFAULT TRUE | 활성 여부 |
| created_at | DATETIME | DEFAULT NOW() | 생성일시 |

---

## 3. API 설계

### 3.1 인증 API

`POST /api/auth/login` — SSO 인증 후 JWT 토큰 발급. `GET /api/auth/me` — 현재 로그인 사용자 정보 및 역할 조회.

### 3.2 조직 관리 API 【변경】

`POST /api/admin/organizations/import` — CSV 파일로 조직 구조 일괄 등록 (사번ID, 이름 포함. 이메일은 {ID}@samsung.com 자동 생성). `GET /api/organizations` — 조직 목록 조회 (필터링 지원). `POST /api/admin/organizations` — 조직 추가 (각 직책자 이름+사번ID 입력). `PUT /api/admin/organizations/{id}` — 조직 수정. `DELETE /api/admin/organizations/{id}` — 조직 삭제.

### 3.3 업무 데이터 API

`GET /api/tasks?org_id={id}` — 조직별 업무 목록 조회. `POST /api/tasks` — 업무 데이터 단건 등록. `POST /api/tasks/bulk` — 업무 데이터 일괄 등록 (클립보드/Excel Import). `PUT /api/tasks/{id}` — 업무 데이터 수정. `DELETE /api/tasks/{id}` — 업무 데이터 삭제. `POST /api/tasks/validate` — 붙여넣기/Import 데이터 검증 (오류 행 반환). `GET /api/tasks/template` — Excel 양식 다운로드.

### 3.4 문항 관리 API

`GET /api/questions/confidential` — 기밀 해당 문항 목록 조회. `POST /api/admin/questions/confidential` — 기밀 문항 추가 ("해당 없음" 선택지 자동 포함). `DELETE /api/admin/questions/confidential/{id}` — 기밀 문항 삭제. `GET /api/questions/national-tech` — 국가핵심기술 문항 목록 조회. `POST /api/admin/questions/national-tech` — 국가핵심기술 문항 추가 ("해당 없음" 선택지 자동 포함). `DELETE /api/admin/questions/national-tech/{id}` — 국가핵심기술 문항 삭제.

### 3.5 승인 API

`POST /api/approvals/submit?org_id={id}` — 파트 단위 승인 요청 제출. `GET /api/approvals/pending` — 내 승인 대기 목록 조회. `POST /api/approvals/{id}/approve` — 승인 처리. `POST /api/approvals/{id}/reject` — 반려 처리 (body: reject_reason 필수). `GET /api/approvals/{id}/history` — 승인 이력 조회.

### 3.6 대시보드 API

`GET /api/dashboard/summary` — 전체 현황 요약 통계. `GET /api/dashboard/completion-rate` — 부서별 입력 완료율. `GET /api/dashboard/approval-status` — 승인 진행 현황. `GET /api/dashboard/classification-ratio` — 기밀/국가핵심기술/Compliance 통합 비율.

### 3.7 관리자 API

`GET /api/admin/tooltips` — 전체 컬럼 예시 목록 조회. `PUT /api/admin/tooltips/{column_key}` — 컬럼 예시 수정. `POST /api/admin/deadline` — 마감일 설정. `GET /api/admin/deadline` — 현재 마감일 조회.

### 3.8 Export API

`GET /api/export/excel?filters={}` — 필터 조건에 따른 Excel 다운로드. 필터 파라미터로 organization_id, approval_status, division, team, group 등을 지원한다.

---

## 4. 인증 및 보안

### 4.1 SSO 연동 【변경】

사내 AD SSO와 LDAP 또는 SAML 2.0 프로토콜로 연동한다. SSO 인증 성공 시 사번ID를 기준으로 사용자를 식별하고, organizations 테이블의 사번ID 매칭을 통해 역할과 소속 조직을 자동 매핑한다. JWT 토큰을 발급하며, API 요청 시 Authorization 헤더에 포함하여 전송한다. 이메일은 `{사번ID}@samsung.com`으로 자동 구성한다.

### 4.2 권한 제어

모든 API에 미들웨어를 통한 역할 기반 접근 제어(RBAC)를 적용한다. 데이터 조회 시 조직 계층에 따른 접근 범위를 서버 사이드에서 강제한다. 관리자 전용 API는 `/api/admin/*` 경로로 분리하고, ADMIN 역할만 접근 가능하도록 한다.

---

## 5. 이메일 서비스 【변경】

### 5.1 발송 시점 및 수신자

| 이벤트 | 수신자 | 이메일 주소 |
|--------|--------|-------------|
| 승인 요청 제출 | 다음 단계 승인자 | {승인자 사번ID}@samsung.com |
| 단계별 승인 완료 | 다음 단계 승인자 + 관리자 | 각각 {사번ID}@samsung.com |
| 최종 승인 완료 | 입력자(파트장) + 관리자 | 각각 {사번ID}@samsung.com |
| 반려 | 입력자(파트장) | {파트장 사번ID}@samsung.com |

### 5.2 구현

FastAPI의 BackgroundTasks 또는 별도 비동기 큐를 활용하여 이메일 발송이 API 응답을 지연시키지 않도록 한다. 이메일 템플릿은 HTML 형식으로 작성하며, 승인 요청 건의 조직명, 상태, 반려 사유 등을 포함한다.

---

## 6. 테스트 전략

개발/테스트 환경에서는 SQLite를 사용하며, `config.py`에서 환경 변수로 DB 종류를 분기한다. SQLAlchemy ORM을 사용하여 MySQL과 SQLite 간 호환성을 확보한다. 단위 테스트(pytest)에서 API 엔드포인트별 테스트를 작성하며, 기밀 판정 로직("해당 없음" 처리 포함), 승인 경로 결정 로직, 데이터 검증 로직에 대한 테스트를 중점적으로 작성한다.
