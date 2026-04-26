# 사내 LLM용 SSO 및 메일 연동 가이드

이 문서는 성능이 낮은 사내 LLM이나 자동화 에이전트가 SSO 인증과 메일 API 연동을 수정할 때 따라야 하는 기준이다. 새 인증 체계를 만들지 말고, 현재 코드의 확장 지점만 사용한다.

## 핵심 원칙

- 지원 SSO 모드는 `mock`, `broker` 두 가지뿐이다.
- `mock`은 로컬 개발과 직접 테스트용이며, 운영 신뢰 경계 밖에 노출하지 않는다.
- 운영은 `SSO_MODE=broker`를 사용한다. 프론트엔드는 `BROKER_URL`로 이동하고, broker가 `SERVICE_URL/?loginid=...&deptname=...&username=...` callback으로 돌려준 값을 앱 세션으로 교환한다.
- 메일 발송은 `MAIL_MODE=mail_api`와 사내 API 라우터 `POST /send_mail`만 사용한다.
- 관리자/입력자/승인자 권한은 SSO 응답값이 아니라 DB 사용자, 조직장 사번, `SSO_ADMIN_EMPLOYEE_IDS`로 결정한다.

## 관련 코드 위치

| 영역 | 파일 |
| --- | --- |
| 환경 변수 | `backend/config.py` |
| 런타임 필수값 검증 | `backend/services/environment.py` |
| 현재 사용자 해석 | `backend/services/current_user.py` |
| SSO adapter | `backend/services/sso.py` |
| 로그인 API | `backend/routers/auth.py` |
| 사용자/권한 매핑 | `backend/services/user_mapping.py` |
| 메일 발송 | `backend/services/email.py` |
| 승인 알림 호출 | `backend/routers/approval.py` |

## SSO 연결 방식

### Mock

로컬 개발과 브라우저 직접 테스트에서만 사용한다. 로그인 화면에서 사번을 입력하면 mock bearer token과 mock 사용자 cookie를 저장한다.

```env
SSO_MODE=mock
SSO_TOKEN_SECRET=change-me-for-local-only
```

mock 모드의 `/api/auth/me`는 브라우저가 선택한 사용자 cookie와 개발용 `X-Employee-Id` header를 허용한다. 오래된 bearer token이 남아 있어도 명시적으로 선택한 mock 사용자를 우선한다.

### Broker

운영 권장 방식이다. Broker 인증이 끝나면 `SERVICE_URL`에 `loginid`, `deptname`, `username` query parameter를 붙여 앱으로 redirect한다.

```env
SSO_MODE=broker
BROKER_URL=https://sso.example.com/svc0
SERVICE_URL=https://example1.com
SSO_BROKER_EMPLOYEE_HEADER=X-Broker-Employee-Id
SSO_BROKER_NAME_HEADER=X-Broker-Display-Name
SSO_BROKER_EMAIL_HEADER=X-Broker-Email
SSO_BROKER_DEPT_HEADER=deptname
SSO_ADMIN_EMPLOYEE_IDS=admin001
```

앱은 broker 운영에서 `/api/auth/login`을 호출하지 않는다. callback query가 있으면 프론트엔드는 `/api/auth/broker/session`으로 값을 보내고, 백엔드는 HttpOnly 세션 cookie를 발급한다. 이후 프론트엔드는 `/api/auth/me`를 호출해 현재 사용자를 확인한다.

검증 예시:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/broker/session" `
  -ContentType "application/json" `
  -Body '{"loginid":"part001","deptname":"AI/IT전략그룹","username":"홍길동"}'
```

`deptname`이 실/팀/그룹까지만 들어오면 CSV import 조직 정보와 비교한다. 파트 후보가 1개로 확정되면 해당 파트로 접속하고, 없거나 여러 개면 `ORG_MAPPING_REQUIRED` 응답과 담당자 등록 요청 모달을 표시한다.

## 메일 API 연동

운영 메일은 `MAIL_MODE=mail_api`를 사용한다. `MAIL_API_BASE_URL=mail.net`이면 앱은 `https://mail.net/send_mail`로 호출한다. 이미 `/send_mail`까지 포함한 URL을 넣어도 중복으로 붙이지 않는다.

```env
MAIL_MODE=mail_api
MAIL_API_BASE_URL=mail.net
MAIL_API_SYSTEM_ID=credential-system
MAIL_API_TIMEOUT_SECONDS=10
APP_BASE_URL=https://credential.example.com
```

앱에서 사내 메일 라우터로 보내는 JSON은 아래 3개 필드만 사용한다.

```json
{
  "recipients": ["group001@samsung.com"],
  "title": "[기밀분류시스템] 승인 요청",
  "content": "<html>승인 상세 링크 포함</html>"
}
```

사내 메일 라우터는 위 값을 받아 최종 메일 API 형식으로 변환한다. 앱 코드에서 `docSecuType`, `contentType`, `recipientType`까지 직접 조립하지 않는다.

승인 메일의 상세 링크는 `APP_BASE_URL`과 `/approver/approvals/{approval_id}`로 만든다. 운영에서는 사용자가 접근 가능한 HTTPS URL을 `APP_BASE_URL`에 넣어야 한다.

## 하지 말아야 할 것

- 운영 broker 모드에서 `X-Employee-Id`를 신뢰하지 않는다.
- mock/broker SSO와 mail API 외의 직접 연동 코드를 추가하지 않는다.
- 사번과 역할을 프론트엔드에 하드코딩하지 않는다.
- 사용자 입력 email로 승인자를 정하지 않는다. 승인자는 조직 데이터와 승인 경로에서 가져오며 메일 주소는 `employee_id@samsung.com` 규칙을 사용한다.
- `.env`, SSO secret, 메일 API 식별자를 커밋하지 않는다.

## 검증 명령

SSO와 메일 관련 변경 후 아래 테스트를 먼저 실행한다.

```powershell
python -m pytest backend/tests/test_sso_adapter.py backend/tests/test_auth_login.py backend/tests/test_permissions.py backend/tests/test_email_and_environment.py -q -p no:cacheprovider
```

전체 백엔드 회귀 검증:

```powershell
python -m pytest backend/tests -q -p no:cacheprovider
```

문서만 수정한 경우에도 `.env.example`, `README.md`, `docs/sso-mysql-setup.md`와 값이 충돌하지 않는지 확인한다.
