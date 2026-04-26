import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import ensure_can_write_org, get_current_user, require_admin
from backend.models import (
    ApprovalRequest,
    ApprovalStep,
    ApprovalTaskReview,
    Organization,
    PartMember,
    TaskAssignee,
    TaskEntry,
    TaskQuestionCheck,
    User,
)
from backend.services.audit import log_audit
from backend.services.classification import classify_from_answers
from backend.services.collection import ensure_collection_open
from backend.services.excel import EXCEL_MIME_TYPE, non_empty_rows, parse_workbook, write_workbook

router = APIRouter(prefix="/tasks", tags=["tasks"])
admin_router = APIRouter(prefix="/admin/tasks", tags=["admin-tasks"])

TASK_EXPORT_HEADERS = [
    "소파트",
    "대업무",
    "세부업무",
    "기밀 데이터 유형",
    "기밀 소유자/사용자",
    "국가핵심기술 데이터 유형",
    "국가핵심기술 소유자/사용자",
    "Compliance 해당",
    "Compliance 데이터 유형",
    "Compliance 소유자/사용자",
    "보관 장소",
    "관련 메뉴",
    "공유 범위",
    "상태",
]


class TaskQuestionAnswer(BaseModel):
    question_id: int | None = None
    selected_options: list[str]


QuestionAnswerInput = TaskQuestionAnswer | list[str]


class TaskCreate(BaseModel):
    organization_id: int
    sub_part: str | None = None
    major_task: str
    detail_task: str
    storage_location: str | None = None
    related_menu: str | None = None
    share_scope: str | None = None
    confidential_answers: list[QuestionAnswerInput] | None = None
    conf_data_type: str | None = None
    conf_owner_user: str | None = None
    national_tech_answers: list[QuestionAnswerInput] | None = None
    ntech_data_type: str | None = None
    ntech_owner_user: str | None = None
    is_compliance: bool = False
    comp_data_type: str | None = None
    comp_owner_user: str | None = None
    assignee_knox_ids: list[str] | None = None


class TaskUpdate(BaseModel):
    sub_part: str | None = None
    major_task: str | None = None
    detail_task: str | None = None
    storage_location: str | None = None
    related_menu: str | None = None
    share_scope: str | None = None
    status: str | None = None
    confidential_answers: list[QuestionAnswerInput] | None = None
    conf_data_type: str | None = None
    conf_owner_user: str | None = None
    national_tech_answers: list[QuestionAnswerInput] | None = None
    ntech_data_type: str | None = None
    ntech_owner_user: str | None = None
    is_compliance: bool | None = None
    comp_data_type: str | None = None
    comp_owner_user: str | None = None
    assignee_knox_ids: list[str] | None = None


class TaskValidationRow(BaseModel):
    organization_id: int | None = None
    major_task: str | None = None
    detail_task: str | None = None
    confidential_answers: list[QuestionAnswerInput] | None = None
    national_tech_answers: list[QuestionAnswerInput] | None = None
    is_compliance: bool = False
    conf_data_type: str | None = None
    conf_owner_user: str | None = None
    ntech_data_type: str | None = None
    ntech_owner_user: str | None = None
    comp_data_type: str | None = None
    comp_owner_user: str | None = None


class TaskValidationRequest(BaseModel):
    rows: list[TaskValidationRow]


def _ensure_user_row(db: Session, user: dict) -> User:
    db_user = db.scalar(select(User).where(User.employee_id == user["employee_id"]))
    if db_user:
        return db_user
    db_user = User(
        employee_id=user["employee_id"],
        name=user["name"],
        role=user["role"],
        organization_id=user["organization_id"],
    )
    db.add(db_user)
    db.flush()
    return db_user


def _none_if_blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _ensure_can_read_task_org(user: dict, org_id: int | None, db: Session) -> None:
    if org_id is None or user["role"] == "ADMIN":
        return
    if user["organization_id"] == org_id:
        return
    org = db.get(Organization, org_id)
    if user["role"] == "APPROVER" and user.get("managed") and _same_assigned_group(user, org):
        return
    if user["role"] == "APPROVER" and _is_approver_subordinate(user, org):
        return
    if _is_current_approval_step_for_org(user, org_id, db):
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def _same_scope_values(scope_id: str | None, scope_name: str | None, org_id: str | None, org_name: str | None) -> bool:
    if scope_id and scope_name:
        return org_id == scope_id and org_name == scope_name
    if scope_id:
        return org_id == scope_id
    return bool(scope_name and org_name == scope_name)


def _scope_condition(id_column, name_column, scope_id: str | None, scope_name: str | None):
    if scope_id and scope_name:
        return (id_column == scope_id) & (name_column == scope_name)
    if scope_id:
        return id_column == scope_id
    if scope_name:
        return name_column == scope_name
    return None


def _is_approver_subordinate(user: dict, org: Organization | None) -> bool:
    if org is None:
        return False
    employee_id = user["employee_id"]
    current_org = user.get("organization") or {}
    if current_org.get("group_head_id") == employee_id:
        return _same_scope_values(
            current_org.get("group_head_id"),
            current_org.get("group_name"),
            org.group_head_id,
            org.group_name,
        )
    if current_org.get("team_head_id") == employee_id:
        return _same_scope_values(
            current_org.get("team_head_id"),
            current_org.get("team_name"),
            org.team_head_id,
            org.team_name,
        )
    if current_org.get("division_head_id") == employee_id:
        return _same_scope_values(
            current_org.get("division_head_id"),
            current_org.get("division_name"),
            org.division_head_id,
            org.division_name,
        )
    return False


def _same_assigned_group(user: dict, org: Organization | None) -> bool:
    if org is None:
        return False
    user_org = user.get("organization") or {}
    user_group_head_id = user_org.get("group_head_id")
    user_group_name = user_org.get("group_name")
    return _same_scope_values(user_group_head_id, user_group_name, org.group_head_id, org.group_name)


def _is_current_approval_step_for_org(user: dict, org_id: int | None, db: Session) -> bool:
    if org_id is None or user["role"] != "APPROVER":
        return False
    step_count = db.scalar(
        select(func.count(ApprovalStep.id))
        .join(ApprovalRequest, ApprovalRequest.id == ApprovalStep.approval_request_id)
        .where(ApprovalRequest.organization_id == org_id)
        .where(ApprovalRequest.status == "PENDING")
        .where(ApprovalStep.status == "PENDING")
        .where(ApprovalStep.step_order == ApprovalRequest.current_step)
        .where(ApprovalStep.approver_employee_id == user["employee_id"])
    )
    return bool(step_count)


def _readable_task_query(user: dict, db: Session):
    if user["role"] == "ADMIN":
        return select(TaskEntry)
    query = select(TaskEntry).join(Organization, Organization.id == TaskEntry.organization_id)
    if user["role"] == "APPROVER":
        employee_id = user["employee_id"]
        current_org = user.get("organization") or {}
        if current_org.get("group_head_id") == employee_id:
            condition = _scope_condition(
                Organization.group_head_id,
                Organization.group_name,
                current_org.get("group_head_id"),
                current_org.get("group_name"),
            )
            if condition is not None:
                return query.where(condition)
        if current_org.get("team_head_id") == employee_id:
            condition = _scope_condition(
                Organization.team_head_id,
                Organization.team_name,
                current_org.get("team_head_id"),
                current_org.get("team_name"),
            )
            if condition is not None:
                return query.where(condition)
        if current_org.get("division_head_id") == employee_id:
            condition = _scope_condition(
                Organization.division_head_id,
                Organization.division_name,
                current_org.get("division_head_id"),
                current_org.get("division_name"),
            )
            if condition is not None:
                return query.where(condition)
        if user.get("managed"):
            assigned_org = db.get(Organization, user["organization_id"])
            condition = _scope_condition(
                Organization.group_head_id,
                Organization.group_name,
                assigned_org.group_head_id if assigned_org else None,
                assigned_org.group_name if assigned_org else None,
            )
            if condition is not None:
                return query.where(condition)
            return query.where(TaskEntry.organization_id == user["organization_id"])
        return query.where(TaskEntry.organization_id == user["organization_id"])
    return query.where(TaskEntry.organization_id == user["organization_id"])


def _classification_summary_for_org(db: Session, org_id: int) -> dict:
    rows = db.execute(
        select(
            TaskEntry.is_confidential,
            TaskEntry.is_national_tech,
            TaskEntry.is_compliance,
        ).where(TaskEntry.organization_id == org_id)
    ).all()
    applicable = sum(
        1
        for is_confidential, is_national_tech, is_compliance in rows
        if is_confidential or is_national_tech or is_compliance
    )
    total = len(rows)
    return {
        "total": total,
        "applicable": applicable,
        "not_applicable": total - applicable,
    }


def _normalize_answers(answers: list[QuestionAnswerInput] | None) -> list[TaskQuestionAnswer]:
    normalized = []
    for index, answer in enumerate(answers or [], start=1):
        if isinstance(answer, TaskQuestionAnswer):
            normalized.append(answer)
        elif isinstance(answer, dict):
            normalized.append(TaskQuestionAnswer(**answer))
        else:
            normalized.append(
                TaskQuestionAnswer(question_id=index, selected_options=answer)
            )
    return normalized


def _answer_options(answers: list[QuestionAnswerInput] | None) -> list[list[str]]:
    return [answer.selected_options for answer in _normalize_answers(answers)]


def _sync_question_checks(
    db: Session,
    task_id: int,
    question_type: str,
    answers: list[QuestionAnswerInput] | None,
) -> None:
    db.execute(
        delete(TaskQuestionCheck)
        .where(TaskQuestionCheck.task_entry_id == task_id)
        .where(TaskQuestionCheck.question_type == question_type)
    )
    for index, answer in enumerate(_normalize_answers(answers), start=1):
        db.add(
            TaskQuestionCheck(
                task_entry_id=task_id,
                question_type=question_type,
                question_id=answer.question_id or index,
                selected_options=json.dumps(answer.selected_options, ensure_ascii=False),
            )
        )


def _serialize_question_checks(db: Session, task_id: int, question_type: str) -> list[dict]:
    checks = db.scalars(
        select(TaskQuestionCheck)
        .where(TaskQuestionCheck.task_entry_id == task_id)
        .where(TaskQuestionCheck.question_type == question_type)
        .order_by(TaskQuestionCheck.question_id, TaskQuestionCheck.id)
    ).all()
    return [
        {
            "question_id": check.question_id,
            "selected_options": json.loads(check.selected_options),
        }
        for check in checks
    ]


def _serialize_task_review(db: Session, review: ApprovalTaskReview | None) -> dict | None:
    if review is None:
        return None
    return {
        "decision": review.decision,
        "comment": review.comment,
        "reviewer_employee_id": review.reviewer_employee_id,
        "approval_id": review.approval_request_id,
    }


def _latest_task_review(db: Session, task_id: int) -> ApprovalTaskReview | None:
    return db.scalar(
        select(ApprovalTaskReview)
        .where(ApprovalTaskReview.task_entry_id == task_id)
        .order_by(ApprovalTaskReview.updated_at.desc(), ApprovalTaskReview.id.desc())
        .limit(1)
    )


def _serialize_task_assignees(db: Session, task_id: int) -> list[dict]:
    assignees = db.scalars(
        select(TaskAssignee)
        .where(TaskAssignee.task_entry_id == task_id)
        .order_by(TaskAssignee.name, TaskAssignee.knox_id)
    ).all()
    return [
        {
            "name": assignee.name,
            "knox_id": assignee.knox_id,
            "part_name": assignee.part_name,
        }
        for assignee in assignees
    ]


def _normalize_knox_ids(knox_ids: list[str] | None) -> list[str]:
    normalized = []
    seen = set()
    for raw in knox_ids or []:
        knox_id = str(raw or "").strip()
        if not knox_id or knox_id in seen:
            continue
        normalized.append(knox_id)
        seen.add(knox_id)
    return normalized


def _sync_task_assignees(db: Session, task: TaskEntry, knox_ids: list[str] | None) -> None:
    selected_knox_ids = _normalize_knox_ids(knox_ids)
    db.execute(delete(TaskAssignee).where(TaskAssignee.task_entry_id == task.id))
    if not selected_knox_ids:
        return

    org = db.get(Organization, task.organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    members = db.scalars(
        select(PartMember)
        .where(PartMember.organization_id == task.organization_id)
        .where(PartMember.part_name == org.part_name)
        .where(PartMember.knox_id.in_(selected_knox_ids))
    ).all()
    members_by_knox_id = {member.knox_id: member for member in members}
    missing = [knox_id for knox_id in selected_knox_ids if knox_id not in members_by_knox_id]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"파트 인력현황에 없는 담당자입니다: {', '.join(missing)}",
        )
    for knox_id in selected_knox_ids:
        member = members_by_knox_id[knox_id]
        db.add(
            TaskAssignee(
                task_entry_id=task.id,
                part_name=member.part_name,
                name=member.name,
                knox_id=member.knox_id,
            )
        )


def _serialize_rejection_reviews(db: Session, approval_request_id: int) -> list[dict]:
    reviews = db.scalars(
        select(ApprovalTaskReview)
        .where(ApprovalTaskReview.approval_request_id == approval_request_id)
        .order_by(ApprovalTaskReview.id)
    ).all()
    rows = []
    for review in reviews:
        task = db.get(TaskEntry, review.task_entry_id)
        rows.append(
            {
                "task_id": review.task_entry_id,
                "major_task": task.major_task if task else None,
                "decision": review.decision,
                "comment": review.comment,
                "reviewer_employee_id": review.reviewer_employee_id,
            }
        )
    return rows


def _serialize_task(db: Session, task: TaskEntry) -> dict:
    creator = db.get(User, task.created_by)
    org = db.get(Organization, task.organization_id)
    return {
        "id": task.id,
        "organization_id": task.organization_id,
        "division_name": org.division_name if org else None,
        "team_name": org.team_name if org else None,
        "group_name": org.group_name if org else None,
        "part_name": org.part_name if org else None,
        "created_by": task.created_by,
        "created_by_employee_id": creator.employee_id if creator else None,
        "sub_part": task.sub_part,
        "major_task": task.major_task,
        "detail_task": task.detail_task,
        "is_confidential": task.is_confidential,
        "confidential_answers": _serialize_question_checks(db, task.id, "CONFIDENTIAL"),
        "conf_data_type": task.conf_data_type,
        "conf_owner_user": task.conf_owner_user,
        "is_national_tech": task.is_national_tech,
        "national_tech_answers": _serialize_question_checks(db, task.id, "NATIONAL_TECH"),
        "ntech_data_type": task.ntech_data_type,
        "ntech_owner_user": task.ntech_owner_user,
        "is_compliance": task.is_compliance,
        "comp_data_type": task.comp_data_type,
        "comp_owner_user": task.comp_owner_user,
        "storage_location": task.storage_location,
        "related_menu": task.related_menu,
        "share_scope": task.share_scope,
        "status": task.status,
        "assignees": _serialize_task_assignees(db, task.id),
        "latest_review": _serialize_task_review(db, _latest_task_review(db, task.id)),
    }


def _excel_headers() -> list[str]:
    return ["소파트", "대업무", "세부업무"]


def _payloads_from_excel_rows(
    rows: list[list[str]],
    organization_id: int,
) -> list[dict]:
    if not rows:
        return []
    headers = rows[0]
    payloads = []
    for row in rows[1:]:
        values = {header: row[index] if index < len(row) else "" for index, header in enumerate(headers)}
        payloads.append(
            {
                "organization_id": organization_id,
                "sub_part": values.get("소파트") or None,
                "major_task": values.get("대업무") or "",
                "detail_task": values.get("세부업무") or "",
                "confidential_answers": [],
                "conf_data_type": "",
                "conf_owner_user": "",
                "national_tech_answers": [],
                "ntech_data_type": "",
                "ntech_owner_user": "",
                "is_compliance": False,
                "comp_data_type": "",
                "comp_owner_user": "",
                "storage_location": "",
                "related_menu": "",
                "share_scope": "",
            }
        )
    return payloads


def _add_task(db: Session, user: dict, payload: TaskCreate, status_name: str = "DRAFT") -> TaskEntry:
    ensure_can_write_org(user, payload.organization_id, db)
    if db.get(Organization, payload.organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    creator = _ensure_user_row(db, user)
    task = TaskEntry(
        organization_id=payload.organization_id,
        created_by=creator.id,
        sub_part=_none_if_blank(payload.sub_part),
        major_task=payload.major_task,
        detail_task=payload.detail_task,
        is_confidential=classify_from_answers(_answer_options(payload.confidential_answers)),
        conf_data_type=_none_if_blank(payload.conf_data_type),
        conf_owner_user=_none_if_blank(payload.conf_owner_user),
        is_national_tech=classify_from_answers(_answer_options(payload.national_tech_answers)),
        ntech_data_type=_none_if_blank(payload.ntech_data_type),
        ntech_owner_user=_none_if_blank(payload.ntech_owner_user),
        is_compliance=payload.is_compliance,
        comp_data_type=_none_if_blank(payload.comp_data_type),
        comp_owner_user=_none_if_blank(payload.comp_owner_user),
        storage_location=_none_if_blank(payload.storage_location),
        related_menu=_none_if_blank(payload.related_menu),
        share_scope=_none_if_blank(payload.share_scope),
        status=status_name,
    )
    db.add(task)
    db.flush()
    _sync_question_checks(db, task.id, "CONFIDENTIAL", payload.confidential_answers)
    _sync_question_checks(db, task.id, "NATIONAL_TECH", payload.national_tech_answers)
    if payload.assignee_knox_ids is not None:
        _sync_task_assignees(db, task, payload.assignee_knox_ids)
    return task


@router.get("")
def list_tasks(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    org_id: int | None = None,
):
    _ensure_can_read_task_org(user, org_id, db)
    if org_id is not None and _is_current_approval_step_for_org(user, org_id, db):
        return [
            _serialize_task(db, task)
            for task in db.scalars(
                select(TaskEntry).where(TaskEntry.organization_id == org_id)
            ).all()
        ]
    query = _readable_task_query(user, db)
    if org_id is not None:
        query = query.where(TaskEntry.organization_id == org_id)
    return [_serialize_task(db, task) for task in db.scalars(query).all()]


@router.get("/group")
def list_same_group_tasks(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if user["role"] == "INPUTTER":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    query = _readable_task_query(user, db)
    return [_serialize_task(db, task) for task in db.scalars(query).all()]


@router.get("/status")
def read_part_status(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    org_id: int | None = None,
):
    target_org_id = org_id or user["organization_id"]
    _ensure_can_read_task_org(user, target_org_id, db)
    rows = db.execute(
        select(TaskEntry.status, func.count(TaskEntry.id))
        .where(TaskEntry.organization_id == target_org_id)
        .group_by(TaskEntry.status)
    ).all()
    counts = {"UPLOADED": 0, "DRAFT": 0, "SUBMITTED": 0, "APPROVED": 0, "REJECTED": 0}
    for status_name, count in rows:
        counts[status_name] = count
    latest_request = db.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.organization_id == target_org_id)
        .order_by(ApprovalRequest.created_at.desc(), ApprovalRequest.id.desc())
        .limit(1)
    )
    active_request = None
    if counts["SUBMITTED"]:
        active_request = db.scalar(
            select(ApprovalRequest)
            .where(ApprovalRequest.organization_id == target_org_id)
            .where(ApprovalRequest.status.in_(("PENDING", "IN_PROGRESS")))
            .order_by(ApprovalRequest.created_at.desc(), ApprovalRequest.id.desc())
            .limit(1)
        )
    latest_requester = db.get(User, latest_request.requested_by) if latest_request else None
    active_requester = db.get(User, active_request.requested_by) if active_request else None
    can_cancel_approval = bool(
        active_request
        and (
            user["role"] == "ADMIN"
            or (
                active_requester is not None
                and active_requester.employee_id == user["employee_id"]
            )
        )
    )
    return {
        "organization_id": target_org_id,
        "total_tasks": sum(counts.values()),
        "status_counts": counts,
        "classification_summary": _classification_summary_for_org(db, target_org_id),
        "approval_id": latest_request.id if latest_request else None,
        "approval_status": latest_request.status if latest_request else "NOT_REQUESTED",
        "approval_requester_employee_id": latest_requester.employee_id if latest_requester else None,
        "active_approval_id": active_request.id if active_request else None,
        "can_cancel_approval": can_cancel_approval,
        "current_step": latest_request.current_step if latest_request else None,
        "total_steps": latest_request.total_steps if latest_request else None,
    }


@router.get("/rejection")
def read_latest_rejection(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    org_id: int | None = None,
):
    target_org_id = org_id or user["organization_id"]
    _ensure_can_read_task_org(user, target_org_id, db)
    request = db.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.organization_id == target_org_id)
        .where(ApprovalRequest.status == "REJECTED")
        .where(ApprovalRequest.reject_reason.is_not(None))
        .order_by(ApprovalRequest.updated_at.desc(), ApprovalRequest.id.desc())
        .limit(1)
    )
    if request is None:
        return {"has_rejection": False, "reject_reason": None}
    return {
        "has_rejection": True,
        "approval_id": request.id,
        "reject_reason": request.reject_reason,
        "task_reviews": _serialize_rejection_reviews(db, request.id),
    }


@router.get("/template")
def download_task_template(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    _ensure_can_read_task_org(user, user["organization_id"], db)
    content = write_workbook([_excel_headers()])
    return Response(
        content=content,
        media_type=EXCEL_MIME_TYPE,
        headers={"Content-Disposition": 'attachment; filename="tasks-template.xlsx"'},
    )


def _task_query_with_org():
    return select(TaskEntry).join(Organization, Organization.id == TaskEntry.organization_id)


@admin_router.get("")
def list_all_tasks_for_admin(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    division: str | None = None,
    team: str | None = None,
    group: str | None = None,
    part: str | None = None,
    status_name: str | None = None,
    status: str | None = None,
    is_confidential: bool | None = None,
    is_national_tech: bool | None = None,
    is_compliance: bool | None = None,
):
    require_admin(user)
    query = _task_query_with_org()
    if division:
        query = query.where(Organization.division_name.contains(division))
    if team:
        query = query.where(Organization.team_name.contains(team))
    if group:
        query = query.where(Organization.group_name.contains(group))
    if part:
        query = query.where(Organization.part_name.contains(part))
    requested_status = status or status_name
    if requested_status:
        query = query.where(TaskEntry.status == requested_status)
    if is_confidential is not None:
        query = query.where(TaskEntry.is_confidential.is_(is_confidential))
    if is_national_tech is not None:
        query = query.where(TaskEntry.is_national_tech.is_(is_national_tech))
    if is_compliance is not None:
        query = query.where(TaskEntry.is_compliance.is_(is_compliance))
    tasks = db.scalars(query.order_by(Organization.id, TaskEntry.id)).all()
    return {"items": [_serialize_task(db, task) for task in tasks], "total_count": len(tasks)}


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_tasks_from_excel(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(...),
    org_id: int | None = None,
):
    ensure_collection_open(db)
    target_org_id = org_id or user["organization_id"]
    ensure_can_write_org(user, target_org_id, db)
    raw = await file.read()
    try:
        rows = non_empty_rows(parse_workbook(raw))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Excel workbook") from exc

    payloads = _payloads_from_excel_rows(rows, target_org_id)
    tasks = [_add_task(db, user, TaskCreate(**payload), status_name="UPLOADED") for payload in payloads]
    log_audit(
        db,
        action="TASK_IMPORT",
        user=user,
        target_type="Organization",
        target_id=target_org_id,
        message=f"{len(tasks)} rows",
    )
    db.commit()
    for task in tasks:
        db.refresh(task)
    return {
        "imported_count": len(tasks),
        "tasks": [_serialize_task(db, task) for task in tasks],
    }


@router.post("/import/preview")
async def preview_tasks_from_excel(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
    file: UploadFile = File(...),
    org_id: int | None = None,
):
    target_org_id = org_id or user["organization_id"]
    ensure_can_write_org(user, target_org_id, db)
    raw = await file.read()
    try:
        rows = non_empty_rows(parse_workbook(raw))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Excel workbook") from exc

    payloads = _payloads_from_excel_rows(rows, target_org_id)
    validation_rows = [TaskValidationRow(**payload) for payload in payloads]
    validation = _validate_task_rows(validation_rows, user, db)
    return {
        "rows": payloads,
        **validation,
    }


def _validate_task_rows(rows: list[TaskValidationRow], user: dict, db: Session | None = None) -> dict:
    errors = []
    valid_count = 0
    for index, row in enumerate(rows):
        row_errors = []
        if row.organization_id is None:
            row_errors.append(("organization_id", "조직 ID는 필수입니다."))
        else:
            try:
                ensure_can_write_org(user, row.organization_id, db)
            except HTTPException:
                row_errors.append(("organization_id", "조직 접근 권한이 없습니다."))
        if not row.major_task:
            row_errors.append(("major_task", "대업무는 필수입니다."))
        if not row.detail_task:
            row_errors.append(("detail_task", "세부업무는 필수입니다."))

        is_confidential = classify_from_answers(_answer_options(row.confidential_answers))
        if is_confidential:
            if not row.conf_data_type:
                row_errors.append(("conf_data_type", "기밀 데이터 유형은 필수입니다."))
            if not row.conf_owner_user:
                row_errors.append(("conf_owner_user", "기밀 소유자/사용자는 필수입니다."))

        is_national_tech = classify_from_answers(_answer_options(row.national_tech_answers))
        if is_national_tech:
            if not row.ntech_data_type:
                row_errors.append(("ntech_data_type", "국가핵심기술 데이터 유형은 필수입니다."))
            if not row.ntech_owner_user:
                row_errors.append(("ntech_owner_user", "국가핵심기술 소유자/사용자는 필수입니다."))

        if row.is_compliance:
            if not row.comp_data_type:
                row_errors.append(("comp_data_type", "Compliance 데이터 유형은 필수입니다."))
            if not row.comp_owner_user:
                row_errors.append(("comp_owner_user", "Compliance 소유자/사용자는 필수입니다."))

        if row_errors:
            for field, message in row_errors:
                errors.append({"row_index": index, "field": field, "message": message})
        else:
            valid_count += 1

    return {
        "total_count": len(rows),
        "valid_count": valid_count,
        "error_count": len(errors),
        "errors": errors,
    }


@router.post("/validate")
def validate_tasks(
    payload: TaskValidationRequest,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return _validate_task_rows(payload.rows, user, db)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ensure_collection_open(db)
    task = _add_task(db, user, payload)
    log_audit(db, action="TASK_CREATE", user=user, target_type="TaskEntry", target_id=task.id)
    db.commit()
    db.refresh(task)
    return _serialize_task(db, task)


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def create_tasks_bulk(
    payloads: list[TaskCreate],
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ensure_collection_open(db)
    tasks = [_add_task(db, user, payload, status_name="UPLOADED") for payload in payloads]
    log_audit(
        db,
        action="TASK_BULK_CREATE",
        user=user,
        target_type="TaskEntry",
        message=f"{len(tasks)} rows",
    )
    db.commit()
    for task in tasks:
        db.refresh(task)
    return {
        "created_count": len(tasks),
        "tasks": [_serialize_task(db, task) for task in tasks],
    }


@router.put("/{task_id}")
def update_task(
    task_id: int,
    payload: TaskUpdate,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ensure_collection_open(db)
    task = db.get(TaskEntry, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    ensure_can_write_org(user, task.organization_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    assignee_update_requested = "assignee_knox_ids" in update_data
    assignee_knox_ids = update_data.pop("assignee_knox_ids", None)
    for key, value in update_data.items():
        if key == "confidential_answers":
            task.is_confidential = classify_from_answers(_answer_options(value))
            _sync_question_checks(db, task.id, "CONFIDENTIAL", value)
            continue
        if key == "national_tech_answers":
            task.is_national_tech = classify_from_answers(_answer_options(value))
            _sync_question_checks(db, task.id, "NATIONAL_TECH", value)
            continue
        if isinstance(value, str):
            value = _none_if_blank(value)
        setattr(task, key, value)
    if assignee_update_requested:
        _sync_task_assignees(db, task, assignee_knox_ids)
    if task.status == "UPLOADED":
        task.status = "DRAFT"
    log_audit(db, action="TASK_UPDATE", user=user, target_type="TaskEntry", target_id=task.id)
    db.commit()
    db.refresh(task)
    return _serialize_task(db, task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ensure_collection_open(db)
    task = db.get(TaskEntry, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    ensure_can_write_org(user, task.organization_id, db)
    creator = db.get(User, task.created_by)
    is_creator = creator is not None and creator.employee_id == user["employee_id"]
    can_delete_rejected = user["role"] == "INPUTTER" and task.status == "REJECTED"
    if user["role"] != "ADMIN" and not is_creator and not can_delete_rejected:
        raise HTTPException(status_code=403, detail="Only the creator can delete this task")
    db.execute(delete(ApprovalTaskReview).where(ApprovalTaskReview.task_entry_id == task_id))
    db.execute(delete(TaskAssignee).where(TaskAssignee.task_entry_id == task_id))
    db.execute(delete(TaskQuestionCheck).where(TaskQuestionCheck.task_entry_id == task_id))
    log_audit(
        db,
        action="TASK_DELETE",
        user=user,
        target_type="TaskEntry",
        target_id=task_id,
        message=task.major_task,
    )
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
