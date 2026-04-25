from sqlalchemy.orm import Session

from backend.models import AuditLog


def log_audit(
    db: Session,
    *,
    action: str,
    user: dict | None = None,
    employee_id: str | None = None,
    role: str | None = None,
    target_type: str | None = None,
    target_id: str | int | None = None,
    status: str = "SUCCESS",
    message: str | None = None,
) -> AuditLog:
    log = AuditLog(
        action=action,
        employee_id=(user or {}).get("employee_id") or employee_id,
        role=(user or {}).get("role") or role,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        status=status,
        message=message,
    )
    db.add(log)
    return log


def serialize_audit_log(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "action": log.action,
        "employee_id": log.employee_id,
        "role": log.role,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "status": log.status,
        "message": log.message,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
