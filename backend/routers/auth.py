from pydantic import BaseModel
from fastapi import APIRouter, Header

from backend.services.sso import authenticate_employee

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    employee_id: str


def _require_mock_user(employee_id: str) -> dict:
    return authenticate_employee(employee_id)


@router.post("/login")
def login(request: LoginRequest):
    user = _require_mock_user(request.employee_id)
    return {
        "access_token": f"mock-token-{request.employee_id}",
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me")
def read_current_user(x_employee_id: str = Header(default="admin001")):
    return _require_mock_user(x_employee_id)
