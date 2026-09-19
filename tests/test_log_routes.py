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
        "punishment_duration": "60",
        "server_name": "US-Central",
        "reason_given": "Exploiting",
    }
    response = client.post("/logs/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["id"] is not None
    assert data["username"] == "Gamer123"
    assert data["SteamID"] == "STEAM_0:1:99999"


def test_create_log_unauthorized(client):
    def mock_failed_auth():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        )

    app.dependency_overrides[verify_api_code_and_log] = mock_failed_auth

    payload = {
        "steam_id": "STEAM_0:1:99999",
        "username": "Gamer123",
        "punishment_duration": "60",
        "server_name": "US-Central",
    }
    response = client.post("/logs/", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Clean up override
    app.dependency_overrides.pop(verify_api_code_and_log, None)


def test_read_paginated_logs(client):
    for i in range(5):
        client.post(
            "/logs/",
            json={
                "steam_id": f"STEAM_{i}",
                "username": f"User_{i}",
                "punishment_duration": "10",
                "server_name": "ServerA",
            },
        )

    response = client.get("/logs/?page=1")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "items" in data
    assert "pagination" in data
    assert data["pagination"]["total_count"] == 5


def test_get_log_by_id(client):
    create_res = client.post(
        "/logs/",
        json={
            "steam_id": "STEAM_BY_ID",
            "username": "SpecificUser",
            "punishment_duration": "45m",
            "server_name": "ServerA",
        },
    )
    log_id = create_res.json()["id"]

    res = client.get(f"/logs/{log_id}")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["id"] == log_id
    assert res.json()["username"] == "SpecificUser"

    bad_res = client.get("/logs/999999")
    assert bad_res.status_code == status.HTTP_404_NOT_FOUND


def test_update_log_flow(client):
    create_res = client.post(
        "/logs/",
        json={
            "steam_id": "STEAM_INITIAL",
            "username": "OldName",
            "punishment_duration": "15",
            "server_name": "Server1",
        },
    )
    log_id = create_res.json()["id"]

    update_payload = {
        "steam_id": "STEAM_UPDATED",
        "username": "NewName",
        "punishment_duration": "30",
        "server_name": "Server2",
        "reason_given": "Fixed Reason",
    }
    update_res = client.put(f"/logs/{log_id}", json=update_payload)
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.json()["username"] == "NewName"
    assert update_res.json()["server_name"] == "Server2"

    bad_res = client.put("/logs/999999", json=update_payload)
    assert bad_res.status_code == status.HTTP_404_NOT_FOUND


def test_delete_log_flow(client):
    create_res = client.post(
        "/logs/",
        json={
            "steam_id": "STEAM_DEL",
            "username": "DeleteMe",
            "punishment_duration": "100",
            "server_name": "Server1",
        },
    )
    log_id = create_res.json()["id"]

    delete_res = client.delete(f"/logs/{log_id}")
    assert delete_res.status_code == status.HTTP_200_OK
    assert delete_res.json() == {"success": True, "deleted_id": log_id}

    bad_res = client.delete(f"/logs/{log_id}")
    assert bad_res.status_code == status.HTTP_404_NOT_FOUND


def test_search_logs_endpoint_success(client):
    """Tests searching across various query parameters via the HTTP API."""
    client.post(
        "/logs/",
        json={
            "steam_id": "STEAM_0:1:77777",
            "username": "ShadowSniper",
            "punishment_duration": "7d",
            "server_name": "US-West-Trade",
            "reason_given": "Wallhacking",
        },
    )
    client.post(
        "/logs/",
        json={
            "steam_id": "STEAM_0:0:88888",
            "username": "CasualGamer",
            "punishment_duration": "1h",
            "server_name": "EU-Central",
            "reason_given": "Mic spamming music",
        },
    )

    # Search for "Sniper"
    response = client.get("/logs/search?search_query=Sniper")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["pagination"]["total_count"] == 1
    assert data["items"][0]["username"] == "ShadowSniper"

    # Search for reason keyword "spam"
    response = client.get("/logs/search?search_query=spam")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["pagination"]["total_count"] == 1
    assert data["items"][0]["username"] == "CasualGamer"

    # Search with no matching items
    response = client.get("/logs/search?search_query=definitely_not_here")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["pagination"]["total_count"] == 0
    assert response.json()["items"] == []


def test_search_logs_endpoint_validation(client):
    """Tests missing parameters and routing precedence."""
    # Omitting search_query must return 422 Unprocessable Entity
    missing_query_res = client.get("/logs/search")
    assert missing_query_res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Ensure /logs/search is NOT captured by /logs/{log_id} with integer parsing failure
    valid_query_res = client.get("/logs/search?search_query=test")
    assert valid_query_res.status_code == status.HTTP_200_OK