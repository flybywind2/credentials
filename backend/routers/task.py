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
    ApprovalTaskReview,
    ConfidentialQuestion,
    NationalTechQuestion,
    Organization,
    TaskEntry,
    TaskQuestionCheck,
    User,
)
from backend.services.classification import classify_from_answers
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


def _same_group(user: dict, org: Organization | None) -> bool:
    if org is None:
        return False
    user_org = user.get("organization") or {}
    user_group_head_id = user_org.get("group_head_id")
    if user_group_head_id and org.group_head_id == user_group_head_id:
        return True
    user_group_name = user_org.get("group_name")
    return bool(user_group_name and org.group_name == user_group_name)


def _ensure_can_read_task_org(user: dict, org_id: int | None, db: Session) -> None:
    if org_id is None or user["role"] in {"ADMIN", "APPROVER"}:
        return
    if user["organization_id"] == org_id:
        return
    if user["role"] == "INPUTTER" and _same_group(user, db.get(Organization, org_id)):
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


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
        "latest_review": _serialize_task_review(db, _latest_task_review(db, task.id)),
    }


def _active_questions(db: Session) -> tuple[list[ConfidentialQuestion], list[NationalTechQuestion]]:
    confidential = db.scalars(
        select(ConfidentialQuestion)
        .where(ConfidentialQuestion.is_active.is_(True))
        .order_by(ConfidentialQuestion.sort_order, ConfidentialQuestion.id)
    ).all()
    national_tech = db.scalars(
        select(NationalTechQuestion)
        .where(NationalTechQuestion.is_active.is_(True))
        .order_by(NationalTechQuestion.sort_order, NationalTechQuestion.id)
    ).all()
    return confidential, national_tech


def _excel_headers(
    confidential: list[ConfidentialQuestion],
    national_tech: list[NationalTechQuestion],
) -> list[str]:
    return (
        ["소파트", "대업무", "세부업무"]
        + [f"기밀 문항 {index}" for index, _ in enumerate(confidential, start=1)]
        + ["기밀 데이터 유형", "기밀 소유자/사용자"]
        + [f"국가핵심기술 문항 {index}" for index, _ in enumerate(national_tech, start=1)]
        + ["국가핵심기술 데이터 유형", "국가핵심기술 소유자/사용자"]
        + [
            "Compliance 해당",
            "Compliance 데이터 유형",
            "Compliance 소유자/사용자",
            "보관 장소",
            "관련 메뉴",
            "공유 범위",
        ]
    )


def _split_options(value: str | None) -> list[str]:
    if not value:
        return []
    normalized = value.replace(",", ";")
    return [item.strip() for item in normalized.split(";") if item.strip()]


def _owner_value(value: str | None) -> str:
    owner_map = {"소유자": "OWNER", "사용자": "USER", "OWNER": "OWNER", "USER": "USER"}
    return owner_map.get((value or "").strip(), "")


def _share_scope_value(value: str | None) -> str:
    scope_map = {
        "부문/사업부": "DIVISION_BU",
        "사업부": "BUSINESS_UNIT",
        "실/팀/그룹": "ORG_UNIT",
        "DIVISION_BU": "DIVISION_BU",
        "BUSINESS_UNIT": "BUSINESS_UNIT",
        "ORG_UNIT": "ORG_UNIT",
    }
    return scope_map.get((value or "").strip(), "")


def _truthy(value: str | None) -> bool:
    return (value or "").strip().upper() in {"Y", "YES", "TRUE", "1", "해당"}


def _payloads_from_excel_rows(
    rows: list[list[str]],
    confidential: list[ConfidentialQuestion],
    national_tech: list[NationalTechQuestion],
    organization_id: int,
) -> list[dict]:
    if not rows:
        return []
    headers = rows[0]
    payloads = []
    for row in rows[1:]:
        values = {header: row[index] if index < len(row) else "" for index, header in enumerate(headers)}
        confidential_answers = [
            {
                "question_id": question.id,
                "selected_options": _split_options(values.get(f"기밀 문항 {index}")),
            }
            for index, question in enumerate(confidential, start=1)
        ]
        national_tech_answers = [
            {
                "question_id": question.id,
                "selected_options": _split_options(values.get(f"국가핵심기술 문항 {index}")),
            }
            for index, question in enumerate(national_tech, start=1)
        ]
        payloads.append(
            {
                "organization_id": organization_id,
                "sub_part": values.get("소파트") or None,
                "major_task": values.get("대업무") or "",
                "detail_task": values.get("세부업무") or "",
                "confidential_answers": confidential_answers,
                "conf_data_type": values.get("기밀 데이터 유형") or "",
                "conf_owner_user": _owner_value(values.get("기밀 소유자/사용자")),
                "national_tech_answers": national_tech_answers,
                "ntech_data_type": values.get("국가핵심기술 데이터 유형") or "",
                "ntech_owner_user": _owner_value(values.get("국가핵심기술 소유자/사용자")),
                "is_compliance": _truthy(values.get("Compliance 해당")),
                "comp_data_type": values.get("Compliance 데이터 유형") or "",
                "comp_owner_user": _owner_value(values.get("Compliance 소유자/사용자")),
                "storage_location": values.get("보관 장소") or "",
                "related_menu": values.get("관련 메뉴") or "",
                "share_scope": _share_scope_value(values.get("공유 범위")),
            }
        )
    return payloads


def _add_task(db: Session, user: dict, payload: TaskCreate) -> TaskEntry:
    ensure_can_write_org(user, payload.organization_id)
    if db.get(Organization, payload.organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    creator = _ensure_user_row(db, user)
    task = TaskEntry(
        organization_id=payload.organization_id,
        created_by=creator.id,
        sub_part=payload.sub_part,
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
        storage_location=payload.storage_location,
        related_menu=payload.related_menu,
        share_scope=payload.share_scope,
        status="DRAFT",
    )
    db.add(task)
    db.flush()
    _sync_question_checks(db, task.id, "CONFIDENTIAL", payload.confidential_answers)
    _sync_question_checks(db, task.id, "NATIONAL_TECH", payload.national_tech_answers)
    return task


@router.get("")
def list_tasks(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    org_id: int | None = None,
):
    _ensure_can_read_task_org(user, org_id, db)
    query = select(TaskEntry)
    if org_id is not None:
        query = query.where(TaskEntry.organization_id == org_id)
    return [_serialize_task(db, task) for task in db.scalars(query).all()]


@router.get("/group")
def list_same_group_tasks(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    current_org = db.get(Organization, user["organization_id"])
    if current_org is None:
        return []
    query = select(TaskEntry).join(Organization, Organization.id == TaskEntry.organization_id)
    if user["role"] == "ADMIN":
        pass
    elif current_org.group_head_id:
        query = query.where(Organization.group_head_id == current_org.group_head_id)
    elif current_org.group_name:
        query = query.where(Organization.group_name == current_org.group_name)
    else:
        query = query.where(TaskEntry.organization_id == current_org.id)
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
    counts = {"DRAFT": 0, "SUBMITTED": 0, "APPROVED": 0, "REJECTED": 0}
    for status_name, count in rows:
        counts[status_name] = count
    return {
        "organization_id": target_org_id,
        "total_tasks": sum(counts.values()),
        "status_counts": counts,
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
    confidential, national_tech = _active_questions(db)
    content = write_workbook([_excel_headers(confidential, national_tech)])
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
    target_org_id = org_id or user["organization_id"]
    ensure_can_write_org(user, target_org_id)
    raw = await file.read()
    try:
        rows = non_empty_rows(parse_workbook(raw))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Excel workbook") from exc

    confidential, national_tech = _active_questions(db)
    payloads = _payloads_from_excel_rows(rows, confidential, national_tech, target_org_id)
    tasks = [_add_task(db, user, TaskCreate(**payload)) for payload in payloads]
    db.commit()
    for task in tasks:
        db.refresh(task)
    return {
        "imported_count": len(tasks),
        "tasks": [_serialize_task(db, task) for task in tasks],
    }


@router.post("/validate")
def validate_tasks(
    payload: TaskValidationRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    errors = []
    valid_count = 0
    for index, row in enumerate(payload.rows):
        row_errors = []
        if row.organization_id is None:
            row_errors.append(("organization_id", "조직 ID는 필수입니다."))
        else:
            try:
                if user["role"] != "ADMIN" and user["organization_id"] != row.organization_id:
                    raise HTTPException(status_code=403, detail="Insufficient permissions")
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
        "total_count": len(payload.rows),
        "valid_count": valid_count,
        "error_count": len(errors),
        "errors": errors,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    task = _add_task(db, user, payload)
    db.commit()
    db.refresh(task)
    return _serialize_task(db, task)


@router.put("/{task_id}")
def update_task(
    task_id: int,
    payload: TaskUpdate,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    task = db.get(TaskEntry, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    ensure_can_write_org(user, task.organization_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
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
    db.commit()
    db.refresh(task)
    return _serialize_task(db, task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    task = db.get(TaskEntry, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    ensure_can_write_org(user, task.organization_id)
    creator = db.get(User, task.created_by)
    if user["role"] != "ADMIN" and (creator is None or creator.employee_id != user["employee_id"]):
        raise HTTPException(status_code=403, detail="Only the creator can delete this task")
    db.execute(delete(ApprovalTaskReview).where(ApprovalTaskReview.task_entry_id == task_id))
    db.execute(delete(TaskQuestionCheck).where(TaskQuestionCheck.task_entry_id == task_id))
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
