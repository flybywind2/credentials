ORGANIZATIONS = [
    {
        "id": 1,
        "division_name": "AI전략실",
        "division_head_name": "김실장",
        "division_head_id": "div001",
        "team_name": "AI전략팀",
        "team_head_name": "이팀장",
        "team_head_id": "team001",
        "group_name": "AI실행그룹",
        "group_head_name": "박그룹장",
        "group_head_id": "group001",
        "part_name": "AI전략실행파트",
        "part_head_name": "최파트장",
        "part_head_id": "part001",
        "org_type": "NORMAL",
    }
]

CURRENT_USER = {
    "employee_id": "admin001",
    "name": "관리자",
    "email": "admin001@samsung.com",
    "role": "ADMIN",
    "organization_id": 1,
}

TASKS = [
    {
        "id": 1,
        "organization_id": 1,
        "sub_part": "기획",
        "major_task": "기밀 분류 체계 수립",
        "detail_task": "부서별 세부업무의 기밀 여부와 국가핵심기술 해당 여부를 검토한다.",
        "is_confidential": True,
        "is_national_tech": False,
        "is_compliance": True,
        "status": "DRAFT",
        "storage_location": "사내 업무 시스템",
        "related_menu": "기밀분류관리",
        "share_scope": "ORG_UNIT",
    },
    {
        "id": 2,
        "organization_id": 1,
        "sub_part": "운영",
        "major_task": "승인 현황 관리",
        "detail_task": "파트별 입력 완료율과 승인 진행 상태를 확인한다.",
        "is_confidential": False,
        "is_national_tech": False,
        "is_compliance": False,
        "status": "SUBMITTED",
        "storage_location": "대시보드",
        "related_menu": "승인현황",
        "share_scope": "DIVISION_BU",
    },
]

QUESTIONS = {
    "confidential": [
        {
            "id": 1,
            "question_text": "업무에 외부 공개가 제한되는 설계/공정/운영 정보가 포함됩니까?",
            "options": ["해당 없음", "해당 됨"],
            "sort_order": 1,
        }
    ],
    "national_tech": [
        {
            "id": 1,
            "question_text": "국가핵심기술 판단 기준에 해당하는 기술 정보가 포함됩니까?",
            "options": ["해당 없음", "해당 됨"],
            "sort_order": 1,
        }
    ],
}

PENDING_APPROVALS = [
    {
        "id": 1,
        "organization_id": 1,
        "part_name": "AI전략실행파트",
        "requester": "최파트장",
        "requested_at": "2026-04-21T19:00:00+09:00",
        "task_count": 2,
        "current_step": 1,
        "total_steps": 3,
        "status": "PENDING",
    }
]

DASHBOARD_SUMMARY = {
    "total_parts": 191,
    "completed_parts": 27,
    "completion_rate": 14.1,
    "confidential_task_ratio": 50.0,
    "national_tech_count": 0,
    "compliance_count": 1,
    "pending_approvals": 1,
    "rejected_requests": 0,
}
