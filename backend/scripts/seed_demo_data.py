import argparse
import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalTaskReview,
    AuditLog,
    ColumnTooltip,
    ConfidentialQuestion,
    NationalTechQuestion,
    Organization,
    PartMember,
    SystemSetting,
    TaskAssignee,
    TaskEntry,
    TaskQuestionCheck,
    User,
)
from backend.services.approval_flow import build_approval_path


KST = timezone(timedelta(hours=9))
BASE_TIME = datetime(2026, 4, 26, 9, 0, tzinfo=KST)
NONE_OPTION = "해당 없음"
YES_OPTION = "해당 됨"


ORGANIZATIONS = [
    {
        "id": 1,
        "division_name": "AI개발실",
        "division_head_name": "김다현",
        "division_head_id": "div001",
        "team_name": "정보전략팀",
        "team_head_name": "이서준",
        "team_head_id": "team001",
        "group_name": "AI/IT전략그룹",
        "group_head_name": "박민재",
        "group_head_id": "group001",
        "part_name": "AI전략기획파트",
        "part_head_name": "최유진",
        "part_head_id": "part001",
        "org_type": "NORMAL",
    },
    {
        "id": 2,
        "division_name": "AI개발실",
        "division_head_name": "김다현",
        "division_head_id": "div001",
        "team_name": "정보전략팀",
        "team_head_name": "이서준",
        "team_head_id": "team001",
        "group_name": "AI/IT전략그룹",
        "group_head_name": "박민재",
        "group_head_id": "group001",
        "part_name": "업무자동화파트",
        "part_head_name": "강민호",
        "part_head_id": "part002",
        "org_type": "NORMAL",
    },
    {
        "id": 3,
        "division_name": "AI개발실",
        "division_head_name": "김다현",
        "division_head_id": "div001",
        "team_name": "정보전략팀",
        "team_head_name": "이서준",
        "team_head_id": "team001",
        "group_name": "AI/IT전략그룹",
        "group_head_name": "박민재",
        "group_head_id": "group001",
        "part_name": "데이터플랫폼파트",
        "part_head_name": "한서연",
        "part_head_id": "part003",
        "org_type": "NORMAL",
    },
    {
        "id": 4,
        "division_name": "AI개발실",
        "division_head_name": "김다현",
        "division_head_id": "div001",
        "team_name": "정보전략팀",
        "team_head_name": "이서준",
        "team_head_id": "team001",
        "group_name": "DX기획그룹",
        "group_head_name": "조현우",
        "group_head_id": "group002",
        "part_name": "DX프로세스파트",
        "part_head_name": "오지훈",
        "part_head_id": "part004",
        "org_type": "NORMAL",
    },
    {
        "id": 5,
        "division_name": "AI개발실",
        "division_head_name": "김다현",
        "division_head_id": "div001",
        "team_name": "정보전략팀",
        "team_head_name": "이서준",
        "team_head_id": "team001",
        "group_name": "DX기획그룹",
        "group_head_name": "조현우",
        "group_head_id": "group002",
        "part_name": "현업지원파트",
        "part_head_name": "윤지아",
        "part_head_id": "part005",
        "org_type": "NORMAL",
    },
    {
        "id": 6,
        "division_name": "AI개발실",
        "division_head_name": "김다현",
        "division_head_id": "div001",
        "team_name": "정보전략팀",
        "team_head_name": "이서준",
        "team_head_id": "team001",
        "group_name": None,
        "group_head_name": None,
        "group_head_id": None,
        "part_name": "정보전략팀 직속기획파트",
        "part_head_name": "신도윤",
        "part_head_id": "part006",
        "org_type": "TEAM_DIRECT",
    },
    {
        "id": 7,
        "division_name": "AI개발실",
        "division_head_name": "김다현",
        "division_head_id": "div001",
        "team_name": "Generative AI팀",
        "team_head_name": "정하린",
        "team_head_id": "team002",
        "group_name": "GenAI플랫폼그룹",
        "group_head_name": "문태준",
        "group_head_id": "group003",
        "part_name": "플랫폼운영파트",
        "part_head_name": "문하늘",
        "part_head_id": "part007",
        "org_type": "NORMAL",
    },
    {
        "id": 8,
        "division_name": "AI개발실",
        "division_head_name": "김다현",
        "division_head_id": "div001",
        "team_name": "Generative AI팀",
        "team_head_name": "정하린",
        "team_head_id": "team002",
        "group_name": "GenAI플랫폼그룹",
        "group_head_name": "문태준",
        "group_head_id": "group003",
        "part_name": "프롬프트검증파트",
        "part_head_name": "배수아",
        "part_head_id": "part008",
        "org_type": "NORMAL",
    },
    {
        "id": 9,
        "division_name": "AI개발실",
        "division_head_name": "김다현",
        "division_head_id": "div001",
        "team_name": "Generative AI팀",
        "team_head_name": "정하린",
        "team_head_id": "team002",
        "group_name": "LLM서비스그룹",
        "group_head_name": "장도영",
        "group_head_id": "group004",
        "part_name": "업무봇파트",
        "part_head_name": "정우성",
        "part_head_id": "part009",
        "org_type": "NORMAL",
    },
    {
        "id": 10,
        "division_name": "AI개발실",
        "division_head_name": "김다현",
        "division_head_id": "div001",
        "team_name": None,
        "team_head_name": None,
        "team_head_id": None,
        "group_name": None,
        "group_head_name": None,
        "group_head_id": None,
        "part_name": "AI개발실 직속혁신파트",
        "part_head_name": "노은채",
        "part_head_id": "part010",
        "org_type": "DIV_DIRECT",
    },
    {
        "id": 11,
        "division_name": "Cloud전환실",
        "division_head_name": "최서윤",
        "division_head_id": "div002",
        "team_name": "클라우드전략팀",
        "team_head_name": "유재민",
        "team_head_id": "team003",
        "group_name": "클라우드기획그룹",
        "group_head_name": "고민석",
        "group_head_id": "group005",
        "part_name": "클라우드전략파트",
        "part_head_name": "서민준",
        "part_head_id": "part011",
        "org_type": "NORMAL",
    },
    {
        "id": 12,
        "division_name": "Cloud전환실",
        "division_head_name": "최서윤",
        "division_head_id": "div002",
        "team_name": "클라우드전략팀",
        "team_head_name": "유재민",
        "team_head_id": "team003",
        "group_name": None,
        "group_head_name": None,
        "group_head_id": None,
        "part_name": "클라우드전략팀 직속운영파트",
        "part_head_name": "양지후",
        "part_head_id": "part012",
        "org_type": "TEAM_DIRECT",
    },
]


PART_MEMBERS = {
    "part001": [("김가은", "kim.ge"), ("박도현", "park.dh"), ("이채원", "lee.cw")],
    "part002": [("정민수", "jung.ms"), ("송하윤", "song.hy"), ("임서준", "lim.sj")],
    "part003": [("최나래", "choi.nr"), ("한지민", "han.jm"), ("오세훈", "oh.sh")],
    "part004": [("문지원", "moon.jw"), ("강예린", "kang.yr"), ("서도윤", "seo.dy")],
    "part005": [("유하늘", "yoo.hn"), ("배지호", "bae.jh"), ("권수빈", "kwon.sb")],
    "part006": [("신아라", "shin.ar"), ("장민혁", "jang.mh")],
    "part007": [("문소율", "moon.sy"), ("조서진", "cho.sj"), ("백현우", "baek.hw")],
    "part008": [("배하린", "bae.hr"), ("남지안", "nam.ja")],
    "part009": [("정다온", "jung.do"), ("김태오", "kim.to")],
    "part010": [("노유나", "roh.yn"), ("이도겸", "lee.dg")],
    "part011": [("서지우", "seo.jw"), ("홍민재", "hong.mj")],
    "part012": [("양서아", "yang.sa"), ("차준호", "cha.jh")],
}


TASKS_BY_PART = {
    "part001": [
        ("전략", "AI 과제 포트폴리오 관리", "전사 AI 과제 후보군을 수집하고 우선순위와 보안 등급을 정리한다.", True, False, True, "SUBMITTED"),
        ("전략", "AI 투자 효과 분석", "부서별 AI 도입 효과와 비용 절감 지표를 분석한다.", True, False, False, "SUBMITTED"),
        ("운영", "AI 과제 월간 보고", "월간 과제 진행률과 이슈를 취합해 경영 보고 자료를 작성한다.", False, False, False, "SUBMITTED"),
    ],
    "part002": [
        ("자동화", "업무 자동화 과제 발굴", "반복 업무 후보를 인터뷰하고 자동화 적용 가능성을 검토한다.", True, False, True, "SUBMITTED"),
        ("자동화", "RPA 운영 현황 관리", "RPA 봇 실행 로그와 실패 원인을 점검한다.", False, False, True, "SUBMITTED"),
        ("자동화", "자동화 표준 템플릿 관리", "자동화 설계서와 테스트 체크리스트 표준 양식을 관리한다.", False, False, False, "SUBMITTED"),
    ],
    "part003": [
        ("데이터", "업무 데이터 카탈로그 관리", "AI 학습 후보 데이터의 위치와 접근 권한을 정리한다.", True, False, True, "APPROVED"),
        ("데이터", "데이터 품질 기준 수립", "업무 데이터 정합성 기준과 예외 처리 방식을 정의한다.", True, False, False, "APPROVED"),
        ("데이터", "데이터 보존 정책 점검", "보존 기간과 삭제 기준을 점검하고 이행 현황을 기록한다.", False, False, True, "APPROVED"),
    ],
    "part004": [
        ("DX", "프로세스 개선 과제 관리", "현업 프로세스 개선 후보를 수집하고 개선 효과를 산정한다.", True, False, True, "SUBMITTED"),
        ("DX", "프로세스 표준화 검토", "팀 간 중복 절차를 비교해 표준 프로세스 후보를 도출한다.", False, False, False, "SUBMITTED"),
    ],
    "part005": [
        ("지원", "현업 요청 채널 운영", "현업 문의와 개선 요청을 접수하고 처리 상태를 관리한다.", False, False, True, "REJECTED"),
        ("지원", "보안 예외 요청 검토", "시스템 접근 예외 요청의 사유와 승인 이력을 점검한다.", True, False, True, "REJECTED"),
    ],
    "part006": [
        ("직속", "정보전략 로드맵 관리", "팀 직속 전략 과제와 실행 일정을 관리한다.", True, False, False, "SUBMITTED"),
        ("직속", "예산 계획 수립", "AI/IT 투자 예산 초안과 집행 우선순위를 정리한다.", False, False, True, "SUBMITTED"),
    ],
    "part007": [
        ("플랫폼", "생성형 AI 플랫폼 운영", "사내 생성형 AI 플랫폼 배포와 운영 정책을 관리한다.", True, True, True, "SUBMITTED"),
        ("플랫폼", "모델 사용량 모니터링", "모델 호출량과 비용 이상 징후를 분석한다.", True, False, False, "SUBMITTED"),
        ("플랫폼", "권한 신청 처리", "플랫폼 사용자 권한 신청과 회수 이력을 관리한다.", False, False, True, "SUBMITTED"),
    ],
    "part008": [
        ("검증", "프롬프트 품질 검증", "업무별 프롬프트의 응답 정확도와 금칙어 위험을 검토한다.", True, False, True, "DRAFT"),
        ("검증", "평가 데이터셋 관리", "프롬프트 평가용 샘플과 채점 기준을 관리한다.", True, False, False, "UPLOADED"),
    ],
    "part009": [
        ("서비스", "업무봇 시나리오 운영", "부서별 업무봇 시나리오와 답변 기준을 운영한다.", True, False, True, "APPROVED"),
        ("서비스", "LLM 장애 대응", "LLM 서비스 장애 접수와 원인 분석 결과를 관리한다.", False, False, True, "APPROVED"),
    ],
    "part010": [
        ("혁신", "실 직속 혁신 과제 관리", "실장 직속 혁신 과제의 보안 등급과 의사결정 이력을 관리한다.", True, True, True, "SUBMITTED"),
        ("혁신", "AI PoC 기술 검토", "신규 AI PoC의 기술 타당성과 적용 리스크를 검토한다.", True, False, False, "SUBMITTED"),
    ],
    "part011": [
        ("클라우드", "클라우드 전환 전략 수립", "시스템별 전환 우선순위와 보안 요건을 정리한다.", True, False, True, "SUBMITTED"),
        ("클라우드", "클라우드 비용 분석", "서비스별 사용량과 비용 추이를 분석한다.", False, False, False, "SUBMITTED"),
    ],
    "part012": [
        ("운영", "전환 운영 표준 관리", "전환 작업 표준 절차와 점검 항목을 관리한다.", False, False, True, "DRAFT"),
        ("운영", "운영 이슈 접수", "전환 이후 운영 이슈를 접수하고 처리 담당자를 지정한다.", False, False, False, "DRAFT"),
    ],
}


APPROVALS_BY_PART = {
    "part001": {"status": "PENDING", "current_step": 1, "created_days_ago": 1},
    "part002": {"status": "PENDING", "current_step": 2, "created_days_ago": 2},
    "part003": {"status": "APPROVED", "current_step": 3, "created_days_ago": 7},
    "part004": {"status": "PENDING", "current_step": 1, "created_days_ago": 1},
    "part005": {"status": "REJECTED", "current_step": 1, "created_days_ago": 5},
    "part006": {"status": "PENDING", "current_step": 1, "created_days_ago": 3},
    "part007": {"status": "PENDING", "current_step": 1, "created_days_ago": 1},
    "part009": {"status": "APPROVED", "current_step": 3, "created_days_ago": 6},
    "part010": {"status": "PENDING", "current_step": 1, "created_days_ago": 2},
    "part011": {"status": "PENDING", "current_step": 1, "created_days_ago": 1},
}


def _sqlite_connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _org_payload(org: Organization) -> dict[str, str | None]:
    return {
        "org_type": org.org_type,
        "group_head_id": org.group_head_id,
        "team_head_id": org.team_head_id,
        "division_head_id": org.division_head_id,
    }


def _approver_info(org: Organization, employee_id: str) -> tuple[str, str]:
    if employee_id == org.group_head_id:
        return org.group_head_name or employee_id, "그룹장"
    if employee_id == org.team_head_id:
        return org.team_head_name or employee_id, "팀장"
    if employee_id == org.division_head_id:
        return org.division_head_name, "실장"
    return employee_id, "승인자"


def _seed_users(db, org_by_part_head_id: dict[str, Organization]) -> dict[str, User]:
    user_rows = [
        ("admin001", "관리자", "ADMIN", "part001"),
        ("div001", "김다현", "APPROVER", "part001"),
        ("div002", "최서윤", "APPROVER", "part011"),
        ("team001", "이서준", "APPROVER", "part001"),
        ("team002", "정하린", "APPROVER", "part007"),
        ("team003", "유재민", "APPROVER", "part011"),
        ("group001", "박민재", "APPROVER", "part001"),
        ("group002", "조현우", "APPROVER", "part004"),
        ("group003", "문태준", "APPROVER", "part007"),
        ("group004", "장도영", "APPROVER", "part009"),
        ("group005", "고민석", "APPROVER", "part011"),
        ("part001", "최유진", "INPUTTER", "part001"),
        ("part002", "강민호", "INPUTTER", "part002"),
        ("part003", "한서연", "INPUTTER", "part003"),
        ("part004", "오지훈", "INPUTTER", "part004"),
        ("part005", "윤지아", "INPUTTER", "part005"),
        ("part006", "신도윤", "INPUTTER", "part006"),
        ("part007", "문하늘", "INPUTTER", "part007"),
        ("part008", "배수아", "INPUTTER", "part008"),
        ("part009", "정우성", "INPUTTER", "part009"),
        ("part010", "노은채", "INPUTTER", "part010"),
        ("part011", "서민준", "INPUTTER", "part011"),
        ("part012", "양지후", "INPUTTER", "part012"),
    ]
    users = {}
    for employee_id, name, role, org_key in user_rows:
        org = org_by_part_head_id[org_key]
        user = User(
            employee_id=employee_id,
            name=name,
            role=role,
            organization_id=org.id,
        )
        db.add(user)
        users[employee_id] = user
    db.flush()
    return users


def _seed_reference_data(db) -> None:
    db.add_all(
        [
            ConfidentialQuestion(
                question_text="업무에 외부 공개가 제한되는 사내 전략/운영/보안 정보가 포함됩니까?",
                options=[NONE_OPTION, YES_OPTION],
                is_active=True,
                sort_order=1,
            ),
            NationalTechQuestion(
                question_text="국가핵심기술 판단 기준에 해당하는 기술/공정/설계 정보가 포함됩니까?",
                options=[NONE_OPTION, YES_OPTION],
                is_active=True,
                sort_order=1,
            ),
            SystemSetting(
                input_deadline=date(2026, 5, 31),
                description="2026년 상반기 기밀업무 분류 시범 입력",
                collection_locked=False,
            ),
        ]
    )
    for column_key, example_text in [
        ("sub_part", "예: 전략, 자동화, 데이터, 플랫폼"),
        ("major_task", "예: AI 과제 포트폴리오 관리"),
        ("detail_task", "업무 내용, 산출물, 취급 정보가 드러나도록 작성"),
        ("confidential", "기밀 여부는 해당 없음/해당 됨 중 하나만 선택"),
        ("national_tech", "국가핵심기술은 해당 없음/해당 됨 중 하나만 선택"),
        ("compliance", "개인정보, 계약, 법규 준수 대상 여부"),
        ("assignees", "파트 CSV로 등록된 담당자 Knox ID 기준 선택"),
        ("storage_location", "예: Confluence, SharePoint, 사내 업무 시스템"),
        ("related_menu", "업무가 수행되는 시스템 메뉴명"),
        ("share_scope", "공유 범위: 사업부/BU, 본부/실, 조직 내"),
    ]:
        db.add(ColumnTooltip(column_key=column_key, example_text=example_text))


def _seed_members(db, org_by_part_head_id: dict[str, Organization]) -> dict[int, list[PartMember]]:
    members_by_org_id = {}
    for part_head_id, rows in PART_MEMBERS.items():
        org = org_by_part_head_id[part_head_id]
        members_by_org_id[org.id] = []
        for name, knox_id in rows:
            member = PartMember(
                organization_id=org.id,
                part_name=org.part_name,
                name=name,
                knox_id=knox_id,
            )
            db.add(member)
            members_by_org_id[org.id].append(member)
    db.flush()
    return members_by_org_id


def _classification_fields(is_confidential: bool, is_national_tech: bool, is_compliance: bool) -> dict:
    return {
        "conf_data_type": "사내 전략/운영 정보" if is_confidential else None,
        "conf_owner_user": "OWNER" if is_confidential else None,
        "ntech_data_type": "AI 모델 학습/추론 기술 정보" if is_national_tech else None,
        "ntech_owner_user": "OWNER" if is_national_tech else None,
        "comp_data_type": "개인정보/계약/권한 이력" if is_compliance else None,
        "comp_owner_user": "USER" if is_compliance else None,
    }


def _seed_tasks(
    db,
    org_by_part_head_id: dict[str, Organization],
    users: dict[str, User],
    members_by_org_id: dict[int, list[PartMember]],
) -> dict[int, list[TaskEntry]]:
    tasks_by_org_id = {}
    for part_head_id, task_rows in TASKS_BY_PART.items():
        org = org_by_part_head_id[part_head_id]
        created_by = users[part_head_id]
        tasks_by_org_id[org.id] = []
        for index, row in enumerate(task_rows, start=1):
            sub_part, major_task, detail_task, is_confidential, is_national_tech, is_compliance, status = row
            task = TaskEntry(
                organization_id=org.id,
                created_by=created_by.id,
                sub_part=sub_part,
                major_task=major_task,
                detail_task=detail_task,
                is_confidential=is_confidential,
                is_national_tech=is_national_tech,
                is_compliance=is_compliance,
                storage_location="Confluence / 사내 업무 시스템",
                related_menu="기밀업무 분류 관리",
                share_scope="ORG_UNIT",
                status=status,
                created_at=BASE_TIME - timedelta(days=10 - index),
                updated_at=BASE_TIME - timedelta(days=4 - min(index, 3)),
                **_classification_fields(is_confidential, is_national_tech, is_compliance),
            )
            db.add(task)
            db.flush()
            tasks_by_org_id[org.id].append(task)
            db.add(
                TaskQuestionCheck(
                    task_entry_id=task.id,
                    question_type="CONFIDENTIAL",
                    question_id=1,
                    selected_options=json.dumps(
                        [YES_OPTION if is_confidential else NONE_OPTION],
                        ensure_ascii=False,
                    ),
                )
            )
            db.add(
                TaskQuestionCheck(
                    task_entry_id=task.id,
                    question_type="NATIONAL_TECH",
                    question_id=1,
                    selected_options=json.dumps(
                        [YES_OPTION if is_national_tech else NONE_OPTION],
                        ensure_ascii=False,
                    ),
                )
            )
            for member in members_by_org_id.get(org.id, [])[:2]:
                db.add(
                    TaskAssignee(
                        task_entry_id=task.id,
                        part_name=org.part_name,
                        name=member.name,
                        knox_id=member.knox_id,
                    )
                )
    db.flush()
    return tasks_by_org_id


def _step_status(request_status: str, current_step: int, step_order: int) -> str:
    if request_status == "APPROVED":
        return "APPROVED"
    if request_status == "REJECTED":
        if step_order < current_step:
            return "APPROVED"
        return "REJECTED" if step_order == current_step else "PENDING"
    if step_order < current_step:
        return "APPROVED"
    return "PENDING"


def _seed_approvals(
    db,
    org_by_part_head_id: dict[str, Organization],
    users: dict[str, User],
    tasks_by_org_id: dict[int, list[TaskEntry]],
) -> None:
    for part_head_id, scenario in APPROVALS_BY_PART.items():
        org = org_by_part_head_id[part_head_id]
        path = build_approval_path(_org_payload(org))
        created_at = BASE_TIME - timedelta(days=scenario["created_days_ago"])
        current_step = min(scenario["current_step"], len(path))
        request = ApprovalRequest(
            organization_id=org.id,
            requested_by=users[part_head_id].id,
            status=scenario["status"],
            current_step=current_step,
            total_steps=len(path),
            reject_reason="업무 설명에 보안 예외 처리 기준을 보완해 주세요."
            if scenario["status"] == "REJECTED"
            else None,
            created_at=created_at,
            updated_at=created_at + timedelta(hours=6),
        )
        db.add(request)
        db.flush()
        for step_order, approver_employee_id in enumerate(path, start=1):
            status = _step_status(scenario["status"], current_step, step_order)
            approver_name, approver_role = _approver_info(org, approver_employee_id)
            step = ApprovalStep(
                approval_request_id=request.id,
                step_order=step_order,
                approver_employee_id=approver_employee_id,
                approver_name=approver_name,
                approver_role=approver_role,
                status=status,
                reject_reason=request.reject_reason if status == "REJECTED" else None,
                acted_at=created_at + timedelta(hours=step_order * 4)
                if status in {"APPROVED", "REJECTED"}
                else None,
                created_at=created_at,
            )
            db.add(step)
            db.flush()
            if status in {"APPROVED", "REJECTED"}:
                for index, task in enumerate(tasks_by_org_id.get(org.id, []), start=1):
                    decision = "REJECTED" if status == "REJECTED" and index == 1 else "APPROVED"
                    db.add(
                        ApprovalTaskReview(
                            approval_request_id=request.id,
                            approval_step_id=step.id,
                            task_entry_id=task.id,
                            reviewer_employee_id=approver_employee_id,
                            decision=decision,
                            comment="세부업무와 데이터 유형 보완 필요"
                            if decision == "REJECTED"
                            else None,
                            created_at=step.acted_at or created_at,
                            updated_at=step.acted_at or created_at,
                        )
                    )


def _seed_audit_logs(db) -> None:
    rows = [
        ("LOGIN", "admin001", "ADMIN", "User", "admin001", "SUCCESS", "관리자 시연 데이터 확인"),
        ("TASK_SUBMIT", "part001", "INPUTTER", "ApprovalRequest", "part001", "SUCCESS", "AI전략기획파트 승인 요청"),
        ("TASK_SUBMIT", "part002", "INPUTTER", "ApprovalRequest", "part002", "SUCCESS", "업무자동화파트 승인 요청"),
        ("APPROVE", "group001", "APPROVER", "ApprovalStep", "part002", "SUCCESS", "1단계 그룹 승인 완료"),
        ("REJECT", "group002", "APPROVER", "ApprovalStep", "part005", "SUCCESS", "현업지원파트 보완 요청"),
    ]
    for index, (action, employee_id, role, target_type, target_id, status, message) in enumerate(rows):
        db.add(
            AuditLog(
                action=action,
                employee_id=employee_id,
                role=role,
                target_type=target_type,
                target_id=target_id,
                status=status,
                message=message,
                created_at=BASE_TIME - timedelta(hours=12 - index),
            )
        )


def seed_demo_data(database_url: str) -> dict[str, int]:
    engine = create_engine(database_url, connect_args=_sqlite_connect_args(database_url))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    try:
        organizations = []
        for row in ORGANIZATIONS:
            org = Organization(**row)
            db.add(org)
            organizations.append(org)
        db.flush()
        org_by_part_head_id = {org.part_head_id: org for org in organizations}
        users = _seed_users(db, org_by_part_head_id)
        _seed_reference_data(db)
        members_by_org_id = _seed_members(db, org_by_part_head_id)
        tasks_by_org_id = _seed_tasks(db, org_by_part_head_id, users, members_by_org_id)
        _seed_approvals(db, org_by_part_head_id, users, tasks_by_org_id)
        _seed_audit_logs(db)
        db.commit()
        return {
            "organizations": len(organizations),
            "users": len(users),
            "tasks": sum(len(tasks) for tasks in tasks_by_org_id.values()),
            "approvals": len(APPROVALS_BY_PART),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset and seed realistic demo data.")
    parser.add_argument("--database-url", default="sqlite:///./dev.db")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Required guard. Drops existing tables before seeding demo data.",
    )
    args = parser.parse_args()
    if not args.reset:
        raise SystemExit("Refusing to overwrite data without --reset.")
    counts = seed_demo_data(args.database_url)
    print(
        "seeded demo data: "
        f"organizations={counts['organizations']}, "
        f"users={counts['users']}, "
        f"tasks={counts['tasks']}, "
        f"approvals={counts['approvals']}"
    )


if __name__ == "__main__":
    main()
