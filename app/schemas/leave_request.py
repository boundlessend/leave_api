from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class LeaveRequestCreate(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_date_range(self) -> "LeaveRequestCreate":
        """проверяет диапазон дат"""
        if self.end_date < self.start_date:
            raise ValueError(
                "end_date must be greater than or equal to start_date"
            )
        return self


class LeaveRequestReject(BaseModel):
    manager_comment: str = Field(min_length=1, max_length=1000)

    @field_validator("manager_comment")
    @classmethod
    def strip_manager_comment(cls, value: str) -> str:
        """убирает лишние пробелы в комментарии"""
        stripped = value.strip()
        if not stripped:
            raise ValueError("manager_comment must not be blank")
        return stripped


class LeaveRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    start_date: date
    end_date: date
    reason: Optional[str]
    status: str
    manager_comment: Optional[str]
    processed_by_id: Optional[int]
    processed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
