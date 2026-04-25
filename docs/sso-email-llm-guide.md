# 사내 LLM용 SSO 및 메일 연동 가이드

이 문서는 성능이 낮은 사내 LLM이나 자동화 에이전트가 SSO 인증과 메일 API 연동을 구현할 때 따라야 하는 기준이다. 새 인증 체계를 만들지 말고, 현재 코드의 확장 지점만 사용한다.

## 핵심 원칙

- 로그인 인증은 SSO가 담당한다. 메일은 승인 요청/반려/완료 알림 발송 수단이며, 메일 OTP 로그인 기능이 아니다.
- 운영에서는 `SSO_MODE=broker`, `ldap`, `saml` 중 하나를 사용한다. `mock`과 `X-Employee-Id` fallback은 개발 전용이다.
- 메일은 SMTP가 아니라 사내 API 라우터 `POST /send_mail` 호출이 기본이다.
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

## SSO 연결 방식 선택

1. 사내 SSO broker 또는 reverse proxy가 먼저 인증하고 사용자 header를 주입하면 `SSO_MODE=broker`를 사용한다.
2. 앱이 AD/LDAP 계정과 비밀번호를 직접 검증해야 하면 `SSO_MODE=ldap`를 사용한다.
3. IdP가 SAML assertion을 전달하면 `SSO_MODE=saml`을 사용한다.
4. 로컬 개발만 `SSO_MODE=mock`을 사용한다.

## Broker SSO 구현

권장 운영 방식이다. Broker가 외부 요청의 `X-Broker-*` header를 먼저 제거한 뒤, 인증 성공 후 내부망 요청에만 다시 주입해야 한다.

```env
SSO_MODE=broker
SSO_BROKER_EMPLOYEE_HEADER=X-Broker-Employee-Id
SSO_BROKER_NAME_HEADER=X-Broker-Display-Name
SSO_BROKER_EMAIL_HEADER=X-Broker-Email
SSO_ADMIN_EMPLOYEE_IDS=admin001
```

앱은 `/api/auth/login`을 호출하지 않는다. 프론트엔드는 `/api/auth/me`를 호출하고, 백엔드는 broker header의 사번으로 사용자를 해석한다. Header가 없으면 `401 Broker employee header is required`가 정상이다.

검증 예시:

```powershell
Invoke-WebRequest `
  -Uri "http://127.0.0.1:8000/api/auth/me" `
  -Headers @{ "X-Broker-Employee-Id" = "part001" } `
  -UseBasicParsing
```

## LDAP SSO 구현

LDAP 모드는 `/api/auth/login`에 `{ "employee_id": "...", "password": "..." }`를 보내고, `ldap3` bind 성공 후 bearer token을 발급한다.

```env
SSO_MODE=ldap
SSO_PROVIDER_URL=ldaps://ldap.example.com:636
SSO_TOKEN_SECRET=change-me
SSO_LDAP_BIND_DN_TEMPLATE=CN={employee_id},OU=Users,DC=example,DC=com
SSO_LDAP_SEARCH_BASE=OU=Users,DC=example,DC=com
SSO_LDAP_SEARCH_FILTER=(sAMAccountName={employee_id})
SSO_LDAP_EMPLOYEE_ATTR=sAMAccountName
SSO_LDAP_NAME_ATTR=displayName
```

로그인 성공 후 모든 API는 `Authorization: Bearer <token>`을 사용한다.

## SAML SSO 구현

SAML 모드는 IdP가 `SAMLResponse`를 `/api/auth/saml/acs`로 POST한다. 백엔드는 `python3-saml`로 assertion을 검증하고 `employee_id` attribute 또는 `NameID`에서 사번을 추출한다.

```env
SSO_MODE=saml
SSO_PROVIDER_URL=https://idp.example.com
SSO_TOKEN_SECRET=change-me
SSO_SAML_SP_ENTITY_ID=https://credential.example.com
SSO_SAML_ACS_URL=https://credential.example.com/api/auth/saml/acs
SSO_SAML_IDP_ENTITY_ID=https://idp.example.com/entity
SSO_SAML_SSO_URL=https://idp.example.com/sso
SSO_SAML_X509_CERT=-----BEGIN CERTIFICATE-----...
SSO_SAML_EMPLOYEE_ATTR=employee_id
```

## 메일 API 연동

운영 메일은 `SMTP_MODE=mail_api`를 사용한다. `MAIL_API_BASE_URL=mail.net`이면 앱은 `https://mail.net/send_mail`로 호출한다. 이미 `/send_mail`까지 포함한 URL을 넣어도 중복으로 붙이지 않는다.

```env
SMTP_MODE=mail_api
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

사내 메일 라우터는 위 값을 받아 최종 메일 API 형식으로 변환한다.

```python
email_data = {
    "subject": payload.title,
    "contents": payload.content,
    "contentType": "HTML",
    "docSecuType": "PERSONAL",
    "recipients": [
        {"emailAddress": email, "recipientType": "TO"}
        for email in payload.recipients
    ],
}
```

승인 메일의 상세 링크는 `APP_BASE_URL`과 `/approver/approvals/{approval_id}`로 만든다. 운영에서는 외부 사용자가 접근 가능한 HTTPS URL을 `APP_BASE_URL`에 넣어야 한다.

## LLM이 하지 말아야 할 것

- Broker/LDAP/SAML 운영 모드에서 `X-Employee-Id`를 신뢰하지 않는다.
- 앱에서 `docSecuType`, `contentType`, `recipientType`까지 직접 조립하지 않는다. 해당 조립은 메일 라우터 책임이다.
- 사번과 역할을 프론트엔드에 하드코딩하지 않는다.
- 사용자 입력 email로 승인자를 정하지 않는다. 승인자는 조직 데이터와 승인 경로에서 가져오며 메일 주소는 `employee_id@samsung.com` 규칙을 사용한다.
- `.env`, SSO secret, SAML 인증서, 메일 API 식별자를 커밋하지 않는다.

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
