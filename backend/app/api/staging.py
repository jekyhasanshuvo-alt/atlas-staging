"""Operator-only mail retrieval. Deliberately excluded from the browser proxy."""

import hmac
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/v1/staging-mail", include_in_schema=False)


class SyntheticMailRequest(BaseModel):
    email: EmailStr
    kind: Literal["verification", "reset"] = "verification"


@router.post("/consume")
def consume_mail(data: SyntheticMailRequest, request: Request):
    settings = request.app.state.settings
    supplied = request.headers.get("X-Atlas-Mailbox-Key", "")
    if not hmac.compare_digest(
        supplied.encode(), settings.staging_mailbox_key.get_secret_value().encode()
    ):
        raise HTTPException(403, "Operator authorization required.")
    if data.email not in settings.staging_synthetic_emails:
        raise HTTPException(403, "Synthetic recipient required.")
    link = request.app.state.staging_mailbox.consume(str(data.email), data.kind)
    if link is None:
        raise HTTPException(
            404, "No unconsumed synthetic message. Request another link if the service restarted."
        )
    return {"link": link, "retention_seconds": 600}
