from datetime import datetime, timezone
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.dependencies import ensure_can_write_org, get_current_user, require_approver_or_admin
from backend.models import ApprovalRequest, ApprovalStep, ApprovalTaskReview, Organization, TaskEntry, User
from backend.services.approval_flow import build_approval_path
from backend.services.email import EmailMessage, build_approval_email_html, employee_email, get_email_service

router = APIRouter(prefix="/approvals", tags=["approvals"])
logger = logging.getLogger(__name__)
email_service = get_email_service()


class ApprovalTaskReviewInput(BaseModel):
    task_id: int
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    comment: str | None = None


class RejectRequest(BaseModel):
    reject_reason: str = Field(min_length=1)
    task_reviews: list[ApprovalTaskReviewInput] = Field(default_factory=list)


class ApprovalActionRequest(BaseModel):
    task_reviews: list[ApprovalTaskReviewInput] = Field(default_factory=list)


class EditRequest(BaseModel):
    reason: str = Field(min_length=1)


def _approval_detail_url(approval_id: int) -> str:
    return f"{settings.app_base_url.rstrip('/')}/approver/approvals/{approval_id}"


def _notify(
    subject: str,
    recipients: list[str | None],
    body: str,
    action_url: str | None = None,
    action_label: str = "승인 검토 바로가기",
) -> None:
    target_recipients = [recipient for recipient in recipients if recipient]
    if not target_recipients:
        return
    email_body = f"{body}\n\n{action_label}: {action_url}" if action_url else body
    try:
        email_service.send(
            EmailMessage(
                subject=subject,
                recipients=target_recipients,
                body=email_body,
                html_body=build_approval_email_html(
                    subject,
                    body,
                    action_url=action_url,
                    action_label=action_label,
                ),
            )
        )
    except Exception:
        logger.exception("email notification failed subject=%s", subject)


def _approver_info(org: Organization, employee_id: str) -> tuple[str, str]:
    if employee_id == org.group_head_id:
        return org.group_head_name or employee_id, "그룹장"
    if employee_id == org.team_head_id:
        return org.team_head_name or employee_id, "팀장"
    if employee_id == org.division_head_id:
        return org.division_head_name, "실장"
    return employee_id, "승인자"


def _serialize_request(db: Session, request: ApprovalRequest) -> dict:
    org = db.get(Organization, request.organization_id)
    requester = db.get(User, request.requested_by)
    steps = db.scalars(
        select(ApprovalStep)
        .where(ApprovalStep.approval_request_id == request.id)
        .order_by(ApprovalStep.step_order)
    ).all()
    return {
        "id": request.id,
        "organization_id": request.organization_id,
        "part_name": org.part_name if org else None,
        "requester": requester.name if requester else None,
        "requested_at": request.created_at.isoformat() if request.created_at else None,
        "status": request.status,
        "reject_reason": request.reject_reason,
        "current_step": request.current_step,
        "total_steps": request.total_steps,
        "steps": [
            {
                "id": step.id,
                "step_order": step.step_order,
                "approver_employee_id": step.approver_employee_id,
                "approver_name": step.approver_name,
                "approver_role": step.approver_role,
                "status": step.status,
            }
            for step in steps
        ],
        "task_reviews": _serialize_task_reviews(db, request.id),
    }


def _serialize_task_reviews(db: Session, approval_request_id: int) -> list[dict]:
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


def _submission_errors(tasks: list[TaskEntry]) -> list[dict]:
    errors = []
    for task in tasks:
        if not task.major_task:
            errors.append({"task_id": task.id, "field": "major_task", "message": "대업무는 필수입니다."})
        if not task.detail_task:
            errors.append({"task_id": task.id, "field": "detail_task", "message": "세부업무는 필수입니다."})
        if task.is_confidential:
            if not task.conf_data_type:
                errors.append({"task_id": task.id, "field": "conf_data_type", "message": "기밀 데이터 유형은 필수입니다."})
            if not task.conf_owner_user:
                errors.append({"task_id": task.id, "field": "conf_owner_user", "message": "기밀 소유자/사용자는 필수입니다."})
        if task.is_national_tech:
            if not task.ntech_data_type:
                errors.append({"task_id": task.id, "field": "ntech_data_type", "message": "국가핵심기술 데이터 유형은 필수입니다."})
            if not task.ntech_owner_user:
                errors.append({"task_id": task.id, "field": "ntech_owner_user", "message": "국가핵심기술 소유자/사용자는 필수입니다."})
        if task.is_compliance:
            if not task.comp_data_type:
                errors.append({"task_id": task.id, "field": "comp_data_type", "message": "Compliance 데이터 유형은 필수입니다."})
            if not task.comp_owner_user:
                errors.append({"task_id": task.id, "field": "comp_owner_user", "message": "Compliance 소유자/사용자는 필수입니다."})
    return errors


@router.get("/pending")
def list_pending_approvals(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_approver_or_admin(user)
    query = (
        select(ApprovalRequest, ApprovalStep)
        .join(ApprovalStep, ApprovalStep.approval_request_id == ApprovalRequest.id)
        .where(ApprovalRequest.status == "PENDING")
        .where(ApprovalStep.status == "PENDING")
        .where(ApprovalStep.step_order == ApprovalRequest.current_step)
    )
    if user["role"] != "ADMIN":
        query = query.where(ApprovalStep.approver_employee_id == user["employee_id"])

    rows = []
    for request, step in db.execute(query).all():
        org = db.get(Organization, request.organization_id)
        requester = db.get(User, request.requested_by)
        task_count = db.scalar(
            select(func.count(TaskEntry.id)).where(
                TaskEntry.organization_id == request.organization_id
            )
        )
        rows.append(
            {
                "id": request.id,
                "organization_id": request.organization_id,
                "part_name": org.part_name if org else None,
                "requester": requester.name if requester else None,
                "task_count": task_count or 0,
                "requested_at": request.created_at.isoformat() if request.created_at else None,
                "current_step": request.current_step,
                "total_steps": request.total_steps,
                "status": request.status,
                "current_approver_employee_id": step.approver_employee_id,
                "current_approver_name": step.approver_name,
            }
        )
    return rows


def _current_step(db: Session, request: ApprovalRequest) -> ApprovalStep:
    step = db.scalar(
        select(ApprovalStep)
        .where(ApprovalStep.approval_request_id == request.id)
        .where(ApprovalStep.step_order == request.current_step)
    )
    if step is None:
        raise HTTPException(status_code=404, detail="Approval step not found")
    return step


def _ensure_can_act(user: dict, step: ApprovalStep) -> None:
    if user["role"] == "ADMIN":
        return
    if user["employee_id"] == step.approver_employee_id:
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def _request_tasks(db: Session, request: ApprovalRequest) -> list[TaskEntry]:
    return db.scalars(
        select(TaskEntry)
        .where(TaskEntry.organization_id == request.organization_id)
        .order_by(TaskEntry.id)
    ).all()


def _record_task_reviews(
    db: Session,
    request: ApprovalRequest,
    step: ApprovalStep,
    user: dict,
    reviews: list[ApprovalTaskReviewInput],
    action: str,
) -> None:
    if not reviews:
        return

    tasks = _request_tasks(db, request)
    task_ids = {task.id for task in tasks}
    reviews_by_task_id = {review.task_id: review for review in reviews}
    if set(reviews_by_task_id) != task_ids:
        raise HTTPException(status_code=400, detail="task_reviews must include every task")

    normalized = []
    for task in tasks:
        review = reviews_by_task_id[task.id]
        comment = (review.comment or "").strip() or None
        if action == "approve" and review.decision != "APPROVED":
            raise HTTPException(status_code=400, detail="All task reviews must be APPROVED")
        if review.decision == "REJECTED" and comment is None:
            raise HTTPException(status_code=400, detail="Rejected task review comment is required")
        normalized.append((task.id, review.decision, comment))

    if action == "reject" and not any(decision == "REJECTED" for _, decision, _ in normalized):
        raise HTTPException(status_code=400, detail="At least one task review must be REJECTED")

    db.execute(
        delete(ApprovalTaskReview).where(ApprovalTaskReview.approval_step_id == step.id)
    )
    for task_id, decision, comment in normalized:
        db.add(
            ApprovalTaskReview(
                approval_request_id=request.id,
                approval_step_id=step.id,
                task_entry_id=task_id,
                reviewer_employee_id=user["employee_id"],
                decision=decision,
                comment=comment,
            )
        )


@router.post("/{approval_id}/approve")
def approve_request(
    approval_id: int,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    payload: ApprovalActionRequest | None = None,
):
    request = db.get(ApprovalRequest, approval_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if request.status != "PENDING":
        raise HTTPException(status_code=400, detail="Approval request is not pending")

    step = _current_step(db, request)
    _ensure_can_act(user, step)
    _record_task_reviews(db, request, step, user, payload.task_reviews if payload else [], "approve")
    step.status = "APPROVED"
    step.acted_at = datetime.now(timezone.utc)

    if request.current_step >= request.total_steps:
        request.status = "APPROVED"
        for task in db.scalars(
            select(TaskEntry).where(TaskEntry.organization_id == request.organization_id)
        ).all():
            task.status = "APPROVED"
    else:
        request.current_step += 1

    db.commit()
    db.refresh(request)
    requester = db.get(User, request.requested_by)
    if request.status == "APPROVED":
        _notify(
            "최종 승인 완료",
            [employee_email(requester.employee_id if requester else None), employee_email("admin001")],
            f"승인 요청 {request.id}이 최종 승인되었습니다.",
        )
    else:
        next_step = _current_step(db, request)
        _notify(
            "다음 단계 승인 요청",
            [employee_email(next_step.approver_employee_id), employee_email("admin001")],
            f"승인 요청 {request.id}이 {request.current_step}단계로 이동했습니다.",
            action_url=_approval_detail_url(request.id),
        )
    return _serialize_request(db, request)


@router.get("/{approval_id}/history")
def read_approval_history(
    approval_id: int,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_approver_or_admin(user)
    request = db.get(ApprovalRequest, approval_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    steps = db.scalars(
        select(ApprovalStep).where(ApprovalStep.approval_request_id == approval_id)
    ).all()
    if user["role"] != "ADMIN" and user["employee_id"] not in {
        step.approver_employee_id for step in steps
    }:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return _serialize_request(db, request)


@router.post("/{approval_id}/reject")
def reject_request(
    approval_id: int,
    payload: RejectRequest,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    request = db.get(ApprovalRequest, approval_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if request.status != "PENDING":
        raise HTTPException(status_code=400, detail="Approval request is not pending")

    step = _current_step(db, request)
    _ensure_can_act(user, step)
    _record_task_reviews(db, request, step, user, payload.task_reviews, "reject")
    step.status = "REJECTED"
    step.reject_reason = payload.reject_reason
    step.acted_at = datetime.now(timezone.utc)
    request.status = "REJECTED"
    request.reject_reason = payload.reject_reason

    for task in db.scalars(
        select(TaskEntry).where(TaskEntry.organization_id == request.organization_id)
    ).all():
        task.status = "REJECTED"

    db.commit()
    db.refresh(request)
    requester = db.get(User, request.requested_by)
    _notify(
        "승인 반려",
        [employee_email(requester.employee_id if requester else None)],
        f"승인 요청 {request.id}이 반려되었습니다.\n사유: {payload.reject_reason}",
    )
    return _serialize_request(db, request)


@router.post("/{approval_id}/request-edit")
def request_edit_after_approval(
    approval_id: int,
    payload: EditRequest,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    request = db.get(ApprovalRequest, approval_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if request.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Approval request is not approved")
    requester = db.get(User, request.requested_by)
    if user["role"] != "ADMIN" and user["employee_id"] != (requester.employee_id if requester else None):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    request.status = "REJECTED"
    request.reject_reason = f"수정 요청: {payload.reason}"
    for task in db.scalars(
        select(TaskEntry).where(TaskEntry.organization_id == request.organization_id)
    ).all():
        task.status = "REJECTED"

    db.commit()
    db.refresh(request)
    _notify(
        "승인 완료 건 수정 요청",
        [employee_email(requester.employee_id if requester else None), employee_email("admin001")],
        f"승인 요청 {request.id}에 수정 요청이 등록되었습니다.\n사유: {payload.reason}",
    )
    return _serialize_request(db, request)


@router.post("/submit", status_code=status.HTTP_201_CREATED)
def submit_approval(
    org_id: int,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ensure_can_write_org(user, org_id)
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    tasks = db.scalars(select(TaskEntry).where(TaskEntry.organization_id == org_id)).all()
    if not tasks:
        raise HTTPException(status_code=400, detail="No tasks to submit")

    validation_errors = _submission_errors(tasks)
    if validation_errors:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Task validation failed",
                "validation_errors": validation_errors,
            },
        )

    requester = db.scalar(select(User).where(User.employee_id == user["employee_id"]))
    if requester is None:
        requester = User(
            employee_id=user["employee_id"],
            name=user["name"],
            role=user["role"],
            organization_id=user["organization_id"],
        )
        db.add(requester)
        db.flush()

    path = build_approval_path(
        {
            "org_type": org.org_type,
            "group_head_id": org.group_head_id,
            "team_head_id": org.team_head_id,
            "division_head_id": org.division_head_id,
        }
    )
    request = ApprovalRequest(
        organization_id=org_id,
        requested_by=requester.id,
        status="PENDING",
        current_step=1,
        total_steps=len(path),
    )
    db.add(request)
    db.flush()

    for index, approver_id in enumerate(path, start=1):
        approver_name, approver_role = _approver_info(org, approver_id)
        db.add(
            ApprovalStep(
                approval_request_id=request.id,
                step_order=index,
                approver_employee_id=approver_id,
                approver_name=approver_name,
                approver_role=approver_role,
                status="PENDING",
            )
        )

    for task in tasks:
        task.status = "SUBMITTED"

    db.commit()
    db.refresh(request)
    _notify(
        "승인 요청 제출",
        [employee_email(path[0])],
        f"{org.part_name} 승인 요청 {request.id}이 제출되었습니다.",
        action_url=_approval_detail_url(request.id),
    )
    return _serialize_request(db, request)
