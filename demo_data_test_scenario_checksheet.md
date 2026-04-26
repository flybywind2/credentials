# 시연 데이터 기반 테스트 시나리오 체크시트

작성일: 2026-04-26  
대상 DB: `sqlite:///./dev.db`  
시드 스크립트: `backend/scripts/seed_demo_data.py`  
자동화 테스트: `backend/tests/test_demo_data_scenarios.py`

## 1. 테스트 데이터 기준

| 구분 | 기대 값 |
| --- | --- |
| 조직 | 12개 |
| 사용자 | 23개 |
| 업무 | 28건 |
| 승인요청 | 10건 |
| 기밀 선택지 | `해당 없음`, `해당 됨` |
| 국가핵심기술 선택지 | `해당 없음`, `해당 됨` |

## 2. 계정별 기준 데이터

| 계정 | 역할 | 기준 조직 | 기대 접근 범위 |
| --- | --- | --- | --- |
| `admin001` | 관리자 | AI전략기획파트 | 전체 조직 12개, 전체 승인 현황 |
| `part001` | 입력자 | AI전략기획파트 | 본인 파트 3건 |
| `part002` | 입력자 | 업무자동화파트 | 본인 파트 3건 |
| `part003` | 입력자 | 데이터플랫폼파트 | 본인 파트 3건 |
| `part004` | 입력자 | DX프로세스파트 | 본인 파트 2건 |
| `group001` | 승인자 | AI/IT전략그룹 | AI전략기획파트, 업무자동화파트, 데이터플랫폼파트 |
| `group002` | 승인자 | DX기획그룹 | DX프로세스파트, 현업지원파트 |
| `team001` | 승인자 | 정보전략팀 | AI/IT전략그룹, DX기획그룹, 정보전략팀 직속기획파트 |
| `team002` | 승인자 | Generative AI팀 | GenAI플랫폼그룹, LLM서비스그룹 |
| `div001` | 승인자 | AI개발실 | 정보전략팀, Generative AI팀, AI개발실 직속혁신파트 |

## 3. 자동화 테스트 시나리오

| 체크 | ID | 시나리오 | 검증 방법 | 기대 결과 | 결과 |
| --- | --- | --- | --- | --- | --- |
| [x] | DEMO-AUTO-001 | 시드 데이터 계약 검증 | 임시 DB에 `seed_demo_data` 실행 후 count/계정/선택지 조회 | 조직 12, 사용자 23, 업무 28, 승인요청 10, 고정 선택지 2개 | PASS |
| [x] | DEMO-AUTO-002 | 입력자 범위 제한 | `part002`로 `/api/auth/me`, `/api/organizations`, `/api/tasks`, 타 파트 업무 조회 | 업무자동화파트만 표시, 타 파트 조회 403 | PASS |
| [x] | DEMO-AUTO-003 | 그룹장 범위 및 승인 상태 | `group001`, `group002`로 조직/승인현황/승인대기 조회 | 각 그룹 산하 파트만 표시, 현재 단계 승인 건만 승인대기에 노출 | PASS |
| [x] | DEMO-AUTO-004 | 팀장 그룹현황 및 직속 파트 | `team001`, `team002`로 하위 조직 현황 조회 | 팀장은 그룹 단위 집계, 팀 직속 파트는 파트 행으로 표시 | PASS |
| [x] | DEMO-AUTO-005 | 실장/관리자 범위 | `div001`, `admin001`로 승인 현황 조회 | 실장은 팀 단위와 실 직속 파트, 관리자는 전체 파트 표시 | PASS |

실행 명령:

```powershell
python -m pytest backend\tests\test_demo_data_scenarios.py -p no:cacheprovider
```

## 4. 계정별 수동 UI 테스트 시나리오

| 체크 | ID | 계정 | 화면 | 수행 절차 | 기대 결과 | 결과/메모 |
| --- | --- | --- | --- | --- | --- | --- |
| [ ] | DEMO-UI-001 | `part002` | 업무 입력 | 로그인 후 업무 입력 화면 진입 | 업무자동화파트 업무 3건만 표시, 조직 선택도 업무자동화파트로 제한 |  |
| [ ] | DEMO-UI-002 | `part003` | 진행 현황 | 로그인 후 진행 현황 확인 | 데이터플랫폼파트 업무 3건, 상태 `APPROVED` 집계 확인 |  |
| [ ] | DEMO-UI-003 | `part004` | 업무 입력 | 로그인 후 타 파트 업무 URL/API 접근 시도 | DX프로세스파트만 표시, 타 파트 접근 불가 |  |
| [x] | DEMO-UI-004 | `group002` | 승인 검토 | 로그인 후 승인 검토 화면 확인 | `파트현황`, DX프로세스파트 승인대기, 현업지원파트 반려 표시, AI/IT전략그룹 파트 미표시 | PASS |
| [x] | DEMO-UI-005 | `team002` | 승인 검토 | 로그인 후 승인 검토 화면 확인 | `그룹현황`, GenAI플랫폼그룹/LLM서비스그룹 표시, DX기획그룹 미표시 | PASS |
| [ ] | DEMO-UI-006 | `team001` | 승인 검토 | 로그인 후 승인 검토 화면 확인 | AI/IT전략그룹, DX기획그룹, 정보전략팀 직속기획파트 표시 |  |
| [ ] | DEMO-UI-007 | `div001` | 승인 검토 | 로그인 후 승인 검토 화면 확인 | 정보전략팀, Generative AI팀, AI개발실 직속혁신파트 표시 |  |
| [ ] | DEMO-UI-008 | `admin001` | 관리자 | 시스템 관리와 전체 조회 화면 확인 | 조직 12개와 전체 승인 현황 확인 |  |

## 5. 승인 단계 기대값

| 파트 | 요청 상태 | 현재 단계 | 현재 승인자 | 기대 노출 |
| --- | --- | --- | --- | --- |
| AI전략기획파트 | 승인대기 | 1/3 | `group001` | `group001` 승인대기 목록 |
| 업무자동화파트 | 승인대기 | 2/3 | `team001` | `team001` 승인대기 목록 |
| 데이터플랫폼파트 | 승인완료 | 3/3 | 없음 | 하위 현황의 승인완료 집계 |
| DX프로세스파트 | 승인대기 | 1/3 | `group002` | `group002` 승인대기 목록 |
| 현업지원파트 | 반려 | 1/3 | 없음 | `group002` 하위 현황의 반려 집계 |
| 정보전략팀 직속기획파트 | 승인대기 | 1/2 | `team001` | 팀 직속 파트로 `team001` 승인대기 목록 |
| 플랫폼운영파트 | 승인대기 | 1/3 | `group003` | `team002`에는 하위 현황만 표시, 승인대기 목록에는 미표시 |
| 업무봇파트 | 승인완료 | 3/3 | 없음 | `team002` 하위 현황의 승인완료 집계 |
| AI개발실 직속혁신파트 | 승인대기 | 1/1 | `div001` | 실 직속 파트로 `div001` 승인대기 목록 |

## 6. 빠른 API 점검 명령

```powershell
python -m pytest backend\tests\test_demo_data_scenarios.py -p no:cacheprovider

@'
import requests
for employee_id in ["part002", "group002", "team002", "div001", "admin001"]:
    response = requests.get(
        "http://127.0.0.1:8000/api/approvals/subordinate-status",
        headers={"X-Employee-Id": employee_id},
        timeout=10,
    )
    print(employee_id, response.status_code, response.json().get("scope_label"))
'@ | python -
```

## 7. 이번 실행 결과

| 항목 | 결과 | 근거 |
| --- | --- | --- |
| 시연 데이터 자동화 테스트 | PASS | `backend/tests/test_demo_data_scenarios.py` 5 passed |
| `group002` 브라우저 승인 검토 | PASS | DX프로세스파트/현업지원파트만 표시, AI전략기획파트 미표시 |
| `team002` 브라우저 승인 검토 | PASS | GenAI플랫폼그룹/LLM서비스그룹 표시, DX프로세스파트 미표시 |
