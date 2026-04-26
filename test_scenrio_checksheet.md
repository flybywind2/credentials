# SSO broker 및 mail API 연동 테스트 시나리오 체크시트

작성일: 2026-04-26
대상 프로젝트: 기밀분류시스템  
목적: 회사 환경에서 SSO broker와 사내 mail API를 연결한 뒤, 자동 테스트와 직접 동작 테스트로 운영 가능 여부를 확인한다.

## 0. 테스트 원칙

- 실제 사번, SSO secret, 메일 API key, DB 비밀번호는 이 파일에 기록하지 않는다.
- 운영 연동 테스트는 테스트용 조직/파트/사번/메일 수신자를 사용한다.
- 환경변수 변경 후에는 반드시 서버를 재시작한다.
- 메일 발송 테스트는 처음에는 본인 또는 테스트 수신자만 포함된 조직 데이터로 수행한다.
- 실패 시 화면 메시지, 서버 로그, API 응답, mail API 응답을 같이 기록한다.

## 1. 사전 준비 체크리스트

| 체크 | 항목 | 확인 내용 | 결과/메모 |
| --- | --- | --- | --- |
| [ ] | Python 환경 | `python --version`이 3.10 계열인지 확인 |  |
| [ ] | 패키지 설치 | `pip install -r backend/requirements.txt` 완료 |  |
| [ ] | DB 연결 | `DATABASE_URL`이 회사 테스트 DB 또는 로컬 검증 DB를 가리킴 |  |
| [ ] | 앱 URL | `APP_BASE_URL`이 회사에서 접근 가능한 URL로 설정됨 |  |
| [ ] | 조직 데이터 | 테스트 사번이 `users` 또는 `organizations`의 파트장/그룹장/팀장/실장 ID와 매핑됨 |  |
| [ ] | 관리자 사번 | `SSO_ADMIN_EMPLOYEE_IDS`에 테스트 관리자 사번이 포함됨 |  |
| [ ] | 메일 수신자 | 테스트 승인자 사번의 메일 주소가 `{employee_id}@samsung.com` 형태로 수신 가능 |  |
| [ ] | 보안 | secret/비밀번호/API key는 git diff에 포함되지 않음 |  |

## 2. 환경변수 설정 체크

### 공통

| 체크 | 변수 | 예시/설명 | 결과/메모 |
| --- | --- | --- | --- |
| [ ] | `DATABASE_URL` | 예: `mysql+pymysql://...` 또는 `sqlite:///./dev.db` |  |
| [ ] | `APP_BASE_URL` | 승인 메일의 바로가기 링크 기준 URL |  |
| [ ] | `SSO_MODE` | 운영은 `broker`, 로컬 직접 테스트는 `mock` |  |
| [ ] | `BROKER_URL` | 예: `https://sso.example.com/svc0` |  |
| [ ] | `SERVICE_URL` | 예: `https://example1.com` |  |
| [ ] | `SSO_TOKEN_SECRET` | mock token 서명용 secret. 운영에서도 임의 긴 값 사용 권장 |  |
| [ ] | `SSO_ADMIN_EMPLOYEE_IDS` | 쉼표 구분 관리자 사번 |  |
| [ ] | `MAIL_MODE` | `disabled` 또는 `mail_api` |  |

### Broker SSO

| 체크 | 변수 | 확인 내용 | 결과/메모 |
| --- | --- | --- | --- |
| [ ] | `SSO_MODE=broker` | 앱이 `BROKER_URL`로 이동해 SSO 인증 시작 |  |
| [ ] | callback URL | 인증 후 `SERVICE_URL/?loginid=...&deptname=...&username=...`으로 돌아옴 |  |
| [ ] | `SSO_BROKER_DEPT_HEADER` | 기본값 `deptname`, 실/팀/그룹 소속명 매핑에 사용 |  |

### Mail API

| 체크 | 변수 | 확인 내용 | 결과/메모 |
| --- | --- | --- | --- |
| [ ] | `MAIL_MODE=mail_api` | 사내 메일 라우터 사용 |  |
| [ ] | `MAIL_API_BASE_URL` | `mail.net` 또는 `https://mail.net/send_mail` 형식 |  |
| [ ] | `MAIL_API_SYSTEM_ID` | 필요 시 요청 header `System-ID`로 전달 |  |
| [ ] | `MAIL_API_TIMEOUT_SECONDS` | 기본 10초, 사내망 지연 시 조정 |  |

## 3. 자동 테스트 시나리오

회사 환경변수 적용 전후로 아래 명령을 실행한다.

```powershell
python -m pytest backend/tests/test_sso_adapter.py backend/tests/test_auth_login.py backend/tests/test_email_and_environment.py -p no:cacheprovider
python -m pytest backend/tests/test_user_admin.py backend/tests/test_permissions.py backend/tests/test_same_group_readonly.py -p no:cacheprovider
python -m pytest backend/tests/test_approval_notifications.py backend/tests/test_approval_submit.py backend/tests/test_approval_actions.py -p no:cacheprovider
node --test frontend\tests\*.test.mjs
```

| 체크 | 시나리오 | 기대 결과 | 결과/메모 |
| --- | --- | --- | --- |
| [ ] | SSO adapter 단위 테스트 | mock/broker adapter 선택 및 제거된 SSO mode 차단 로직 통과 |  |
| [ ] | 로그인 API 테스트 | mock `/api/auth/login`, token 발급, `/api/auth/me` 통과 |  |
| [ ] | Broker 인증 테스트 | callback query 기반 session 생성 후 `/api/auth/me` 통과, 외부 fallback 무시 |  |
| [ ] | 담당조직 변경 테스트 | 관리자 사용자 권한관리에서 담당조직 변경 후 `auth/me`, 조직 목록, 업무 조회 범위가 변경됨 |  |
| [ ] | 기존 세션 갱신 테스트 | 담당조직 변경 전 로그인 브라우저도 새로고침 후 DB의 최신 담당조직이 반영됨 |  |
| [ ] | 조직장 자동계정 override 테스트 | 조직장 자동계정을 관리 사용자로 등록하면 기존 자동 조직장 범위가 섞이지 않음 |  |
| [ ] | 메일 서비스 테스트 | disabled/mail_api 선택과 payload mapping 통과 |  |
| [ ] | 승인 알림 테스트 | 제출/승인/반려 시 알림 경계 로직 통과 |  |
| [ ] | 프론트 테스트 | 로그인, 라우팅, 승인/입력 화면 회귀 없음 |  |

## 4. 서버 실행 및 기초 점검

```powershell
uvicorn backend.main:app --reload --port 8000
```

| 체크 | 점검 | 방법 | 기대 결과 | 결과/메모 |
| --- | --- | --- | --- | --- |
| [ ] | Health check | 브라우저 또는 `Invoke-WebRequest http://127.0.0.1:8000/api/health` | 200 응답 |  |
| [ ] | 정적 화면 | `http://127.0.0.1:8000` 접속 | 로그인 화면 표시 |  |
| [ ] | 환경 누락 없음 | 서버 시작 로그 확인 | 필수 환경변수 오류 없음 |  |
| [ ] | DB 연결 | 로그인 전후 주요 API 호출 | DB connection 오류 없음 |  |

## 5. SSO 직접 동작 테스트

### Mock 직접 테스트

| 체크 | 시나리오 | 방법 | 기대 결과 | 결과/메모 |
| --- | --- | --- | --- | --- |
| [ ] | 사용자 전환 | 로그인 화면에서 `part001`, `group001`, `team001`, `admin001` 순서로 로그인 | `/api/auth/me`가 방금 선택한 사용자로 응답 |  |
| [ ] | stale token 무시 | 이전 사용자 token이 남은 상태에서 다른 사용자 로그인 | cookie/header의 현재 mock 사용자가 우선 적용 |  |
| [ ] | 로그아웃 | 로그아웃 버튼 클릭 | mock cookie/token 삭제, 로그인 화면 이동 |  |

### Broker SSO

| 체크 | 시나리오 | 방법 | 기대 결과 | 결과/메모 |
| --- | --- | --- | --- | --- |
| [ ] | 인증 헤더 정상 매핑 | SSO broker를 거쳐 앱 접속 | 사용자명/역할이 실제 사번 기준으로 표시 |  |
| [ ] | callback query 확인 | 인증 후 주소가 `SERVICE_URL/?loginid=...&deptname=...&username=...` 형태인지 확인 | 실제 값이 들어오고 앱 접속 후 주소창에서 query 제거 |  |
| [ ] | broker session 생성 | callback 후 Network에서 `/api/auth/broker/session` 확인 | 200 응답, 현재 사용자 세션 생성 |  |
| [ ] | `/api/auth/me` 확인 | broker 경유 상태에서 `/api/auth/me` 호출 | 현재 사용자 JSON이 실제 사번과 일치 |  |
| [ ] | `deptname` 단일 파트 매핑 | `deptname`이 CSV의 실/팀/그룹/파트 중 하나와 매칭되고 후보 파트가 1개 | 해당 파트 소속 입력자로 접속 |  |
| [ ] | `deptname` 미등록 | `deptname`이 CSV 조직 정보에 없음 | `소속 정보 등록 필요` 모달 표시 |  |
| [ ] | `deptname` 다중 후보 | 같은 실/팀/그룹 아래 여러 파트가 있어 1개로 확정 불가 | 담당자에게 CSV 파트 정보 등록/보완 요청 모달 표시 |  |
| [ ] | 임의 사번 fallback 차단 | `SSO_MODE=broker`에서 `X-Employee-Id`만 넣고 API 호출 | 인증되지 않거나 broker session 요구 |  |
| [ ] | 관리자 권한 매핑 | 관리자 사번으로 접속 | 시스템 관리 메뉴 접근 가능 |  |
| [ ] | 일반 사용자 권한 매핑 | 파트장/일반 사용자 사번으로 접속 | 허용된 메뉴만 표시 |  |

## 6. 로그인 후 권한/조직 범위 회귀 테스트

| 체크 | 시나리오 | 방법 | 기대 결과 | 결과/메모 |
| --- | --- | --- | --- | --- |
| [ ] | 입력자 화면 | 파트장/입력자 계정으로 접속 | 업무 입력 가능, 타 파트 수정 제한 |  |
| [ ] | 승인자 화면 | 그룹장/팀장/실장 계정으로 접속 | 본인 승인 단계 요청만 검토 가능 |  |
| [ ] | 관리자 화면 | 관리자 계정으로 접속 | 시스템 관리, 전체 조회 가능 |  |
| [ ] | 입력자 담당조직 변경 반영 | 관리자 화면에서 입력자 담당조직을 다른 파트로 변경 후 해당 입력자로 재접속 또는 새로고침 | 새 담당 파트만 조직 목록/업무 목록에 표시되고 이전 파트 접근은 403 |  |
| [ ] | 승인자 담당조직 변경 반영 | 조직장 자동계정을 사용자 권한관리에서 다른 담당조직으로 등록 후 해당 승인자로 재접속 또는 새로고침 | 새 담당조직 기준의 하위 범위만 표시되고 기존 자동 조직장 범위는 표시되지 않음 |  |
| [ ] | 상위관리자 기준파트 오인 방지 | 실제 파트장이 아닌 상위관리자에게 기준 파트를 지정한 뒤 업무 입력/수정/승인요청/파트 인력현황 접근 시도 | 기준 파트는 조회 범위 계산에만 사용되고, 파트장/입력자 권한이나 파트 구성원 권한은 부여되지 않음 |  |
| [ ] | 실제 조직장 권한 유지 | 실제 그룹장/팀장/실장 ID가 CSV 조직장 필드에 들어간 계정으로 하위 파트 조회 | 실제 조직장은 하위 파트 업무/인력현황 조회 가능 |  |
| [ ] | 입력자 그룹조회 차단 | 입력자 계정으로 `/group` 직접 접근 또는 `/api/tasks/group` 호출 | 메뉴에 그룹 조회가 없고 API는 403 |  |
| [ ] | 승인자 그룹조회 범위 | 승인자 계정으로 그룹 업무 조회 접속 | 담당 하위 조직의 파트 업무만 표시, 타 조직/전체 파트 제외 |  |
| [ ] | 승인 검토 하위조직 현황 | 승인자 화면 진입 | 본인 하위 조직별 승인 요청 상태만 요약 표시 |  |
| [ ] | 업무 입력 하위파트 선택 | 그룹장/팀장/실장으로 `/inputter` 접속 | 본인이 관리하는 하위 파트만 선택지에 표시 |  |
| [ ] | 진행 현황 하위파트 선택 | 그룹장/팀장/실장으로 `/status` 접속 | 본인이 관리하는 하위 파트만 선택지에 표시 |  |

## 7. Mail API 직접 동작 테스트

메일 발송은 승인 흐름에서 자동으로 발생한다. 발송 실패는 운영 상태의 메일 실패 목록과 audit log에서 확인한다.

| 체크 | 시나리오 | 방법 | 기대 결과 | 결과/메모 |
| --- | --- | --- | --- | --- |
| [ ] | URL 조립 | `MAIL_API_BASE_URL=mail.net` | 실제 호출 URL이 `https://mail.net/send_mail` |  |
| [ ] | URL 직접 지정 | `MAIL_API_BASE_URL=https://mail.net/send_mail` | 중복 `/send_mail` 없이 호출 |  |
| [ ] | payload 확인 | 메일 라우터 로그 또는 테스트 endpoint 확인 | `{recipients,title,content}` JSON 전달 |  |
| [ ] | System-ID | `MAIL_API_SYSTEM_ID` 설정 후 호출 | `System-ID` header 전달 |  |
| [ ] | timeout 처리 | 라우터 지연/차단 상황 확인 | 서버 로그에 실패 기록, 앱 흐름은 과도하게 멈추지 않음 |  |

## 8. 승인 메일 트리거 테스트

테스트 전에 본인 또는 테스트 계정이 파트장/그룹장/팀장/실장으로 들어간 테스트 조직을 준비한다.

| 체크 | 트리거 | 실행 방법 | 기대 메일 제목/내용 | 결과/메모 |
| --- | --- | --- | --- | --- |
| [ ] | 승인 요청 제출 | 입력자 계정으로 업무 저장 후 승인 요청 | 제목 `승인 요청 제출`, 1단계 승인자에게 발송 |  |
| [ ] | 승인 상세 링크 | 수신 메일의 바로가기 클릭 | `/approver/approvals/{approval_id}`로 이동 |  |
| [ ] | 다음 단계 승인 요청 | 1단계 승인자가 전체 승인 | 제목 `다음 단계 승인 요청`, 다음 승인자에게 발송 |  |
| [ ] | 최종 승인 완료 | 마지막 승인자가 승인 | 제목 `최종 승인 완료`, 요청자와 관리자에게 발송 |  |
| [ ] | 승인 반려 | 승인자가 일부 업무 반려 후 반려 처리 | 제목 `승인 반려`, 반려 사유 포함 |  |
| [ ] | 승인 완료 건 수정 요청 | 승인 완료 건에서 수정 요청 | 제목 `승인 완료 건 수정 요청`, 수정 사유 포함 |  |
| [ ] | 수신자 중복/빈값 | 요청자/승인자/관리자 중 일부 중복 또는 없음 | 빈 수신자는 제외, 중복 수신은 실제 라우터 정책 확인 |  |
| [ ] | 메일 실패 표시 | mail API 장애 또는 잘못된 설정으로 발송 | 운영 화면의 메일 발송 실패 목록에 기록 |  |

## 9. 메일 내용 검수

| 체크 | 항목 | 기대 결과 | 결과/메모 |
| --- | --- | --- | --- |
| [ ] | 제목 | 업무 상황을 구분 가능 |  |
| [ ] | 본문 | 승인 요청 번호, 단계/사유가 포함 |  |
| [ ] | HTML 렌더링 | 사내 메일 클라이언트에서 깨짐 없음 |  |
| [ ] | 한글 인코딩 | 제목/본문 한글 깨짐 없음 |  |
| [ ] | 링크 | `APP_BASE_URL` 기준의 접근 가능한 URL |  |
| [ ] | 권한 | 링크 클릭 후 권한 없는 사용자는 접근 불가 |  |
| [ ] | 보안 | 메일에 비밀번호, secret, 내부 stack trace 없음 |  |

## 10. 장애/음성 테스트

| 체크 | 시나리오 | 방법 | 기대 결과 | 결과/메모 |
| --- | --- | --- | --- | --- |
| [ ] | SSO 필수값 누락 | broker 사번 header 설정 제거 후 서버 시작/로그인 | 명확한 설정 오류 |  |
| [ ] | 지원하지 않는 SSO_MODE | `SSO_MODE=unknown` | `Unsupported SSO_MODE` 계열 오류 |  |
| [ ] | 제거된 SSO 모드 차단 | `SSO_MODE`에 제거된 값을 넣고 테스트 | 인증 요청 실패, 앱이 구형 모드를 사용하지 않음 |  |
| [ ] | mail API 장애 | `MAIL_API_BASE_URL` 오기입 | 승인 처리는 진행, 메일 실패 audit log 기록 |  |
| [ ] | 제거된 메일 모드 차단 | `MAIL_MODE`에 제거된 값을 넣고 테스트 | 환경 검증 실패 |  |
| [ ] | 권한 없는 접근 | 일반 사용자가 관리자 API 호출 | 403 |  |
| [ ] | 타 승인자 접근 | 다른 승인자가 승인 상세 URL 접근 | 권한 없음 또는 목록 제외 |  |

## 11. 빠른 API 확인 명령

Mock 모드는 브라우저 로그인 또는 아래 명령으로 현재 사용자를 확인한다.

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/auth/me" `
  -Headers @{ "X-Employee-Id" = "part001" }
```

Broker SSO는 직접 form login을 쓰지 않는다. 아래 명령은 broker callback query를 서버 세션으로 교환하는 API만 단독 검증한다.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/broker/session" `
  -ContentType "application/json" `
  -Body '{"loginid":"TEST_EMPLOYEE_ID","deptname":"TEST_DEPTNAME","username":"TEST_USER_NAME"}'
```

승인 대기 목록은 같은 브라우저 세션에서 `/approver`에 접속하거나, callback 세션 cookie가 유지된 상태에서 `/api/approvals/pending`을 호출해 확인한다.

## 12. 최종 승인 기준

| 체크 | 기준 | 결과/메모 |
| --- | --- | --- |
| [ ] | 회사 SSO broker 방식으로 실제 테스트 사번 로그인 성공 |  |
| [ ] | 사번별 역할/조직 매핑 정상 |  |
| [ ] | mock 모드의 개발용 `X-Employee-Id` fallback이 운영 신뢰 경계 밖에 노출되지 않음 |  |
| [ ] | 승인 요청 제출 메일 수신 성공 또는 실패 로그 정상 기록 |  |
| [ ] | 승인 단계 이동/최종 승인/반려/수정 요청 메일 수신 또는 실패 기록 정상 |  |
| [ ] | 메일 링크가 실제 앱의 승인 상세 화면으로 이동 |  |
| [ ] | 자동 테스트 전체 통과 |  |
| [ ] | 실패 케이스의 오류 메시지와 audit log가 운영자가 추적 가능한 수준 |  |

## 13. 테스트 결과 요약

| 항목 | 결과 | 근거/링크/스크린샷 | 담당자 |
| --- | --- | --- | --- |
| SSO 자동 테스트 |  |  |  |
| SSO broker 직접 로그인 |  |  |  |
| 권한 매핑 |  |  |  |
| 메일 자동 테스트 |  |  |  |
| 승인 메일 수신 |  |  |  |
| 메일 링크 이동 |  |  |  |
| 장애 테스트 |  |  |  |
