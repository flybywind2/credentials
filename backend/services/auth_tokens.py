import base64
import binascii
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException

from backend.config import settings

ALGORITHM = "HS256"
DEFAULT_TOKEN_SECRET = "credential-dev-token-secret"


def _now_utc(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _token_secret(secret: str | None = None) -> str:
    return secret or settings.sso_token_secret or settings.sso_client_secret or DEFAULT_TOKEN_SECRET


def _encode_json(value: dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode_json(value: str) -> dict[str, Any]:
    padded = value + ("=" * (-len(value) % 4))
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        decoded = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Invalid access token") from None
    if not isinstance(decoded, dict):
        raise HTTPException(status_code=401, detail="Invalid access token")
    return decoded


def _signature(message: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), message.encode("ascii"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def create_access_token(
    user: dict[str, Any],
    *,
    secret: str | None = None,
    now: datetime | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    issued_at = _now_utc(now)
    ttl = expires_delta or timedelta(minutes=settings.sso_token_expire_minutes)
    payload = {
        **user,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + ttl).timestamp()),
    }
    header = {"alg": ALGORITHM, "typ": "JWT"}
    encoded_header = _encode_json(header)
    encoded_payload = _encode_json(payload)
    signed_content = f"{encoded_header}.{encoded_payload}"
    signed_secret = _token_secret(secret)
    return f"{signed_content}.{_signature(signed_content, signed_secret)}"


def verify_access_token(
    token: str,
    *,
    secret: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid access token")
    encoded_header, encoded_payload, supplied_signature = parts
    signed_content = f"{encoded_header}.{encoded_payload}"
    expected_signature = _signature(signed_content, _token_secret(secret))
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid access token")

    header = _decode_json(encoded_header)
    if header.get("alg") != ALGORITHM:
        raise HTTPException(status_code=401, detail="Invalid access token")

    payload = _decode_json(encoded_payload)
    exp = payload.get("exp")
    if not isinstance(exp, int | float):
        raise HTTPException(status_code=401, detail="Invalid access token")
    if _now_utc(now).timestamp() > exp:
        raise HTTPException(status_code=401, detail="Access token expired")
    return payload
