import pytest
from fastapi import HTTPException, status
from services.security import verify_api_code_and_log
from src.main import app


def test_heartbeat(client):
    response = client.get("/logs/heartbeat")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_create_log_success(client):
    payload = {
        "steam_id": "STEAM_0:1:99999",
        "username": "Gamer123",
        "punishment_duration": 60,
        "server_name": "US-Central",
        "reason_given": "Exploiting",
        "issued_by": "ModA",
        "review": None,
    }
    response = client.post("/logs/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["id"] is not None
    assert data["username"] == "Gamer123"
    assert data["SteamID"] == "STEAM_0:1:99999"


def test_create_log_unauthorized(client):
    # Simulate failed API token check
    def mock_failed_auth():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        )

    app.dependency_overrides[verify_api_code_and_log] = mock_failed_auth

    payload = {
        "steam_id": "STEAM_0:1:99999",
        "username": "Gamer123",
        "punishment_duration": 60,
        "server_name": "US-Central",
    }
    response = client.post("/logs/", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_read_paginated_logs(client):
    # Seed entries
    for i in range(5):
        client.post(
            "/logs/",
            json={
                "steam_id": f"STEAM_{i}",
                "username": f"User_{i}",
                "punishment_duration": 10,
                "server_name": "ServerA",
            },
        )

    response = client.get("/logs/?page=1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "items" in data
    assert "pagination" in data
    assert data["pagination"]["total_count"] == 5


def test_update_log_flow(client):
    create_res = client.post(
        "/logs/",
        json={
            "steam_id": "STEAM_INITIAL",
            "username": "OldName",
            "punishment_duration": 15,
            "server_name": "Server1",
        },
    )
    log_id = create_res.json()["id"]

    update_payload = {
        "steam_id": "STEAM_UPDATED",
        "username": "NewName",
        "punishment_duration": 30,
        "server_name": "Server2",
        "reason_given": "Fixed Reason",
    }
    update_res = client.put(f"/logs/{log_id}", json=update_payload)
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.json()["username"] == "NewName"
    assert update_res.json()["server_name"] == "Server2"

    # Test update 404 for non-existent ID
    bad_res = client.put("/logs/999999", json=update_payload)
    assert bad_res.status_code == status.HTTP_404_NOT_FOUND


def test_review_log_flow(client):
    create_res = client.post(
        "/logs/",
        json={
            "steam_id": "STEAM_REV",
            "username": "NeedReview",
            "punishment_duration": 45,
            "server_name": "Server1",
        },
    )
    log_id = create_res.json()["id"]

    review_res = client.patch(f"/logs/{log_id}/review", json={"reviewer": "LeadAdmin"})
    assert review_res.status_code == status.HTTP_200_OK
    assert review_res.json()["review"] == "LeadAdmin"

    # Test review 404
    bad_res = client.patch("/logs/999999/review", json={"reviewer": "LeadAdmin"})
    assert bad_res.status_code == status.HTTP_404_NOT_FOUND


def test_delete_log_flow(client):
    create_res = client.post(
        "/logs/",
        json={
            "steam_id": "STEAM_DEL",
            "username": "DeleteMe",
            "punishment_duration": 100,
            "server_name": "Server1",
        },
    )
    log_id = create_res.json()["id"]

    delete_res = client.delete(f"/logs/{log_id}")
    assert delete_res.status_code == status.HTTP_200_OK
    assert delete_res.json() == {"success": True, "deleted_id": log_id}

    # Test delete 404
    bad_res = client.delete(f"/logs/{log_id}")
    assert bad_res.status_code == status.HTTP_404_NOT_FOUND