from typing import Annotated, TypeAlias

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, require_admin
from backend.models import ConfidentialQuestion, NationalTechQuestion

router = APIRouter(prefix="/questions", tags=["questions"])
admin_router = APIRouter(prefix="/admin/questions", tags=["admin-questions"])
QuestionModel: TypeAlias = ConfidentialQuestion | NationalTechQuestion


class QuestionCreate(BaseModel):
    question_text: str
    options: list[str]
    sort_order: int = 0


class QuestionReorder(BaseModel):
    question_ids: list[int]


def _with_none_option(options: list[str]) -> list[str]:
    cleaned = [option for option in options if option and option != "해당 없음"]
    return ["해당 없음", *cleaned]


def _serialize(question: QuestionModel) -> dict:
    return {
        "id": question.id,
        "question_text": question.question_text,
        "options": question.options,
        "is_active": question.is_active,
        "sort_order": question.sort_order,
    }


def _list_questions(db: Session, model: type[QuestionModel]) -> list[dict]:
    query = select(model).where(model.is_active.is_(True)).order_by(model.sort_order, model.id)
    return [_serialize(question) for question in db.scalars(query).all()]


def _create_question(db: Session, model: type[QuestionModel], payload: QuestionCreate) -> dict:
    question = model(
        question_text=payload.question_text,
        options=_with_none_option(payload.options),
        sort_order=payload.sort_order,
        is_active=True,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return _serialize(question)


def _delete_question(db: Session, model: type[QuestionModel], question_id: int) -> Response:
    question = db.get(model, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(question)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _reorder_questions(db: Session, model: type[QuestionModel], payload: QuestionReorder) -> list[dict]:
    questions = {
        question.id: question
        for question in db.scalars(select(model).where(model.id.in_(payload.question_ids))).all()
    }
    if set(questions) != set(payload.question_ids):
        raise HTTPException(status_code=404, detail="Question not found")
    for index, question_id in enumerate(payload.question_ids, start=1):
        questions[question_id].sort_order = index
    db.commit()
    return _list_questions(db, model)


@router.get("")
def list_questions(db: Annotated[Session, Depends(get_db)]):
    return {
        "confidential": _list_questions(db, ConfidentialQuestion),
        "national_tech": _list_questions(db, NationalTechQuestion),
    }


@router.get("/confidential")
def list_confidential_questions(db: Annotated[Session, Depends(get_db)]):
    return _list_questions(db, ConfidentialQuestion)


@router.get("/national-tech")
def list_national_tech_questions(db: Annotated[Session, Depends(get_db)]):
    return _list_questions(db, NationalTechQuestion)


@admin_router.post("/confidential", status_code=status.HTTP_201_CREATED)
def create_confidential_question(
    payload: QuestionCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    return _create_question(db, ConfidentialQuestion, payload)


@admin_router.delete("/confidential/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_confidential_question(
    question_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    return _delete_question(db, ConfidentialQuestion, question_id)


@admin_router.put("/confidential/reorder")
def reorder_confidential_questions(
    payload: QuestionReorder,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    return _reorder_questions(db, ConfidentialQuestion, payload)


@admin_router.post("/national-tech", status_code=status.HTTP_201_CREATED)
def create_national_tech_question(
    payload: QuestionCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    return _create_question(db, NationalTechQuestion, payload)


@admin_router.delete("/national-tech/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_national_tech_question(
    question_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    return _delete_question(db, NationalTechQuestion, question_id)


@admin_router.put("/national-tech/reorder")
def reorder_national_tech_questions(
    payload: QuestionReorder,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    require_admin(user)
    return _reorder_questions(db, NationalTechQuestion, payload)
