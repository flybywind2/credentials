# SSO 및 MySQL 연결 가이드

## 목적

이 문서는 기밀분류시스템을 사내 SSO broker와 MySQL에 연결할 때 필요한 환경 변수, 실행 절차, 검증 방법을 정리한다. 앱은 FastAPI가 `/api/*`와 정적 프론트엔드를 한 포트(`8000`)에서 제공한다.

## 현재 구현 상태

- DB 연결은 `DATABASE_URL`로 전환 가능하며, 기본값은 `sqlite:///./dev.db`이다.
- MySQL 드라이버는 `PyMySQL`을 사용한다.
- SSO 설정 모드는 `mock`, `broker`만 지원한다.
- Broker 모드는 `BROKER_URL`로 인증을 시작하고, broker가 `SERVICE_URL/?loginid=...&deptname=...&username=...`으로 돌려준 callback query를 앱 세션으로 교환한다. 내부 사용자 헤더 주입 방식도 보조로 지원한다.
- `X-Employee-Id` 헤더 fallback은 `SSO_MODE=mock` 개발 모드에서만 동작한다.
- 메일은 `MAIL_MODE=disabled` 또는 `MAIL_MODE=mail_api`만 지원한다.

## 환경 변수

`.env.example`을 복사해 `.env.private-cloud`를 만들고 실제 값을 채운다. 이 파일은 저장소에 커밋하지 않는다.

```powershell
Copy-Item .env.example .env.private-cloud
```

운영 broker와 mail API 예시:

```env
DATABASE_URL=mysql+pymysql://credential_user:change-me@mysql.internal:3306/credential?charset=utf8mb4
SSO_MODE=broker
SSO_TOKEN_SECRET=change-me-to-random-32-byte-secret
BROKER_URL=https://sso.example.com/svc0
SERVICE_URL=https://example1.com
SSO_BROKER_EMPLOYEE_HEADER=X-Broker-Employee-Id
SSO_BROKER_NAME_HEADER=X-Broker-Display-Name
SSO_BROKER_EMAIL_HEADER=X-Broker-Email
SSO_BROKER_DEPT_HEADER=deptname
SSO_ADMIN_EMPLOYEE_IDS=admin001
APP_BASE_URL=https://credential.example.internal
MAIL_MODE=mail_api
MAIL_API_BASE_URL=mail.net
MAIL_API_SYSTEM_ID=credential-system
```

로컬 직접 테스트 예시:

```env
DATABASE_URL=sqlite:///./dev.db
SSO_MODE=mock
MAIL_MODE=disabled
APP_BASE_URL=http://127.0.0.1:8000
```

Broker는 인증 후 `SERVICE_URL/?loginid=사번&deptname=소속명&username=이름` 형태로 redirect해야 한다. 내부 header 방식을 같이 쓰는 경우 proxy는 외부 클라이언트가 보낸 `X-Broker-*` 헤더를 제거한 뒤 인증된 사용자에 대해서만 내부 헤더를 다시 주입해야 한다.

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
$env:SSO_MODE="broker"
$env:BROKER_URL="https://sso.example.com/svc0"
$env:SERVICE_URL="https://example1.com"
$env:SSO_BROKER_EMPLOYEE_HEADER="X-Broker-Employee-Id"
$env:SSO_BROKER_DEPT_HEADER="deptname"
$env:MAIL_MODE="disabled"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

앱 시작 시 `DATABASE_URL`에 지정된 DB에 누락 테이블을 생성하고, 조직 데이터가 없으면 seed 데이터를 넣는다. 운영에서는 Alembic으로 스키마를 먼저 적용하고 seed 주입 여부를 별도 검토한다.

## SSO 운영 연동 체크리스트

- `SSO_MODE=broker`에서는 프론트엔드가 `BROKER_URL`로 이동해 인증을 시작한다.
- 인증 완료 후 broker는 `SERVICE_URL/?loginid=...&deptname=...&username=...`으로 redirect한다.
- 앱은 callback query를 `/api/auth/broker/session`으로 교환해 HttpOnly 세션 cookie를 발급하고, 이후 `/api/auth/me`와 업무 API는 이 세션으로 현재 사용자를 해석한다.
- 소속 파라미터 이름은 `deptname`이다. broker의 `deptname`이 실/팀/그룹까지만 들어오는 경우 CSV로 import한 조직 정보의 `division_name`, `team_name`, `group_name`, `part_name`과 비교해 파트 후보가 1개로 확정될 때만 접속을 허용한다.
- `deptname`으로 파트를 찾을 수 없거나 여러 파트가 매칭되어 확정할 수 없으면 409 `ORG_MAPPING_REQUIRED`를 반환하고, 프론트는 담당자에게 정보 등록을 요청하는 모달을 표시한다.
- 개발용 `X-Employee-Id` fallback과 mock cookie는 broker 모드에서 무시된다.
- Reverse proxy나 broker 계층에서 외부 요청의 동일 헤더를 반드시 삭제하고 인증 후 재주입한다.
- 인증된 사번은 `organizations`의 파트장/그룹장/팀장/실장 ID 또는 `users` 테이블, `SSO_ADMIN_EMPLOYEE_IDS`와 매핑된다.

## 메일 API 운영 체크리스트

- `MAIL_MODE=disabled`이면 메일을 발송하지 않고 앱 흐름만 계속한다.
- `MAIL_MODE=mail_api`이면 `MAIL_API_BASE_URL`이 필요하다.
- `MAIL_API_BASE_URL=mail.net`과 `MAIL_API_BASE_URL=https://mail.net/send_mail` 모두 지원한다.
- 앱은 JSON payload `{recipients, title, content}`만 전달하고, `docSecuType`, `contentType`, `recipientType` 조립은 메일 라우터가 담당한다.
- `MAIL_API_SYSTEM_ID`가 있으면 요청 header `System-ID`로 전달한다.

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

Broker callback 세션 확인:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/broker/session" `
  -ContentType "application/json" `
  -Body '{"loginid":"part001","deptname":"AI/IT전략그룹","username":"홍길동"}'
```

관련 자동 테스트:

```powershell
python -m pytest backend/tests/test_mysql_compatibility.py backend/tests/test_sso_adapter.py backend/tests/test_auth_login.py backend/tests/test_email_and_environment.py -p no:cacheprovider
```

## 장애 확인 포인트

- `SSO_MODE`는 `mock`, `broker`만 지원한다.
- `SSO_MODE=broker`이면 `BROKER_URL`, `SERVICE_URL`이 필요하다.
- `MAIL_MODE`는 `disabled`, `mail_api`만 지원한다.
- `MAIL_MODE=mail_api`이면 `MAIL_API_BASE_URL`이 필요하다.
- 사내 메일 라우터는 `POST https://mail.net/send_mail` 형식으로 호출한다.
- 값이 없으면 앱 시작 시 `Missing required environment variables` 오류로 중단된다.
- 지원하지 않는 `SSO_MODE`를 쓰면 인증 요청에서 `Unsupported SSO_MODE` 오류가 발생한다.
- MySQL 접속 실패 시 DNS, 방화벽, 계정 host, TLS 옵션, URL 인코딩된 비밀번호를 우선 확인한다.

## 보안 원칙

- `.env.private-cloud`, DB 비밀번호, SSO token secret, 메일 API 식별자는 커밋하지 않는다.
- 운영 DB 계정은 앱 DB에만 권한을 제한한다.
- 운영 인증 전환 전에는 `SSO_MODE=mock`의 `X-Employee-Id` fallback을 신뢰 경계 밖에 노출하지 않는다.
- 접근 로그와 감사 로그 보관 정책은 `docs/operations.md`를 기준으로 적용한다.
