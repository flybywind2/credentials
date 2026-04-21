# SSO 및 MySQL 연결 가이드

## 목적

이 문서는 기밀분류시스템을 사내 SSO와 MySQL에 연결할 때 필요한 환경 변수, 실행 절차, 검증 방법을 정리한다. 앱은 FastAPI가 `/api/*`와 정적 프론트엔드를 한 포트(`8000`)에서 제공한다.

## 현재 구현 상태

- DB 연결은 `DATABASE_URL`로 전환 가능하며, 기본값은 `sqlite:///./dev.db`이다.
- MySQL 드라이버는 `PyMySQL`을 사용한다.
- SSO 설정 모드는 `mock`, `ldap`, `saml`을 지원한다.
- LDAP 모드는 `ldap3`로 AD/LDAP bind와 선택적 사용자 조회를 수행한다.
- SAML 모드는 `python3-saml`로 ACS endpoint(`/api/auth/saml/acs`)에서 assertion 서명, audience, issuer, 만료를 검증한다.
- 인증 성공 후 백엔드는 HMAC 서명 bearer token을 발급하고, `/api/auth/me`와 업무 API는 `Authorization: Bearer ...`를 우선 신뢰한다.
- `X-Employee-Id` 헤더 fallback은 `SSO_MODE=mock` 개발 모드에서만 동작한다.

## 환경 변수

`.env.example`을 복사해 `.env.private-cloud`를 만들고 실제 값을 채운다. 이 파일은 저장소에 커밋하지 않는다.

```powershell
Copy-Item .env.example .env.private-cloud
```

예시:

```env
DATABASE_URL=mysql+pymysql://credential_user:change-me@mysql.internal:3306/credential?charset=utf8mb4
SSO_MODE=ldap
SSO_PROVIDER_URL=ldap://ad.example.internal:389
SSO_TOKEN_SECRET=change-me-to-random-32-byte-secret
SSO_LDAP_BIND_DN_TEMPLATE={employee_id}@example.internal
SSO_LDAP_SEARCH_BASE=OU=Users,DC=example,DC=internal
SSO_LDAP_SEARCH_FILTER=(sAMAccountName={employee_id})
SSO_LDAP_EMPLOYEE_ATTR=sAMAccountName
SSO_LDAP_NAME_ATTR=displayName
SMTP_MODE=smtp
SMTP_HOST=smtp.example.internal
SMTP_PORT=587
SMTP_USERNAME=credential-app@example.internal
SMTP_PASSWORD=change-me
```

SAML을 사용할 경우:

```env
SSO_MODE=saml
SSO_PROVIDER_URL=https://idp.example.internal/saml/metadata
SSO_TOKEN_SECRET=change-me-to-random-32-byte-secret
SSO_SAML_SP_ENTITY_ID=credential-app
SSO_SAML_ACS_URL=https://credential.example.internal/api/auth/saml/acs
SSO_SAML_IDP_ENTITY_ID=https://idp.example.internal
SSO_SAML_SSO_URL=https://idp.example.internal/sso
SSO_SAML_X509_CERT=paste-idp-signing-certificate
SSO_SAML_EMPLOYEE_ATTR=employee_id
```

## MySQL 준비

MySQL 8.x 기준 권장 DB와 계정 예시는 다음과 같다.

```sql
CREATE DATABASE credential
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

CREATE USER 'credential_user'@'%' IDENTIFIED BY 'change-me';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX
  ON credential.* TO 'credential_user'@'%';
FLUSH PRIVILEGES;
```

비밀번호에 특수문자가 있으면 URL 인코딩한다. 예를 들어 `p@ss#1`은 `p%40ss%231`로 적는다.

TLS가 필요한 환경에서는 사내 표준에 맞춰 `DATABASE_URL`에 SSL 옵션을 추가한다.

```env
DATABASE_URL=mysql+pymysql://credential_user:change-me@mysql.internal:3306/credential?charset=utf8mb4&ssl_ca=/path/to/ca.pem
```

## 스키마 적용

초기 스키마 적용은 Alembic을 권장한다.

```powershell
$env:DATABASE_URL="mysql+pymysql://credential_user:change-me@mysql.internal:3306/credential?charset=utf8mb4"
alembic upgrade head
```

개발/검증 DB를 완전히 재생성해야 할 때만 `--reset`을 사용한다. 운영 데이터가 있는 DB에서는 사용하지 않는다.

```powershell
python -m backend.scripts.init_db `
  --database-url "mysql+pymysql://credential_user:change-me@mysql.internal:3306/credential?charset=utf8mb4" `
  --reset
```

## 실행

컨테이너 실행:

```powershell
docker compose -f docker/docker-compose.private-cloud.yml up --build -d
```

로컬 Python 실행:

```powershell
$env:DATABASE_URL="mysql+pymysql://credential_user:change-me@mysql.internal:3306/credential?charset=utf8mb4"
$env:SSO_MODE="ldap"
$env:SSO_PROVIDER_URL="ldap://ad.example.internal:389"
$env:SSO_TOKEN_SECRET="change-me-to-random-32-byte-secret"
$env:SSO_LDAP_BIND_DN_TEMPLATE="{employee_id}@example.internal"
$env:SSO_LDAP_SEARCH_BASE="OU=Users,DC=example,DC=internal"
$env:SMTP_MODE="disabled"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

앱 시작 시 `DATABASE_URL`에 지정된 DB에 누락 테이블을 생성하고, 조직 데이터가 없으면 seed 데이터를 넣는다. 운영에서는 Alembic으로 스키마를 먼저 적용하고 seed 주입 여부를 별도 검토한다.

## SSO 운영 연동 체크리스트

LDAP 방식:

- `LdapSsoAdapter.authenticate()`에서 사번/계정으로 AD bind를 수행한다.
- `SSO_LDAP_BIND_DN_TEMPLATE`은 `{employee_id}` placeholder를 포함해야 한다.
- `SSO_LDAP_SEARCH_BASE`가 설정되면 `SSO_LDAP_SEARCH_FILTER`로 이름, 메일, 사번 속성을 조회한다.
- bind 실패는 401, LDAP 설정/서버 오류는 500으로 응답한다.

SAML 방식:

- `SSO_SAML_ACS_URL`은 외부에서 접근 가능한 `/api/auth/saml/acs` URL이어야 한다.
- SAML assertion의 서명, audience, issuer, 만료 시간을 검증한다.
- assertion의 `SSO_SAML_EMPLOYEE_ATTR` 또는 NameID에서 사번을 추출한다.
- IdP 인증서 교체 시 `SSO_SAML_X509_CERT`를 함께 갱신한다.

공통:

- 인증된 사번은 `organizations`의 파트장/그룹장/팀장/실장 ID 또는 `users` 테이블, `SSO_ADMIN_EMPLOYEE_IDS`와 매핑된다.
- 운영에서 `mock-token-*`은 사용하지 않으며 모든 API는 bearer token을 우선 사용한다.
- reverse proxy가 `X-Employee-Id`를 주입하는 구조라도 운영 모드에서는 앱이 이 헤더를 fallback 인증으로 쓰지 않는다.

## 검증

서버 상태:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing
```

MySQL 연결:

```powershell
@'
from sqlalchemy import create_engine, text
from backend.config import settings

engine = create_engine(settings.database_url)
with engine.connect() as conn:
    print(conn.execute(text("select 1")).scalar_one())
'@ | python -
```

LDAP 로그인 및 bearer token 확인:

```powershell
$login = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/auth/login" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"employee_id":"part001","password":"change-me"}'

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/auth/me" `
  -Headers @{ Authorization = "Bearer $($login.access_token)" }
```

관련 자동 테스트:

```powershell
python -m pytest backend/tests/test_mysql_compatibility.py backend/tests/test_sso_adapter.py backend/tests/test_auth_login.py
```

## 장애 확인 포인트

- `SSO_MODE=ldap`이면 `SSO_PROVIDER_URL`, `SSO_LDAP_BIND_DN_TEMPLATE`, `SSO_TOKEN_SECRET` 또는 `SSO_CLIENT_SECRET`이 필요하다.
- `SSO_MODE=saml`이면 ACS URL, SP entity id, IdP entity id, SSO URL, IdP 인증서, token secret이 필요하다.
- `SMTP_MODE=smtp`이면 `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`가 필요하다.
- 값이 없으면 앱 시작 시 `Missing required environment variables` 오류로 중단된다.
- 지원하지 않는 `SSO_MODE`를 쓰면 인증 요청에서 `Unsupported SSO_MODE` 오류가 발생한다.
- MySQL 접속 실패 시 DNS, 방화벽, 계정 host, TLS 옵션, URL 인코딩된 비밀번호를 우선 확인한다.

## 보안 원칙

- `.env.private-cloud`, DB 비밀번호, SSO token/client secret, IdP 인증서는 커밋하지 않는다.
- 운영 DB 계정은 앱 DB에만 권한을 제한한다.
- 운영 인증 전환 전에는 `SSO_MODE=mock`의 `X-Employee-Id` fallback을 신뢰 경계 밖에 노출하지 않는다.
- 접근 로그와 감사 로그 보관 정책은 `docs/operations.md`를 기준으로 적용한다.
