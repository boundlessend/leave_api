from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import AppException
from app.db.models import LeaveRequest, User
from app.schemas.leave_request import LeaveRequestCreate, LeaveRequestReject


class LeaveRequestService:
    """содержит бизнес логику по заявкам"""

    def __init__(self, db: Session):
        self.db = db

    def create_request(
        self, user: User, payload: LeaveRequestCreate
    ) -> LeaveRequest:
        """создает заявку если нет пересечений"""
        overlap_query = select(LeaveRequest).where(
            LeaveRequest.user_id == user.id,
            LeaveRequest.status.in_(["pending", "approved"]),
            LeaveRequest.start_date <= payload.end_date,
            LeaveRequest.end_date >= payload.start_date,
        )
        overlap = self.db.scalar(overlap_query)
        if overlap is not None:
            raise AppException(
                409,
                "leave_request_overlap",
                "есть пересечение с существующей заявкой",
                details={
                    "existing_request_id": overlap.id,
                    "existing_status": overlap.status,
                },
            )

        leave_request = LeaveRequest(
            user_id=user.id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            reason=payload.reason,
            status="pending",
        )
        self.db.add(leave_request)
        self.db.commit()
        self.db.refresh(leave_request)
        return leave_request

    def list_user_requests(
        self, user_id: int, status: str | None = None
    ) -> list[LeaveRequest]:
        """возвращает заявки пользователя"""
        query = select(LeaveRequest).where(LeaveRequest.user_id == user_id)
        if status:
            query = query.where(LeaveRequest.status == status)
        query = query.order_by(
            LeaveRequest.created_at.desc(), LeaveRequest.id.desc()
        )
        return list(self.db.scalars(query).all())

    def list_all_requests(
        self, status: str | None = None
    ) -> list[LeaveRequest]:
        """возвращает все заявки"""
        query = select(LeaveRequest)
        if status:
            query = query.where(LeaveRequest.status == status)
        query = query.order_by(
            LeaveRequest.created_at.desc(), LeaveRequest.id.desc()
        )
        return list(self.db.scalars(query).all())

    def approve_request(self, request_id: int, admin: User) -> LeaveRequest:
        """согласует pending заявку"""
        leave_request = self._get_request_or_404(request_id)
        self._assert_pending(leave_request)
        leave_request.status = "approved"
        leave_request.processed_by_id = admin.id
        leave_request.processed_at = datetime.now(timezone.utc)
        leave_request.manager_comment = None
        self.db.commit()
        self.db.refresh(leave_request)
        return leave_request

    def reject_request(
        self, request_id: int, admin: User, payload: LeaveRequestReject
    ) -> LeaveRequest:
        """отклоняет pending заявку"""
        leave_request = self._get_request_or_404(request_id)
        self._assert_pending(leave_request)
        leave_request.status = "rejected"
        leave_request.processed_by_id = admin.id
        leave_request.processed_at = datetime.now(timezone.utc)
        leave_request.manager_comment = payload.manager_comment
        self.db.commit()
        self.db.refresh(leave_request)
        return leave_request

    def _get_request_or_404(self, request_id: int) -> LeaveRequest:
        """ищет заявку по id"""
        leave_request = self.db.get(LeaveRequest, request_id)
        if leave_request is None:
            raise AppException(
                404, "leave_request_not_found", "заявка не найдена"
            )
        return leave_request

    @staticmethod
    def _assert_pending(leave_request: LeaveRequest) -> None:
        """проверяет что заявку еще можно обработать"""
        if leave_request.status != "pending":
            raise AppException(
                409,
                "leave_request_already_closed",
                "заявка уже закрыта",
                details={"current_status": leave_request.status},
            )
