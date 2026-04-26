# Kubernetes Deployment

이 디렉터리는 기밀분류시스템을 Kubernetes에 배포하기 위한 기본 매니페스트를 제공한다. FastAPI 앱은 단일 컨테이너에서 API와 정적 프론트엔드를 모두 제공하며, 컨테이너 포트는 `8000`이다.

## Files

| File | Purpose |
| --- | --- |
| `namespace.yaml` | `credential` namespace 생성 |
| `configmap.yaml` | 비밀이 아닌 런타임 설정 |
| `secret.example.yaml` | 실제 secret 생성을 위한 예시 템플릿 |
| `deployment.yaml` | 앱 Deployment, probe, resource request/limit |
| `service.yaml` | ClusterIP Service |
| `ingress.yaml` | nginx Ingress 예시 |
| `kustomization.yaml` | `kubectl apply -k k8s`용 Kustomize entrypoint |

`secret.example.yaml`은 실제 배포에 바로 사용하지 않는다. 운영 secret은 `kubectl create secret` 또는 클러스터의 secret 관리 도구로 생성한다.

## Build and Push Image

기본 매니페스트는 `credential-classification:latest` 이미지를 사용한다. 운영에서는 레지스트리와 불변 태그를 사용한다.

```powershell
docker build -f docker/Dockerfile -t registry.example.internal/credential-classification:2026-04-21 .
docker push registry.example.internal/credential-classification:2026-04-21
```

이미지 태그는 `k8s/kustomization.yaml`에서 변경하거나 배포 후 `kubectl set image`로 교체한다.

```powershell
kubectl -n credential set image `
  deployment/credential-app `
  credential-app=registry.example.internal/credential-classification:2026-04-21
```

## Create Namespace and Secret

namespace를 먼저 만든다.

```powershell
kubectl apply -f k8s/namespace.yaml
```

외부 MySQL, broker SSO, 사내 메일 API를 사용하는 운영 배포는 secret을 만든다.

```powershell
kubectl -n credential create secret generic credential-secrets `
  --from-literal=DATABASE_URL="mysql+pymysql://credential_user:change-me@mysql.internal:3306/credential?charset=utf8mb4" `
  --from-literal=SSO_TOKEN_SECRET="change-me-to-random-32-byte-secret" `
  --from-literal=MAIL_API_BASE_URL="mail.net" `
  --from-literal=MAIL_API_SYSTEM_ID="credential-system"
```

개발 smoke test 목적이면 secret 없이도 컨테이너 이미지의 기본 `sqlite:///./dev.db`, `SSO_MODE=mock`, `MAIL_MODE=disabled` 값으로 기동할 수 있다. 단, 이 경우 DB는 pod 수명에 종속되므로 운영 데이터에는 사용할 수 없다.

## Configure Runtime Mode

비밀이 아닌 설정은 `k8s/configmap.yaml`에서 관리한다.

```yaml
data:
  APP_BASE_URL: "http://127.0.0.1:8000"
  SSO_MODE: "mock"
  MAIL_MODE: "disabled"
  MAIL_API_BASE_URL: "mail.net"
```

운영 broker 연동 예시:

```yaml
data:
  APP_BASE_URL: "https://credential.example.internal"
  SSO_MODE: "broker"
  SSO_BROKER_EMPLOYEE_HEADER: "X-Broker-Employee-Id"
  SSO_BROKER_NAME_HEADER: "X-Broker-Display-Name"
  SSO_BROKER_EMAIL_HEADER: "X-Broker-Email"
  SSO_BROKER_DEPT_HEADER: "deptname"
  MAIL_MODE: "mail_api"
  MAIL_API_BASE_URL: "mail.net"
```

Broker/ingress 계층은 외부 요청의 `X-Broker-*` 헤더를 삭제한 뒤 인증된 요청에만 내부 헤더를 재주입해야 한다.

`SSO_MODE=broker`이면 `SSO_BROKER_EMPLOYEE_HEADER` 값이 필요하다. `MAIL_MODE=mail_api`이면 `MAIL_API_BASE_URL` 값이 필요하고, `MAIL_API_SYSTEM_ID`는 필요한 경우 header `System-ID`로 전달한다.

## Deploy

Kustomize로 전체 리소스를 적용한다.

```powershell
kubectl apply -k k8s
```

배포 상태를 확인한다.

```powershell
kubectl -n credential rollout status deployment/credential-app
kubectl -n credential get pods,svc,ingress
kubectl -n credential logs deployment/credential-app
```

Ingress 없이 로컬에서 확인하려면 port-forward를 사용한다.

```powershell
kubectl -n credential port-forward svc/credential-app 8000:80
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing
```

브라우저 접속:

```text
http://127.0.0.1:8000
```

## Ingress

기본 host는 `credential.example.internal`이다. 실제 사내 DNS에 맞게 `k8s/ingress.yaml`을 수정한다.

```yaml
rules:
  - host: credential.example.internal
```

TLS를 적용하려면 클러스터의 인증서 발급 방식에 맞춰 `tls` 섹션과 annotation을 추가한다.

## Scale

초기 기본값은 `replicas: 1`이다. 앱 시작 시 DB 초기화/seed 로직이 실행되므로, 신규 DB 최초 기동 시에는 1개 replica로 시작하는 것이 안전하다. 외부 MySQL 스키마 적용과 초기 데이터 준비가 끝난 뒤 scale out한다.

```powershell
kubectl -n credential scale deployment/credential-app --replicas=2
```

## Delete

앱 리소스를 삭제한다.

```powershell
kubectl delete -k k8s
```

운영 secret까지 삭제해야 할 때만 별도로 삭제한다.

```powershell
kubectl -n credential delete secret credential-secrets
```

## Operational Notes

- Broker 인증 코드는 구현되어 있다. 운영 전 사내 broker header 주입, header 제거 정책, 방화벽/DNS를 실제 클러스터에서 검증한다.
- 운영에서는 외부 MySQL을 사용하고 `DATABASE_URL`을 secret으로 주입한다.
- 운영에서 mock 모드와 외부에서 주입 가능한 `X-Employee-Id` header fallback을 사용하지 않는다. Broker 모드는 ingress에서 외부 `X-Broker-*` 헤더를 제거해야 한다.
- Docker image는 immutable tag를 사용하고, `latest`는 개발/검증 용도로만 사용한다.
- `secret.example.yaml`의 값은 예시이므로 실제 비밀번호나 secret 값으로 교체한 파일을 커밋하지 않는다.
