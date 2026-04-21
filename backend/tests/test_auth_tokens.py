from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from backend.services.auth_tokens import create_access_token, verify_access_token


USER = {
    "employee_id": "part001",
    "name": "최파트장",
    "email": "part001@samsung.com",
    "role": "INPUTTER",
    "organization_id": 1,
}


def test_access_token_round_trips_user_payload():
    token = create_access_token(USER, secret="test-secret", now=datetime(2026, 4, 22, tzinfo=timezone.utc))

    payload = verify_access_token(token, secret="test-secret", now=datetime(2026, 4, 22, tzinfo=timezone.utc))

    assert payload["employee_id"] == "part001"
    assert payload["role"] == "INPUTTER"


def test_access_token_rejects_tampering():
    token = create_access_token(USER, secret="test-secret", now=datetime(2026, 4, 22, tzinfo=timezone.utc))
    tampered = f"{token[:-1]}x"

    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(tampered, secret="test-secret", now=datetime(2026, 4, 22, tzinfo=timezone.utc))

    assert exc_info.value.status_code == 401


def test_access_token_rejects_expired_tokens():
    issued_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    token = create_access_token(USER, secret="test-secret", now=issued_at, expires_delta=timedelta(seconds=1))

    with pytest.raises(HTTPException) as exc_info:
        verify_access_token(token, secret="test-secret", now=issued_at + timedelta(seconds=2))

    assert exc_info.value.status_code == 401
