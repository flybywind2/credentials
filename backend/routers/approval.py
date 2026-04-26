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
from backend.routers.organization import _scoped_organization_query
from backend.services.audit import log_audit
from backend.services.approval_flow import build_approval_path
from backend.services.collection import ensure_collection_open
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


TASK_STATUSES = ("UPLOADED", "DRAFT", "SUBMITTED", "APPROVED", "REJECTED")
APPROVAL_STATUS_LABELS = {
    "NOT_REQUESTED": "미요청",
    "PENDING": "승인대기",
    "APPROVED": "승인완료",
    "REJECTED": "반려",
    "CANCELLED": "요청취소",
}
UNIT_TYPE_LABELS = {
    "PART": "파트",
    "GROUP": "그룹",
    "TEAM": "팀",
}


def _approval_detail_url(approval_id: int) -> str:
    return f"{settings.app_base_url.rstrip('/')}/approver/approvals/{approval_id}"


def _notify(
    subject: str,
    recipients: list[str | None],
    body: str,
    action_url: str | None = None,
    action_label: str = "승인 검토 바로가기",
    db: Session | None = None,
    user: dict | None = None,
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
    except Exception as exc:
        logger.exception("email notification failed subject=%s", subject)
        if db is not None:
            try:
                log_audit(
                    db,
                    action="EMAIL_SEND",
                    user=user,
                    target_type="Email",
                    status="FAILED",
                    message=f"{subject}: {exc}",
                )
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("email failure audit log failed subject=%s", subject)


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


def _unit_for_status(user: dict, org: Organization) -> tuple[str, str, str]:
    current_org = user.get("organization") or {}
    employee_id = user["employee_id"]
    if user["role"] == "ADMIN":
        return "PART", f"part:{org.id}", org.part_name
    if current_org.get("group_head_id") == employee_id:
        return "PART", f"part:{org.id}", org.part_name
    if current_org.get("team_head_id") == employee_id:
        if org.group_name:
            return "GROUP", f"group:{org.team_name}:{org.group_name}", org.group_name
        return "PART", f"part:{org.id}", org.part_name
    if current_org.get("division_head_id") == employee_id:
        if org.team_name:
            return "TEAM", f"team:{org.division_name}:{org.team_name}", org.team_name
        return "PART", f"part:{org.id}", org.part_name
    if user.get("managed"):
        return "PART", f"part:{org.id}", org.part_name
    return "PART", f"part:{org.id}", org.part_name


def _scope_label_for_status(user: dict) -> str:
    current_org = user.get("organization") or {}
    employee_id = user["employee_id"]
    if user["role"] == "ADMIN":
        return "전체현황"
    if current_org.get("group_head_id") == employee_id:
        return "파트현황"
    if current_org.get("team_head_id") == employee_id:
        return "그룹현황"
    if current_org.get("division_head_id") == employee_id:
        return "실현황"
    if user.get("managed"):
        return "파트현황"
    return "하위 조직 현황"


def _latest_requests_by_org(db: Session, organization_ids: list[int]) -> dict[int, ApprovalRequest]:
    if not organization_ids:
        return {}
    latest_by_org = {}
    requests = db.scalars(
        select(ApprovalRequest)
        .where(ApprovalRequest.organization_id.in_(organization_ids))
        .order_by(ApprovalRequest.created_at.desc(), ApprovalRequest.id.desc())
    ).all()
    for request in requests:
        latest_by_org.setdefault(request.organization_id, request)
    return latest_by_org


def _task_counts_by_org(db: Session, organization_ids: list[int]) -> dict[int, dict[str, int]]:
    counts = {
        org_id: {status_name: 0 for status_name in TASK_STATUSES}
        for org_id in organization_ids
    }
    if not organization_ids:
        return counts
    rows = db.execute(
        select(TaskEntry.organization_id, TaskEntry.status, func.count(TaskEntry.id))
        .where(TaskEntry.organization_id.in_(organization_ids))
        .group_by(TaskEntry.organization_id, TaskEntry.status)
    ).all()
    for org_id, status_name, count in rows:
        counts.setdefault(org_id, {status: 0 for status in TASK_STATUSES})[status_name] = count
    return counts


def _approval_summary_for_requests(requests: list[ApprovalRequest]) -> dict:
    status_counts = {"PENDING": 0, "APPROVED": 0, "REJECTED": 0, "CANCELLED": 0}
    for request in requests:
        if request.status in status_counts:
            status_counts[request.status] += 1
    if status_counts["PENDING"]:
        status = "PENDING"
    elif status_counts["REJECTED"]:
        status = "REJECTED"
    elif status_counts["APPROVED"]:
        status = "APPROVED"
    elif status_counts["CANCELLED"]:
        status = "CANCELLED"
    else:
        status = "NOT_REQUESTED"
    latest = max(
        requests,
        key=lambda request: (request.created_at or datetime.min.replace(tzinfo=timezone.utc), request.id),
        default=None,
    )
    return {
        "approval_status": status,
        "approval_status_label": APPROVAL_STATUS_LABELS[status],
        "pending_count": status_counts["PENDING"],
        "approved_count": status_counts["APPROVED"],
        "rejected_count": status_counts["REJECTED"],
        "cancelled_count": status_counts["CANCELLED"],
        "latest_requested_at": latest.created_at.isoformat() if latest and latest.created_at else None,
        "current_step": latest.current_step if latest else None,
        "total_steps": latest.total_steps if latest else None,
    }


def _same_scope_values(scope_id: str | None, scope_name: str | None, org_id: str | None, org_name: str | None) -> bool:
    if scope_id and scope_name:
        return org_id == scope_id and org_name == scope_name
    if scope_id:
        return org_id == scope_id
    return bool(scope_name and org_name == scope_name)


def _approval_role_for_user(user: dict) -> str | None:
    current_org = user.get("organization") or {}
    employee_id = user["employee_id"]
    if current_org.get("group_head_id") == employee_id:
        return "그룹장"
    if current_org.get("team_head_id") == employee_id:
        return "팀장"
    if current_org.get("division_head_id") == employee_id:
        return "실장"
    if user.get("managed"):
        return "그룹장"
    return None


def _matches_step_scope(user: dict, org: Organization | None, step: ApprovalStep) -> bool:
    if org is None:
        return False
    current_org = user.get("organization") or {}
    role = _approval_role_for_user(user)
    if role != step.approver_role:
        return False
    if role == "그룹장":
        return _same_scope_values(
            current_org.get("group_head_id"),
            current_org.get("group_name"),
            org.group_head_id,
            org.group_name,
        )
    if role == "팀장":
        return _same_scope_values(
            current_org.get("team_head_id"),
            current_org.get("team_name"),
            org.team_head_id,
            org.team_name,
        )
    if role == "실장":
        return _same_scope_values(
            current_org.get("division_head_id"),
            current_org.get("division_name"),
            org.division_head_id,
            org.division_name,
        )
    return False


def _can_act_on_step(user: dict, request: ApprovalRequest, step: ApprovalStep, db: Session) -> bool:
    if user["role"] == "ADMIN":
        return True
    if user["employee_id"] == step.approver_employee_id:
        return True
    if user["role"] != "APPROVER":
        return False
    return _matches_step_scope(user, db.get(Organization, request.organization_id), step)


def _submission_errors(tasks: list[TaskEntry]) -> list[dict]:
    errors = []
    for task in tasks:
        if task.status == "UPLOADED":
            errors.append(
                {
                    "task_id": task.id,
                    "field": "status",
                    "message": "Excel/붙여넣기 업로드 행은 웹에서 분류 저장 후 승인 요청할 수 있습니다.",
                }
            )
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

    rows = []
    for request, step in db.execute(query).all():
        if not _can_act_on_step(user, request, step, db):
            continue
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


@router.get("/subordinate-status")
def read_subordinate_approval_status(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_approver_or_admin(user)
    organizations = db.scalars(_scoped_organization_query(user).order_by(Organization.id)).all()
    organization_ids = [org.id for org in organizations]
    task_counts_by_org = _task_counts_by_org(db, organization_ids)
    latest_requests = _latest_requests_by_org(db, organization_ids)
    rows_by_key: dict[str, dict] = {}

    for org in organizations:
        unit_type, key, display_name = _unit_for_status(user, org)
        row = rows_by_key.setdefault(
            key,
            {
                "key": key,
                "unit_type": unit_type,
                "unit_type_label": UNIT_TYPE_LABELS[unit_type],
                "display_name": display_name,
                "division_name": org.division_name,
                "team_name": org.team_name,
                "group_name": org.group_name,
                "part_name": org.part_name if unit_type == "PART" else None,
                "organization_ids": [],
                "organization_count": 0,
                "task_count": 0,
                "status_counts": {status_name: 0 for status_name in TASK_STATUSES},
                "_approval_requests": [],
            },
        )
        row["organization_ids"].append(org.id)
        row["organization_count"] += 1
        org_counts = task_counts_by_org.get(org.id, {})
        for status_name in TASK_STATUSES:
            count = org_counts.get(status_name, 0)
            row["status_counts"][status_name] += count
            row["task_count"] += count
        latest_request = latest_requests.get(org.id)
        if latest_request is not None:
            row["_approval_requests"].append(latest_request)

    rows = []
    for row in rows_by_key.values():
        approval_summary = _approval_summary_for_requests(row.pop("_approval_requests"))
        row.update(approval_summary)
        rows.append(row)

    return {
        "scope_label": _scope_label_for_status(user),
        "rows": rows,
    }


def _current_step(db: Session, request: ApprovalRequest) -> ApprovalStep:
    step = db.scalar(
        select(ApprovalStep)
        .where(ApprovalStep.approval_request_id == request.id)
        .where(ApprovalStep.step_order == request.current_step)
    )
    if step is None:
        raise HTTPException(status_code=404, detail="Approval step not found")
    return step


def _ensure_can_act(user: dict, request: ApprovalRequest, step: ApprovalStep, db: Session) -> None:
    if _can_act_on_step(user, request, step, db):
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def _can_view_approval_history(
    user: dict,
    request: ApprovalRequest,
    steps: list[ApprovalStep],
    db: Session,
) -> bool:
    return any(_can_act_on_step(user, request, step, db) for step in steps)


def _ensure_can_cancel(user: dict, request: ApprovalRequest, db: Session) -> None:
    if user["role"] == "ADMIN":
        return
    requester = db.get(User, request.requested_by)
    if requester and requester.employee_id == user["employee_id"]:
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def _approval_has_started(db: Session, request: ApprovalRequest) -> bool:
    return db.scalar(
        select(func.count(ApprovalStep.id))
        .where(ApprovalStep.approval_request_id == request.id)
        .where(
            (ApprovalStep.status != "PENDING")
            | (ApprovalStep.acted_at.is_not(None))
        )
    ) > 0


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
    _ensure_can_act(user, request, step, db)
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

    log_audit(
        db,
        action="APPROVAL_APPROVE",
        user=user,
        target_type="ApprovalRequest",
        target_id=request.id,
    )
    db.commit()
    db.refresh(request)
    requester = db.get(User, request.requested_by)
    if request.status == "APPROVED":
        _notify(
            "최종 승인 완료",
            [employee_email(requester.employee_id if requester else None), employee_email("admin001")],
            f"승인 요청 {request.id}이 최종 승인되었습니다.",
            db=db,
            user=user,
        )
    else:
        next_step = _current_step(db, request)
        _notify(
            "다음 단계 승인 요청",
            [employee_email(next_step.approver_employee_id), employee_email("admin001")],
            f"승인 요청 {request.id}이 {request.current_step}단계로 이동했습니다.",
            action_url=_approval_detail_url(request.id),
            db=db,
            user=user,
        )
    return _serialize_request(db, request)


@router.post("/{approval_id}/cancel")
def cancel_request(
    approval_id: int,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    request = db.get(ApprovalRequest, approval_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if request.status != "PENDING":
        raise HTTPException(status_code=400, detail="Approval request is not pending")
    _ensure_can_cancel(user, request, db)
    if _approval_has_started(db, request):
        raise HTTPException(status_code=400, detail="Approval request is already in review")

    request.status = "CANCELLED"
    for step in db.scalars(
        select(ApprovalStep).where(ApprovalStep.approval_request_id == request.id)
    ).all():
        step.status = "CANCELLED"
        step.acted_at = datetime.now(timezone.utc)
    for task in db.scalars(
        select(TaskEntry).where(TaskEntry.organization_id == request.organization_id)
    ).all():
        if task.status == "SUBMITTED":
            task.status = "DRAFT"

    log_audit(
        db,
        action="APPROVAL_CANCEL",
        user=user,
        target_type="ApprovalRequest",
        target_id=request.id,
    )
    db.commit()
    db.refresh(request)
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
    if not _can_view_approval_history(user, request, steps, db):
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
    _ensure_can_act(user, request, step, db)
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

    log_audit(
        db,
        action="APPROVAL_REJECT",
        user=user,
        target_type="ApprovalRequest",
        target_id=request.id,
        message=payload.reject_reason,
    )
    db.commit()
    db.refresh(request)
    requester = db.get(User, request.requested_by)
    _notify(
        "승인 반려",
        [employee_email(requester.employee_id if requester else None)],
        f"승인 요청 {request.id}이 반려되었습니다.\n사유: {payload.reject_reason}",
        db=db,
        user=user,
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

    log_audit(
        db,
        action="APPROVAL_EDIT_REQUEST",
        user=user,
        target_type="ApprovalRequest",
        target_id=request.id,
        message=payload.reason,
    )
    db.commit()
    db.refresh(request)
    _notify(
        "승인 완료 건 수정 요청",
        [employee_email(requester.employee_id if requester else None), employee_email("admin001")],
        f"승인 요청 {request.id}에 수정 요청이 등록되었습니다.\n사유: {payload.reason}",
        db=db,
        user=user,
    )
    return _serialize_request(db, request)


@router.post("/submit", status_code=status.HTTP_201_CREATED)
def submit_approval(
    org_id: int,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    ensure_collection_open(db)
    ensure_can_write_org(user, org_id, db)
    org = db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    tasks = db.scalars(select(TaskEntry).where(TaskEntry.organization_id == org_id)).all()
    if not tasks:
        raise HTTPException(status_code=400, detail="No tasks to submit")
    if any(task.status == "SUBMITTED" for task in tasks):
        active_request = db.scalar(
            select(ApprovalRequest)
            .where(ApprovalRequest.organization_id == org_id)
            .where(ApprovalRequest.status.in_(("PENDING", "IN_PROGRESS")))
            .order_by(ApprovalRequest.created_at.desc(), ApprovalRequest.id.desc())
            .limit(1)
        )
        if active_request is not None:
            raise HTTPException(status_code=400, detail="Pending approval request already exists")

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

    log_audit(
        db,
        action="APPROVAL_SUBMIT",
        user=user,
        target_type="ApprovalRequest",
        target_id=request.id,
    )
    db.commit()
    db.refresh(request)
    _notify(
        "승인 요청 제출",
        [employee_email(path[0])],
        f"{org.part_name} 승인 요청 {request.id}이 제출되었습니다.",
        action_url=_approval_detail_url(request.id),
        db=db,
        user=user,
    )
    return _serialize_request(db, request)
