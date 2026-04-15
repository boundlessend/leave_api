from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession, get_current_user
from app.db.models import User
from app.schemas.leave_request import LeaveRequestCreate, LeaveRequestRead
from app.services.leave_requests import LeaveRequestService

router = APIRouter(prefix="/api/leave-requests", tags=["leave requests"])


@router.post(
    "", response_model=LeaveRequestRead, status_code=status.HTTP_201_CREATED
)
def create_leave_request(
    payload: LeaveRequestCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
) -> LeaveRequestRead:
    """создает заявку текущего пользователя"""
    return LeaveRequestService(db).create_request(current_user, payload)


@router.get(
    "", response_model=list[LeaveRequestRead], status_code=status.HTTP_200_OK
)
def list_my_leave_requests(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(pending|approved|rejected)$"),
    ] = None,
) -> list[LeaveRequestRead]:
    """возвращает заявки текущего пользователя"""
    return LeaveRequestService(db).list_user_requests(
        current_user.id, status=status_filter
    )
