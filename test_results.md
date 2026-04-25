# 권한별 테스트 결과

실행일: 2026-04-25
대상: `http://127.0.0.1:8000` 로컬 단일 포트 앱
기준 문서: `spec.md`

## 1. 요약

- [x] `spec.md` 최신 기능 반영 확인
- [x] INPUTTER 권한 시나리오 통과
- [x] APPROVER 권한 시나리오 통과
- [x] ADMIN 권한 시나리오 통과
- [x] mock stale token / broker header 권한 혼선 방지 자동 테스트 통과
- [x] 브라우저 역할별 메뉴 노출 확인 통과
- [x] 사내 메일 라우터 `/send_mail` payload 계약 자동 테스트 통과
- [x] 전체 backend/frontend 회귀 테스트 통과

## 2. API 권한 시나리오

| ID | 역할 | 시나리오 | 요청 | 기대 | 결과 |
| --- | --- | --- | --- | --- | --- |
| AUTH-01 | INPUTTER | `part001`은 INPUTTER로 식별된다 | `GET /api/auth/me` | 200, role INPUTTER | [x] 통과 |
| AUTH-02 | APPROVER | `group001`은 APPROVER로 식별된다 | `GET /api/auth/me` | 200, role APPROVER | [x] 통과 |
| AUTH-03 | ADMIN | `admin001`은 ADMIN으로 식별된다 | `GET /api/auth/me` | 200, role ADMIN | [x] 통과 |
| IN-01 | INPUTTER | 본인 조직 업무 조회 가능 | `GET /api/tasks?org_id=1` | 200 | [x] 통과 |
| IN-02 | INPUTTER | 타 조직 업무 조회 차단 | `GET /api/tasks?org_id=999` | 403 | [x] 통과 |
| IN-03 | INPUTTER | 승인 대기 목록 접근 차단 | `GET /api/approvals/pending` | 403 | [x] 통과 |
| IN-04 | INPUTTER | 사용자 권한 관리 API 접근 차단 | `GET /api/admin/users` | 403 | [x] 통과 |
| IN-05 | INPUTTER | 파트원 명단 읽기 가능 | `GET /api/part-members` | 200 | [x] 통과 |
| AP-01 | APPROVER | 본인 차례 승인 대기 목록만 조회 | `GET /api/approvals/pending` | 200, 현재 승인자 `group001`만 포함 | [x] 통과 |
| AP-02 | APPROVER | 사용자 권한 관리 API 접근 차단 | `GET /api/admin/users` | 403 | [x] 통과 |
| AP-03 | APPROVER | 동일 그룹 조회 API 접근 가능 | `GET /api/tasks/group` | 200 | [x] 통과 |
| AD-01 | ADMIN | 전체 승인 대기 목록 조회 가능 | `GET /api/approvals/pending` | 200 | [x] 통과 |
| AD-02 | ADMIN | 사용자 권한 목록 조회 가능 | `GET /api/admin/users` | 200, `admin001` 포함 | [x] 통과 |
| AD-03 | ADMIN | 전체 업무 조회 API 접근 가능 | `GET /api/admin/tasks` | 200 | [x] 통과 |

## 3. 브라우저 메뉴 시나리오

| ID | 역할 | 계정 | 기대 메뉴 | 결과 |
| --- | --- | --- | --- | --- |
| BR-IN-01 | INPUTTER | `part001` | 입력자, 내 파트 현황, 그룹 조회 표시. 승인자/관리자 미표시 | [x] 통과 |
| BR-AP-01 | APPROVER | `group001` | 입력자, 내 파트 현황, 그룹 조회, 승인자 표시. 관리자 미표시 | [x] 통과 |
| BR-AD-01 | ADMIN | `admin001` | 입력자, 내 파트 현황, 그룹 조회, 승인자, 관리자 표시 | [x] 통과 |

## 4. 자동 테스트 증거

```powershell
python -m pytest backend\tests -q -p no:cacheprovider
```

결과: `144 passed in 6.59s`

```powershell
node --test frontend\tests\*.test.mjs
```

결과: `91 passed`

## 5. 추가 확인 및 수정

- [x] 파트원 CSV 업로드는 화면상 관리자 메뉴에만 있었으나 API에서 입력자도 가능했던 권한 차이를 확인했다.
- [x] `POST /api/part-members/import`를 ADMIN 전용으로 수정했다.
- [x] 회귀 테스트 `test_inputter_cannot_import_part_members_csv`를 추가했다.
- [x] 관리자 업로드 후 입력자가 파트원 기반 담당자 배정을 할 수 있는 흐름은 유지했다.
- [x] 메일 발송은 `POST /send_mail`에 `{recipients, title, content}` JSON payload를 보내도록 확인했다.
- [x] `docSecuType`, `contentType`, `recipientType` 조립은 사내 메일 라우터 책임으로 문서화했다.
- [x] 승인 성공 경로의 단계별/최종 승인 메일 알림 테스트를 추가했다.
- [x] broker SSO 모드에서 broker 사번 헤더 누락 시 401을 반환하는 테스트를 추가했다.
- [x] 파트원 CSV 헤더 오류, 타 파트원 명단 조회 차단, 잘못된 knox_id 담당자 배정 차단 테스트를 추가했다.
- [x] 일회성 취합 잠금, 최종 Export 이력, 감사 로그, 메일 실패 관리자 표시 테스트를 추가했다.

## 6. UI 버튼별 브라우저 검증

실행 환경: Codex in-app browser, `http://127.0.0.1:8000`, `admin001`

| 화면 | 버튼 | 결과 | 확인 내용 |
| --- | --- | --- | --- |
| 로그인 | SSO 인증 | [x] 통과 | `admin001` 입력 후 ADMIN 로그인 |
| 공통 | 로그아웃 | [x] 통과 | 로그인 화면으로 전환 |
| 좌측 메뉴 | 입력자 | [x] 통과 | 데이터 입력 화면 이동 |
| 좌측 메뉴 | 내 파트 현황 | [x] 통과 | 내 파트 현황 화면 이동 |
| 좌측 메뉴 | 그룹 조회 | [x] 통과 | 동일 그룹 조회 화면 이동 |
| 좌측 메뉴 | 승인자 | [x] 통과 | 승인 대기 화면 이동 |
| 좌측 메뉴 | 관리자 | [x] 통과 | 관리자 대시보드 이동 |
| 입력자 | 행 추가 | [x] 통과 | 신규 업무 상세 모달 열림 |
| 입력자 | 전체 저장 | [x] 통과 | 클릭 후 화면 유지, 오류 없음 |
| 입력자 | 양식 | [x] 통과 | 다운로드 버튼 클릭 오류 없음 |
| 입력자 | Excel Import | [x] 통과 | 버튼 노출 확인, 파일 선택은 미실행 |
| 입력자 | Excel 붙여넣기 | [x] 통과 | 그리드형 미리보기 모달 열림, `TSV 데이터` 원문 라벨 미노출 |
| 입력자 | 승인 요청 | [ ] 미실행 | 승인 제출 및 메일 알림 가능성이 있어 최종 실행 제외 |
| 입력자 | 삭제 | [ ] 미실행 | 로컬 데이터 삭제 버튼이므로 최종 삭제 제외 |
| 입력 모달 | 닫기(X) | [x] 통과 | 모달 닫힘 |
| 입력 모달 | 취소 | [x] 통과 | 모달 닫힘 |
| 입력 모달 | 저장 | [x] 통과 | 빈 신규 행에서 검증 동작, 500 오류 없음 |
| 입력 모달 | 저장 후 닫기 | [x] 통과 | 빈 신규 행에서 검증 동작, 500 오류 없음 |
| 입력 모달 | 해당 없음 일괄 선택 | [x] 통과 | 기밀/국가핵심기술 2개 버튼 클릭 |
| 그룹 조회 | 다음 | [x] 통과 | 다음 페이지 이동 |
| 그룹 조회 | 이전 | [x] 통과 | 이전 페이지 이동 |
| 승인자 | 검토 | [x] 통과 | 승인 상세 화면 진입 |
| 승인 상세 | 목록 | [x] 통과 | 승인 대기 목록 복귀 |
| 승인 상세 | 검토 완료 | [ ] 미실행 | 승인/반려 확정 및 메일 알림 가능성이 있어 제외 |
| 관리자 대시보드 | Excel 다운로드 | [x] 통과 | 클릭 오류 없음 |
| 관리자 대시보드 | 다음 | [x] 통과 | 부서별 요약 다음 페이지 이동 |
| 관리자 대시보드 | 이전 | [x] 통과 | 부서별 요약 이전 페이지 이동 |
| 관리자 섹션 | 접기 | [x] 통과 | 열린 섹션 접힘 |
| 관리자 섹션 | 펴기 | [x] 통과 | 7개 섹션 펼침 |
| 관리자 전체 데이터 조회 | 조회 | [x] 통과 | 조회 실행 |
| 관리자 폼 | 초기화 | [x] 통과 | 사용자/조직 폼 초기화 버튼 클릭 |
| 관리자 조직 관리 | 검색 | [x] 통과 | 조직 검색 실행 |
| 관리자 CSV | CSV 파일 | [x] 통과 | 파일 선택 버튼 노출 확인 |
| 관리자 CSV | Choose File | [x] 통과 | 파일 선택 버튼 노출 확인 |
| 관리자 CSV | CSV 저장 | [x] 통과 | 파일 미선택 상태에서 비활성 확인 |
| 관리자 문항 관리 | 항목 추가 | [x] 통과 | 기밀/국가핵심기술 2개 버튼 노출 확인 |
| 관리자 문항 관리 | 위/아래 | [x] 통과 | 순서 변경 버튼 노출 확인 |
| 관리자 목록 | 수정 | [x] 통과 | 버튼 노출 확인, 기존 데이터 변경 방지로 클릭 제외 |
| 관리자 목록 | 등록 | [x] 통과 | 버튼 노출 확인, 권한 변경 방지로 클릭 제외 |
| 관리자 목록 | 삭제 | [ ] 미실행 | 데이터 삭제 버튼이므로 최종 삭제 제외 |
| 브라우저 | 콘솔 오류 | [x] 통과 | error log 0건 |

## 7. Excel 붙여넣기 개선 검증

| 항목 | 결과 | 확인 내용 |
| --- | --- | --- |
| HTML 우선 파싱 | [x] 통과 | Excel `text/html` table이 plain text보다 우선 적용됨 |
| TSV fallback | [x] 통과 | HTML이 없으면 기존 `text/plain` TSV를 업무 3개 컬럼으로 변환 |
| 모달 UI | [x] 통과 | `Excel 붙여넣기 미리보기`, `소파트/대업무/세부업무` 그리드, `data-paste-dropzone` 표시 |
| Raw TSV 미노출 | [x] 통과 | 브라우저 DOM에서 `TSV 데이터` 라벨 미노출 |
| 캐시 갱신 | [x] 통과 | `index.html -> app.js -> spreadsheet.js -> clipboard.js` import version 갱신 |

## 8. 미검증 항목

- [ ] 실제 사내 SSO broker 장비/프록시 연동 검증은 로컬 환경에서 수행하지 않았다. 로컬에서는 broker header 우선순위와 mock 권한 혼선 방지 자동 테스트로 검증했다.
- [ ] 운영 MySQL, Kubernetes, Docker 실제 기동 및 191개 파트/5,000건 성능 검증은 별도 운영 환경에서 수행해야 한다.
