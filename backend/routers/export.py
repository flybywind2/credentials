from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, require_admin
from backend.models import Organization, TaskEntry
from backend.services.excel import EXCEL_MIME_TYPE, write_workbook

router = APIRouter(prefix="/export", tags=["export"])


def _yes_no(value: bool, positive: str = "해당", negative: str = "비해당") -> str:
    return positive if value else negative


@router.get("/excel")
def export_tasks_excel(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    division: str | None = None,
    team: str | None = None,
    group: str | None = None,
    part: str | None = None,
    status: str | None = None,
    is_confidential: bool | None = None,
    is_national_tech: bool | None = None,
    is_compliance: bool | None = None,
):
    require_admin(user)
    query = select(TaskEntry, Organization).join(
        Organization, Organization.id == TaskEntry.organization_id
    )
    if division:
        query = query.where(Organization.division_name.contains(division))
    if team:
        query = query.where(Organization.team_name.contains(team))
    if group:
        query = query.where(Organization.group_name.contains(group))
    if part:
        query = query.where(Organization.part_name.contains(part))
    if status:
        query = query.where(TaskEntry.status == status)
    if is_confidential is not None:
        query = query.where(TaskEntry.is_confidential.is_(is_confidential))
    if is_national_tech is not None:
        query = query.where(TaskEntry.is_national_tech.is_(is_national_tech))
    if is_compliance is not None:
        query = query.where(TaskEntry.is_compliance.is_(is_compliance))

    rows = [
        [
            "실",
            "팀",
            "그룹",
            "파트",
            "소파트",
            "대업무",
            "세부업무",
            "기밀",
            "국가핵심기술",
            "Compliance",
            "상태",
        ]
    ]
    for task, org in db.execute(query.order_by(Organization.id, TaskEntry.id)).all():
        rows.append(
            [
                org.division_name,
                org.team_name or "",
                org.group_name or "",
                org.part_name,
                task.sub_part or "",
                task.major_task,
                task.detail_task,
                _yes_no(task.is_confidential, "기밀", "비기밀"),
                _yes_no(task.is_national_tech),
                _yes_no(task.is_compliance),
                task.status,
            ]
        )
    return Response(
        content=write_workbook(rows, sheet_name="TaskExport"),
        media_type=EXCEL_MIME_TYPE,
        headers={"Content-Disposition": 'attachment; filename="tasks-export.xlsx"'},
    )
