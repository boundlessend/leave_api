from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession, get_current_admin
from app.db.models import User
from app.schemas.leave_request import LeaveRequestRead, LeaveRequestReject
from app.services.leave_requests import LeaveRequestService

router = APIRouter(tags=["admin"])


@router.patch(
    "/api/leave-requests/{request_id}/approve",
    response_model=LeaveRequestRead,
    status_code=status.HTTP_200_OK,
)
def approve_leave_request(
    request_id: int,
    db: DbSession,
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> LeaveRequestRead:
    """согласует заявку администратором"""
    return LeaveRequestService(db).approve_request(request_id, current_admin)


@router.patch(
    "/api/leave-requests/{request_id}/reject",
    response_model=LeaveRequestRead,
    status_code=status.HTTP_200_OK,
)
def reject_leave_request(
    request_id: int,
    payload: LeaveRequestReject,
    db: DbSession,
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> LeaveRequestRead:
    """отклоняет заявку администратором"""
    return LeaveRequestService(db).reject_request(
        request_id, current_admin, payload
    )


@router.get(
    "/api/admin/leave-requests",
    response_model=list[LeaveRequestRead],
    status_code=status.HTTP_200_OK,
)
def list_all_leave_requests(
    db: DbSession,
    _: Annotated[User, Depends(get_current_admin)],
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(pending|approved|rejected)$"),
    ] = None,
) -> list[LeaveRequestRead]:
    """возвращает все заявки для админа"""
    return LeaveRequestService(db).list_all_requests(status=status_filter)
