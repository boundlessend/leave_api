from datetime import date

from app.db.models import LeaveRequest
from tests.conftest import login


def test_owner_sees_only_own_requests(
    client, session, regular_user, another_user
):
    session.add_all(
        [
            LeaveRequest(
                user_id=regular_user.id,
                start_date=date(2026, 5, 1),
                end_date=date(2026, 5, 2),
                status="pending",
            ),
            LeaveRequest(
                user_id=another_user.id,
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 2),
                status="pending",
            ),
        ]
    )
    session.commit()

    tokens = login(client, "user@example.com", "user123")
    response = client.get(
        "/api/leave-requests",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == regular_user.id


def test_admin_sees_all_requests(
    client, session, admin_user, regular_user, another_user
):
    session.add_all(
        [
            LeaveRequest(
                user_id=regular_user.id,
                start_date=date(2026, 5, 1),
                end_date=date(2026, 5, 2),
                status="pending",
            ),
            LeaveRequest(
                user_id=another_user.id,
                start_date=date(2026, 6, 1),
                end_date=date(2026, 6, 2),
                status="approved",
            ),
        ]
    )
    session.commit()

    tokens = login(client, "admin@example.com", "admin123")
    response = client.get(
        "/api/admin/leave-requests",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_user_cannot_approve_request(
    client, session, admin_user, regular_user
):
    leave_request = LeaveRequest(
        user_id=regular_user.id,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        status="pending",
    )
    session.add(leave_request)
    session.commit()
    session.refresh(leave_request)

    tokens = login(client, "user@example.com", "user123")
    response = client.patch(
        f"/api/leave-requests/{leave_request.id}/approve",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_closed_request_cannot_be_approved_twice(
    client, approved_request, admin_user
):
    tokens = login(client, "admin@example.com", "admin123")
    response = client.patch(
        f"/api/leave-requests/{approved_request.id}/approve",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "leave_request_already_closed"


def test_overlapping_requests_are_rejected(client, regular_user):
    tokens = login(client, "user@example.com", "user123")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    first = client.post(
        "/api/leave-requests",
        json={
            "start_date": "2026-05-10",
            "end_date": "2026-05-12",
            "reason": "trip",
        },
        headers=headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/api/leave-requests",
        json={
            "start_date": "2026-05-11",
            "end_date": "2026-05-13",
            "reason": "another trip",
        },
        headers=headers,
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "leave_request_overlap"


def test_admin_can_reject_with_comment_and_filter_by_status(
    client, session, admin_user, regular_user
):
    leave_request = LeaveRequest(
        user_id=regular_user.id,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 3),
        status="pending",
    )
    session.add(leave_request)
    session.commit()
    session.refresh(leave_request)

    tokens = login(client, "admin@example.com", "admin123")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    reject_response = client.patch(
        f"/api/leave-requests/{leave_request.id}/reject",
        json={"manager_comment": "release window"},
        headers=headers,
    )
    filtered_response = client.get(
        "/api/admin/leave-requests?status=rejected", headers=headers
    )

    assert reject_response.status_code == 200
    assert reject_response.json()["manager_comment"] == "release window"
    assert filtered_response.status_code == 200
    assert len(filtered_response.json()) == 1


def test_request_not_found_returns_404(client, admin_user):
    tokens = login(client, "admin@example.com", "admin123")
    response = client.patch(
        "/api/leave-requests/999/approve",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "leave_request_not_found"


def test_invalid_date_range_returns_validation_error(client, regular_user):
    tokens = login(client, "user@example.com", "user123")
    response = client.post(
        "/api/leave-requests",
        json={
            "start_date": "2026-05-12",
            "end_date": "2026-05-10",
            "reason": "trip",
        },
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
