from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import SystemSetting


LOCKED_MESSAGE = "취합이 종료되어 입력/수정/삭제/승인 요청할 수 없습니다."


def setting_row(db: Session) -> SystemSetting:
    setting = db.scalar(select(SystemSetting).order_by(SystemSetting.id).limit(1))
    if setting is None:
        setting = SystemSetting()
        db.add(setting)
        db.flush()
    return setting


def ensure_collection_open(db: Session) -> None:
    setting = setting_row(db)
    if setting.collection_locked:
        raise HTTPException(status_code=423, detail=LOCKED_MESSAGE)
