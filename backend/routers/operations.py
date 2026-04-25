from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, require_admin
from backend.models import AuditLog
from backend.services.audit import log_audit, serialize_audit_log
from backend.services.collection import setting_row

router = APIRouter(prefix="/admin", tags=["admin-operations"])


class CollectionStatusUpdate(BaseModel):
    collection_locked: bool
    lock_reason: str | None = None


def _latest_export(db: Session) -> dict | None:
    log = db.scalar(
        select(AuditLog)
        .where(AuditLog.action == "EXPORT_FINAL")
        .where(AuditLog.status == "SUCCESS")
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(1)
    )
    if log is None:
        return None
    return {
        "employee_id": log.employee_id,
        "filename": log.message,
        "exported_at": log.created_at.isoformat() if log.created_at else None,
    }


def _recent_mail_failures(db: Session) -> list[dict]:
    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.action == "EMAIL_SEND")
        .where(AuditLog.status == "FAILED")
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(5)
    ).all()
    return [serialize_audit_log(log) for log in logs]


def _serialize_collection_status(db: Session) -> dict:
    setting = setting_row(db)
    return {
        "collection_locked": bool(setting.collection_locked),
        "lock_reason": setting.collection_lock_reason,
        "locked_at": setting.collection_locked_at.isoformat() if setting.collection_locked_at else None,
        "last_export": _latest_export(db),
        "mail_failures": _recent_mail_failures(db),
    }


@router.get("/collection/status")
def read_collection_status(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin(user)
    return _serialize_collection_status(db)


@router.put("/collection/status")
def update_collection_status(
    payload: CollectionStatusUpdate,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin(user)
    setting = setting_row(db)
    setting.collection_locked = payload.collection_locked
    setting.collection_lock_reason = (payload.lock_reason or "").strip() or None
    setting.collection_locked_at = datetime.now(timezone.utc) if payload.collection_locked else None
    log_audit(
        db,
        action="COLLECTION_LOCK" if payload.collection_locked else "COLLECTION_REOPEN",
        user=user,
        target_type="SystemSetting",
        target_id=setting.id,
        message=setting.collection_lock_reason,
    )
    db.commit()
    return _serialize_collection_status(db)


@router.get("/audit-logs")
def list_audit_logs(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    action: str | None = None,
    status: str | None = None,
    limit: int = 50,
):
    require_admin(user)
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if status:
        query = query.where(AuditLog.status == status)
    logs = db.scalars(
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(min(max(limit, 1), 100))
    ).all()
    return {"items": [serialize_audit_log(log) for log in logs]}
