import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import ApprovalRequest, ApprovalStep, Organization, TaskEntry, User


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_organization_rejects_unknown_org_type(db_session):
    db_session.add(
        Organization(
            division_name="실",
            division_head_name="실장",
            division_head_id="d1",
            part_name="파트",
            part_head_name="파트장",
            part_head_id="p1",
            org_type="UNKNOWN",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_rejects_unknown_role(db_session):
    db_session.add(User(employee_id="u1", name="사용자", role="UNKNOWN"))

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_task_rejects_unknown_status(db_session):
    org = Organization(
        division_name="실",
        division_head_name="실장",
        division_head_id="d1",
        part_name="파트",
        part_head_name="파트장",
        part_head_id="p1",
        org_type="NORMAL",
    )
    user = User(employee_id="u1", name="사용자", role="INPUTTER")
    db_session.add_all([org, user])
    db_session.flush()

    db_session.add(
        TaskEntry(
            organization_id=org.id,
            created_by=user.id,
            major_task="대업무",
            detail_task="세부업무",
            status="UNKNOWN",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_task_accepts_uploaded_status(db_session):
    org = Organization(
        division_name="실",
        division_head_name="실장",
        division_head_id="d1",
        part_name="파트",
        part_head_name="파트장",
        part_head_id="p1",
        org_type="NORMAL",
    )
    user = User(employee_id="u1", name="사용자", role="INPUTTER")
    db_session.add_all([org, user])
    db_session.flush()

    db_session.add(
        TaskEntry(
            organization_id=org.id,
            created_by=user.id,
            major_task="대업무",
            detail_task="세부업무",
            status="UPLOADED",
        )
    )

    db_session.commit()


def test_approval_request_rejects_invalid_step_count(db_session):
    org = Organization(
        division_name="실",
        division_head_name="실장",
        division_head_id="d1",
        part_name="파트",
        part_head_name="파트장",
        part_head_id="p1",
        org_type="DIV_DIRECT",
    )
    user = User(employee_id="u1", name="사용자", role="INPUTTER")
    db_session.add_all([org, user])
    db_session.flush()

    db_session.add(
        ApprovalRequest(
            organization_id=org.id,
            requested_by=user.id,
            status="PENDING",
            current_step=0,
            total_steps=0,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_approval_request_and_step_accept_cancelled_status(db_session):
    org = Organization(
        division_name="취소실",
        division_head_name="취소실장",
        division_head_id="cancel-d1",
        part_name="취소파트",
        part_head_name="취소파트장",
        part_head_id="cancel-p1",
        org_type="DIV_DIRECT",
    )
    user = User(employee_id="cancel-u1", name="취소사용자", role="INPUTTER")
    db_session.add_all([org, user])
    db_session.flush()
    request = ApprovalRequest(
        organization_id=org.id,
        requested_by=user.id,
        status="CANCELLED",
        current_step=1,
        total_steps=1,
    )
    db_session.add(request)
    db_session.flush()
    db_session.add(
        ApprovalStep(
            approval_request_id=request.id,
            step_order=1,
            approver_employee_id="cancel-d1",
            approver_name="취소실장",
            approver_role="실장",
            status="CANCELLED",
        )
    )

    db_session.commit()
