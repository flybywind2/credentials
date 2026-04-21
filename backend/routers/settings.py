from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, require_admin
from backend.models import ColumnTooltip, SystemSetting

router = APIRouter(tags=["settings"])
admin_router = APIRouter(prefix="/admin", tags=["admin-settings"])


COLUMN_DEFINITIONS = [
    ("sub_part", "소파트"),
    ("major_task", "대업무"),
    ("detail_task", "세부업무"),
    ("confidential", "기밀"),
    ("national_tech", "국가핵심기술"),
    ("compliance", "Compliance"),
    ("storage_location", "보관 장소"),
    ("related_menu", "관련 메뉴"),
    ("share_scope", "공유 범위"),
]


class TooltipUpdate(BaseModel):
    example_text: str


class DeadlineUpdate(BaseModel):
    input_deadline: date | None = None
    description: str | None = None


def _tooltip_map(db: Session) -> dict[str, ColumnTooltip]:
    return {
        tooltip.column_key: tooltip
        for tooltip in db.scalars(select(ColumnTooltip)).all()
    }


def _list_tooltips(db: Session) -> list[dict]:
    saved = _tooltip_map(db)
    return [
        {
            "column_key": key,
            "label": label,
            "example_text": saved[key].example_text if key in saved else "",
        }
        for key, label in COLUMN_DEFINITIONS
    ]


@router.get("/tooltips")
def list_public_tooltips(db: Annotated[Session, Depends(get_db)]):
    return _list_tooltips(db)


@admin_router.get("/tooltips")
def list_admin_tooltips(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    return _list_tooltips(db)


@admin_router.put("/tooltips/{column_key}")
def update_tooltip(
    column_key: str,
    payload: TooltipUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    tooltip = db.scalar(select(ColumnTooltip).where(ColumnTooltip.column_key == column_key))
    if tooltip is None:
        tooltip = ColumnTooltip(column_key=column_key, example_text=payload.example_text)
        db.add(tooltip)
    else:
        tooltip.example_text = payload.example_text
    db.commit()
    db.refresh(tooltip)
    label = dict(COLUMN_DEFINITIONS).get(column_key, column_key)
    return {
        "column_key": tooltip.column_key,
        "label": label,
        "example_text": tooltip.example_text,
    }


def _setting_row(db: Session) -> SystemSetting:
    setting = db.scalar(select(SystemSetting).order_by(SystemSetting.id).limit(1))
    if setting is None:
        setting = SystemSetting()
        db.add(setting)
        db.flush()
    return setting


def _serialize_deadline(setting: SystemSetting) -> dict:
    today = date.today()
    if setting.input_deadline is None:
        return {
            "input_deadline": None,
            "description": setting.description,
            "today": today.isoformat(),
            "d_day": None,
            "is_closed": False,
        }
    d_day = (setting.input_deadline - today).days
    return {
        "input_deadline": setting.input_deadline.isoformat(),
        "description": setting.description,
        "today": today.isoformat(),
        "d_day": d_day,
        "is_closed": d_day < 0,
    }


@router.get("/settings/deadline")
def read_public_deadline(db: Annotated[Session, Depends(get_db)]):
    return _serialize_deadline(_setting_row(db))


@admin_router.get("/settings/deadline")
def read_admin_deadline(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    return _serialize_deadline(_setting_row(db))


@admin_router.put("/settings/deadline")
def update_deadline(
    payload: DeadlineUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    setting = _setting_row(db)
    setting.input_deadline = payload.input_deadline
    setting.description = payload.description
    db.commit()
    db.refresh(setting)
    return _serialize_deadline(setting)
