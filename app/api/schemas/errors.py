from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class ErrorDetail(BaseModel):
    code: str = Field(..., description="UPPER_SNAKE_CASE machine-readable error code", example="INVALID_INPUT")
    message: str = Field(..., description="Readable human-friendly error explanation", example="Script or audio must be provided.")
    retryable: bool = Field(default=False, description="Whether the client can retry the request safely")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured contextual diagnostics")


class ErrorResponse(BaseModel):
    error: ErrorDetail
