import pytest
from database.db_logs import (
    create_main_log,
    get_paginated_main_logs,
    get_all_main_logs,
    get_main_log_by_id,
    update_main_log,
    delete_main_log,
    review_main_log,
)


def test_create_and_get_log_by_id(test_db):
    log = create_main_log(
        conn=test_db,
        steam_id="STEAM_0:1:12345",
        username="TestUser",
        punishment_duration=60,
        server_name="US-East",
        reason_given="Rule violation",
        issued_by="Admin1",
    )

    assert log is not None
    assert log["username"] == "TestUser"
    assert log["SteamID"] == "STEAM_0:1:12345"
    assert log["punishment_duration"] == 60

    fetched = get_main_log_by_id(test_db, log["id"])
    assert fetched is not None
    assert fetched["id"] == log["id"]
    assert fetched["username"] == "TestUser"


def test_update_main_log(test_db):
    log = create_main_log(
        conn=test_db,
        steam_id="STEAM_0:1:11111",
        username="OriginalName",
        punishment_duration=30,
        server_name="EU-Central",
    )

    updated = update_main_log(
        conn=test_db,
        log_id=log["id"],
        steam_id="STEAM_0:1:22222",
        username="UpdatedName",
        punishment_duration=120,
        server_name="EU-North",
        reason_given="Updated Reason",
        issued_by="Admin2",
        review="Under Review",
    )

    assert updated["username"] == "UpdatedName"
    assert updated["SteamID"] == "STEAM_0:1:22222"
    assert updated["punishment_duration"] == 120
    assert updated["review"] == "Under Review"


def test_review_main_log(test_db):
    log = create_main_log(
        conn=test_db,
        steam_id="STEAM_0:1:33333",
        username="Reviewee",
        punishment_duration=15,
        server_name="US-West",
    )

    reviewed = review_main_log(test_db, log_id=log["id"], reviewer="SeniorAdmin")
    assert reviewed is not None
    assert reviewed["review"] == "SeniorAdmin"


def test_delete_main_log(test_db):
    log = create_main_log(
        conn=test_db,
        steam_id="STEAM_0:1:44444",
        username="ToDelete",
        punishment_duration=10,
        server_name="US-East",
    )

    assert delete_main_log(test_db, log["id"]) is True
    assert get_main_log_by_id(test_db, log["id"]) is None
    assert delete_main_log(test_db, 99999) is False


def test_get_paginated_main_logs(test_db, monkeypatch):
    # Set chunk size to 3 for predictable pagination math
    from services.config import settings
    monkeypatch.setattr(settings, "MAX_LOG_CHUNK_SIZE", 3)

    for i in range(8):
        create_main_log(
            conn=test_db,
            steam_id=f"STEAM_0:1:{i}",
            username=f"Player_{i}",
            punishment_duration=10 * i,
            server_name="Server1",
        )

    # Page 1 (expected: 3 items, has_next=True, has_previous=False)
    page_1 = get_paginated_main_logs(test_db, page=1)
    assert len(page_1["items"]) == 3
    assert page_1["pagination"]["page"] == 1
    assert page_1["pagination"]["total_count"] == 8
    assert page_1["pagination"]["total_pages"] == 3
    assert page_1["pagination"]["has_next"] is True
    assert page_1["pagination"]["has_previous"] is False

    # Page 3 (expected: 2 items remaining, has_next=False, has_previous=True)
    page_3 = get_paginated_main_logs(test_db, page=3)
    assert len(page_3["items"]) == 2
    assert page_3["pagination"]["page"] == 3
    assert page_3["pagination"]["has_next"] is False
    assert page_3["pagination"]["has_previous"] is True