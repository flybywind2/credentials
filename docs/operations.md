# 운영 정책 및 검증 가이드

이 문서는 기밀분류시스템의 운영 배포 전 확인해야 하는 백업/복구, 감사 로그, 접근 로그, 성능 검증 기준을 정의한다.

## 백업 정책

- MySQL 운영 DB는 매일 1회 전체 백업, 1시간 단위 binlog 증분 백업을 수행한다.
- 백업 파일은 운영 DB와 다른 스토리지에 저장하고 30일 이상 보관한다.
- 백업 산출물은 암호화 저장소에 보관하며, DB 계정과 별도 권한으로 접근을 제한한다.
- 배포 전후에는 수동 스냅샷을 추가로 생성한다.

## 복구 절차

1. 신규 MySQL 인스턴스를 준비하고 앱 트래픽을 차단한다.
2. 최신 전체 백업을 복원한다.
3. 장애 직전 시점까지 binlog를 적용한다.
4. `pytest`와 `/api/health` 확인 후 읽기 전용 검증 계정으로 주요 화면을 점검한다.
5. DNS 또는 서비스 라우팅을 복구 DB로 전환한다.

## 감사 로그

- 승인 요청, 승인, 반려, 수정 요청, 관리자 설정 변경은 감사 대상 이벤트로 분류한다.
- 감사 로그 필드는 `event`, `employee_id`, `role`, `organization_id`, `resource_id`, `status`, `created_at`을 기본으로 한다.
- 로그는 최소 1년 보관하며, 운영 환경에서는 중앙 로그 저장소로 전송한다.
- 개인정보와 SSO secret, SMTP password, 사내 메일 API 식별자, DB password는 로그에 기록하지 않는다.

## 접근 로그

- FastAPI 요청 미들웨어는 method, path, status, elapsed_ms를 기록한다.
- 운영 reverse proxy는 client IP, authenticated employee id, user agent를 추가 기록한다.
- 접근 로그는 최소 90일 보관한다.

## 성능 검증 기준

- 기준 데이터: 191개 파트, 5,000건 업무, 동시 접속 100명.
- 핵심 API 목표: 목록/대시보드 조회 p95 2초 이하, 승인/반려 p95 3초 이하.
- 검증 시나리오: 로그인, 업무 조회, 행 저장, 승인 요청, 승인 대기 조회, 승인/반려, 관리자 대시보드 조회.
- 성능 검증은 운영과 동일한 MySQL, SSO gateway, 메일 발송 설정을 사용하는 스테이징 환경에서 수행한다.

## Docker 기동 검증

```powershell
docker compose -f docker/docker-compose.yml up --build
Invoke-WebRequest http://localhost:8000/api/health
Invoke-WebRequest http://localhost:8000/
```

검증 후 컨테이너 로그에 시작 오류, DB 초기화 오류, 정적 파일 404가 없는지 확인한다.
