# SSO Broker 연동 가이드

이 문서는 다른 프로젝트에서도 동일하게 사용할 수 있는 SSO broker 연동 기준을 정리한다. LDAP, SAML, SMTP 방식은 사용하지 않는다. 인증은 사내 SSO broker가 담당하고, 서비스는 broker가 전달한 사용자 정보를 앱 세션으로 교환해 사용한다.

## 1. 기본 흐름

```text
사용자 브라우저
  -> 서비스 로그인 화면
  -> BROKER_URL
  -> SSO broker 인증
  -> SERVICE_URL/?loginid=사번&deptname=소속명&username=이름
  -> 서비스가 callback query를 세션으로 교환
  -> 서비스 화면 진입
```

예시:

```env
BROKER_URL=https://sso.example.com/svc0
SERVICE_URL=https://example1.com
```

broker 인증이 끝나면 아래처럼 서비스 URL로 redirect된다.

```text
https://example1.com/?loginid=part001&deptname=AI%2FIT%EC%A0%84%EB%9E%B5%EA%B7%B8%EB%A3%B9&username=%ED%99%8D%EA%B8%B8%EB%8F%99
```

## 2. 환경 변수

| 변수 | 필수 | 설명 |
| --- | --- | --- |
| `SSO_MODE` | Y | 운영은 `broker`, 로컬 개발은 `mock` |
| `BROKER_URL` | Y | SSO broker 인증 진입 URL |
| `SERVICE_URL` | Y | broker 인증 후 돌아올 서비스 URL |
| `SSO_TOKEN_SECRET` | 권장 | 앱 세션 token 서명 secret |
| `SSO_TOKEN_EXPIRE_MINUTES` | N | 앱 세션 유지 시간 |
| `SSO_ADMIN_EMPLOYEE_IDS` | N | 쉼표 구분 관리자 사번 |

`SSO_MODE=broker`에서는 `BROKER_URL`, `SERVICE_URL`이 실제 운영 값과 일치해야 한다.

## 3. Callback Query 규약

broker는 인증 성공 후 `SERVICE_URL`에 아래 query parameter를 붙여 redirect한다.

| 파라미터 | 필수 | 설명 |
| --- | --- | --- |
| `loginid` | Y | 사번 또는 서비스 사용자 ID |
| `deptname` | 권장 | 사용자의 소속명. 조직 매핑에 사용 |
| `username` | 권장 | 사용자 표시명 |

서비스는 callback query를 받은 즉시 서버 API로 교환하고, 브라우저 주소창에서 `loginid`, `deptname`, `username`을 제거한다. Query 값을 계속 주소창에 남기지 않는다.

## 4. 서비스 API 권장 형태

### SSO 설정 조회

프론트엔드가 현재 인증 방식을 판단할 수 있도록 제공한다.

```http
GET /api/auth/sso-config
```

응답 예시:

```json
{
  "sso_mode": "broker",
  "broker_url": "https://sso.example.com/svc0",
  "service_url": "https://example1.com"
}
```

### Broker Callback 세션 교환

프론트엔드가 callback query를 서버 세션으로 교환한다.

```http
POST /api/auth/broker/session
Content-Type: application/json

{
  "loginid": "part001",
  "deptname": "AI/IT전략그룹",
  "username": "홍길동"
}
```

응답 예시:

```json
{
  "access_token": "signed-token",
  "token_type": "bearer",
  "user": {
    "employee_id": "part001",
    "name": "홍길동",
    "role": "INPUTTER"
  }
}
```

서버는 가능하면 HttpOnly cookie도 같이 내려 이후 API 호출이 같은 사용자 세션으로 동작하게 한다.

### 현재 사용자 조회

```http
GET /api/auth/me
```

서버는 세션 cookie 또는 bearer token을 확인해 현재 사용자를 반환한다. `SSO_MODE=broker`에서는 임의의 `X-Employee-Id` 같은 개발용 헤더를 신뢰하지 않는다.

## 5. 프론트엔드 처리 기준

1. 앱 시작 시 URL query에서 `loginid`를 찾는다.
2. `loginid`가 있으면 `loginid`, `deptname`, `username`을 `/api/auth/broker/session`으로 보낸다.
3. 세션 생성이 성공하면 `history.replaceState`로 민감 query를 제거한다.
4. 이후 `/api/auth/me`로 사용자 정보를 조회하고 역할별 화면을 렌더링한다.
5. `loginid`가 없고 로그인 세션도 없으면 `/api/auth/sso-config`를 조회한다.
6. `sso_mode=broker`이면 로그인 버튼은 `BROKER_URL`로 이동시킨다.
7. `sso_mode=mock`이면 로컬 개발용 사번 입력 화면을 보여준다.

## 6. 조직 매핑

서비스는 `loginid`를 기준으로 사용자 또는 조직장 정보를 찾는다. `deptname`은 조직/파트 매핑에 사용한다.

권장 매핑 순서:

1. 서비스 DB의 사용자 테이블에 등록된 `loginid`
2. 조직 데이터의 파트장/그룹장/팀장/실장 ID
3. 관리자 사번 목록(`SSO_ADMIN_EMPLOYEE_IDS`)
4. `deptname`으로 단일 조직/파트가 확정되는 경우

`deptname`으로 조직을 찾을 수 없거나 여러 조직이 매칭되면 로그인은 중단하고 담당자에게 조직 정보 등록을 요청한다.

응답 예시:

```json
{
  "detail": {
    "code": "ORG_MAPPING_REQUIRED",
    "message": "소속에 맞는 파트 정보가 없습니다. 담당자에게 정보 등록을 요청해 주세요.",
    "deptname": "AI/IT전략그룹"
  }
}
```

## 7. 보안 기준

- `SSO_MODE=broker`에서는 개발용 사번 헤더나 로컬 스토리지 값을 인증 근거로 쓰지 않는다.
- `loginid`, `deptname`, `username` query는 세션 교환 후 즉시 주소창에서 제거한다.
- 앱 세션 token은 서명하고 만료 시간을 둔다.
- 운영에서는 HTTPS를 사용한다.
- 실제 secret, 운영 URL, 사번 목록은 저장소에 커밋하지 않는다.
- `BROKER_URL`과 `SERVICE_URL`은 운영 환경별 설정으로 관리한다.

## 8. 테스트 체크리스트

| 체크 | 시나리오 | 기대 결과 |
| --- | --- | --- |
| [ ] | 로그인 버튼 클릭 | `BROKER_URL`로 이동 |
| [ ] | broker 인증 성공 | `SERVICE_URL/?loginid=...&deptname=...&username=...`로 복귀 |
| [ ] | callback 세션 교환 | `/api/auth/broker/session` 200 응답 |
| [ ] | 주소창 정리 | `loginid`, `deptname`, `username` query 제거 |
| [ ] | 현재 사용자 조회 | `/api/auth/me`가 실제 사번 사용자 반환 |
| [ ] | 조직 매핑 실패 | 담당자 등록 요청 메시지 표시 |
| [ ] | 개발용 헤더 주입 | broker mode에서 인증 우회 불가 |
| [ ] | 세션 만료 | 재인증 필요 상태로 전환 |

## 9. 로컬 Mock 모드

로컬 개발에서는 아래처럼 사용한다.

```env
SSO_MODE=mock
```

mock 모드에서는 사번을 직접 입력해 개발 seed 사용자로 로그인할 수 있다. 이 모드는 운영에 노출하지 않는다.
