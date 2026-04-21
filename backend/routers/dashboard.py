from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, require_admin
from backend.models import ApprovalRequest, Organization, TaskEntry

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _task_count(db: Session) -> int:
    return db.scalar(select(func.count(TaskEntry.id))) or 0


def _count_tasks_where(db: Session, expression) -> int:
    return db.scalar(select(func.count(TaskEntry.id)).where(expression)) or 0


def _completion_items(db: Session) -> list[dict]:
    organizations = db.scalars(select(Organization).order_by(Organization.id)).all()
    items = []
    for org in organizations:
        total_tasks = db.scalar(
            select(func.count(TaskEntry.id)).where(TaskEntry.organization_id == org.id)
        ) or 0
        approved_tasks = db.scalar(
            select(func.count(TaskEntry.id))
            .where(TaskEntry.organization_id == org.id)
            .where(TaskEntry.status == "APPROVED")
        ) or 0
        rate = round((approved_tasks / total_tasks) * 100, 1) if total_tasks else 0.0
        items.append(
            {
                "organization_id": org.id,
                "division_name": org.division_name,
                "team_name": org.team_name,
                "group_name": org.group_name,
                "part_name": org.part_name,
                "total_tasks": total_tasks,
                "approved_tasks": approved_tasks,
                "completion_rate": rate,
            }
        )
    return items


def _approval_status_counts(db: Session) -> dict[str, int]:
    statuses = {"PENDING": 0, "IN_PROGRESS": 0, "APPROVED": 0, "REJECTED": 0}
    rows = db.execute(
        select(ApprovalRequest.status, func.count(ApprovalRequest.id)).group_by(
            ApprovalRequest.status
        )
    ).all()
    for status, count in rows:
        statuses[status] = count
    return statuses


@router.get("/summary")
def read_dashboard_summary(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin(user)
    total_parts = db.scalar(select(func.count(Organization.id))) or 0
    completed_parts = (
        db.scalar(
            select(func.count(distinct(TaskEntry.organization_id))).where(
                TaskEntry.status == "APPROVED"
            )
        )
        or 0
    )
    total_tasks = _task_count(db)
    confidential_count = _count_tasks_where(db, TaskEntry.is_confidential.is_(True))
    national_tech_count = _count_tasks_where(db, TaskEntry.is_national_tech.is_(True))
    compliance_count = _count_tasks_where(db, TaskEntry.is_compliance.is_(True))
    pending_approvals = (
        db.scalar(
            select(func.count(ApprovalRequest.id)).where(
                ApprovalRequest.status == "PENDING"
            )
        )
        or 0
    )
    rejected_requests = (
        db.scalar(
            select(func.count(ApprovalRequest.id)).where(
                ApprovalRequest.status == "REJECTED"
            )
        )
        or 0
    )
    return {
        "total_parts": total_parts,
        "completed_parts": completed_parts,
        "completion_rate": round((completed_parts / total_parts) * 100, 1)
        if total_parts
        else 0.0,
        "confidential_task_ratio": round((confidential_count / total_tasks) * 100, 1)
        if total_tasks
        else 0.0,
        "national_tech_count": national_tech_count,
        "compliance_count": compliance_count,
        "pending_approvals": pending_approvals,
        "rejected_requests": rejected_requests,
    }


@router.get("/completion-rate")
def read_completion_rate(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin(user)
    return {"items": _completion_items(db)}


@router.get("/approval-status")
def read_approval_status(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin(user)
    return _approval_status_counts(db)


@router.get("/classification-ratio")
def read_classification_ratio(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin(user)
    total_tasks = _task_count(db)
    confidential_count = _count_tasks_where(db, TaskEntry.is_confidential.is_(True))
    national_tech_count = _count_tasks_where(db, TaskEntry.is_national_tech.is_(True))
    compliance_count = _count_tasks_where(db, TaskEntry.is_compliance.is_(True))
    return {
        "total_tasks": total_tasks,
        "confidential": confidential_count,
        "national_tech": national_tech_count,
        "compliance": compliance_count,
        "confidential_ratio": round((confidential_count / total_tasks) * 100, 1)
        if total_tasks
        else 0.0,
        "national_tech_ratio": round((national_tech_count / total_tasks) * 100, 1)
        if total_tasks
        else 0.0,
        "compliance_ratio": round((compliance_count / total_tasks) * 100, 1)
        if total_tasks
        else 0.0,
    }
