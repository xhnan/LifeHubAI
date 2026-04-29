from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthAgentRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User health request")
    user_id: str = Field(default="local-user", min_length=1, description="Caller user id")


class HealthAgentResponse(BaseModel):
    state: dict[str, Any]
    summary: dict[str, Any]
    record_payload: dict[str, Any]
