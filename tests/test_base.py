import pytest
from database.db_logs import (
    create_main_log,
    delete_main_log,
    get_all_main_logs,
    get_main_log_by_id,
    get_paginated_main_logs,
    search_main_logs,
    update_main_log,
)


def test_create_and_get_log_by_id(test_db):
    log = create_main_log(
        conn=test_db,
        steam_id="STEAM_0:1:12345",
        username="TestUser",
        punishment_duration="60",
        server_name="US-East",
        reason_given="Rule violation",
    )

    assert log is not None
    assert log["username"] == "TestUser"
    assert log["SteamID"] == "STEAM_0:1:12345"
    assert str(log["punishment_duration"]) == "60"

    fetched = get_main_log_by_id(test_db, log["id"])
    assert fetched is not None
    assert fetched["id"] == log["id"]
    assert fetched["username"] == "TestUser"


def test_update_main_log(test_db):
    log = create_main_log(
        conn=test_db,
        steam_id="STEAM_0:1:11111",
        username="OriginalName",
        punishment_duration="30",
        server_name="EU-Central",
    )

    updated = update_main_log(
        conn=test_db,
        log_id=log["id"],
        steam_id="STEAM_0:1:22222",
        username="UpdatedName",
        punishment_duration="120",
        server_name="EU-North",
        reason_given="Updated Reason",
    )

    assert updated["username"] == "UpdatedName"
    assert updated["SteamID"] == "STEAM_0:1:22222"
    assert str(updated["punishment_duration"]) == "120"


def test_delete_main_log(test_db):
    log = create_main_log(
        conn=test_db,
        steam_id="STEAM_0:1:44444",
        username="ToDelete",
        punishment_duration="10",
        server_name="US-East",
    )

    assert delete_main_log(test_db, log["id"]) is True
    assert get_main_log_by_id(test_db, log["id"]) is None
    assert delete_main_log(test_db, 99999) is False


def test_get_paginated_main_logs(test_db, monkeypatch):
    from services.config import settings

    monkeypatch.setattr(settings, "MAX_LOG_CHUNK_SIZE", 3)

    for i in range(8):
        create_main_log(
            conn=test_db,
            steam_id=f"STEAM_0:1:{i}",
            username=f"Player_{i}",
            punishment_duration=f"{10 * i}",
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


def test_search_main_logs_matching_fields(test_db):
    """Verifies that search_main_logs correctly matches across different target columns."""
    create_main_log(
        conn=test_db,
        steam_id="STEAM_0:0:1111",
        username="TargetGamer",
        punishment_duration="1d",
        server_name="US-West-1",
        reason_given="Aimbotting detected",
    )
    create_main_log(
        conn=test_db,
        steam_id="STEAM_0:1:2222",
        username="Innocent bystander",
        punishment_duration="permanent",
        server_name="EU-East-2",
        reason_given="Griefing spawn points",
    )

    # Match by partial username (case-insensitive ASCII)
    res_user = search_main_logs(test_db, "%gamer%")
    assert res_user["pagination"]["total_count"] == 1
    assert res_user["items"][0]["username"] == "TargetGamer"

    # Match by partial SteamID
    res_steam = search_main_logs(test_db, "%1111%")
    assert res_steam["pagination"]["total_count"] == 1
    assert res_steam["items"][0]["SteamID"] == "STEAM_0:0:1111"

    # Match by reason
    res_reason = search_main_logs(test_db, "%griefing%")
    assert res_reason["pagination"]["total_count"] == 1
    assert res_reason["items"][0]["username"] == "Innocent bystander"

    # Match by server name
    res_server = search_main_logs(test_db, "%US-West%")
    assert res_server["pagination"]["total_count"] == 1

    # Match by duration string
    res_dur = search_main_logs(test_db, "%perm%")
    assert res_dur["pagination"]["total_count"] == 1
    assert res_dur["items"][0]["punishment_duration"] == "permanent"


def test_search_main_logs_pagination_and_no_matches(test_db, monkeypatch):
    """Verifies search pagination count accuracy and behavior when 0 results match."""
    from services.config import settings

    monkeypatch.setattr(settings, "MAX_LOG_CHUNK_SIZE", 2)

    # Seed 5 logs with shared keyword "Toxic" and 1 different log
    for i in range(5):
        create_main_log(
            conn=test_db,
            steam_id=f"STEAM_0:1:{i}",
            username=f"ToxicPlayer_{i}",
            punishment_duration="30m",
            server_name="Server1",
            reason_given="Toxic behavior in chat",
        )

    create_main_log(
        conn=test_db,
        steam_id="STEAM_0:9:9999",
        username="CleanPlayer",
        punishment_duration="5m",
        server_name="Server1",
        reason_given="Accidental team hit",
    )

    # Page 1 for "toxic" (expected 2 out of 5 items)
    page_1 = search_main_logs(test_db, "%toxic%", page=1)
    assert len(page_1["items"]) == 2
    assert page_1["pagination"]["total_count"] == 5
    assert page_1["pagination"]["total_pages"] == 3
    assert page_1["pagination"]["has_next"] is True
    assert page_1["pagination"]["has_previous"] is False

    # Page 3 for "toxic" (expected 1 remaining item)
    page_3 = search_main_logs(test_db, "%toxic%", page=3)
    assert len(page_3["items"]) == 1
    assert page_3["pagination"]["page"] == 3
    assert page_3["pagination"]["has_next"] is False
    assert page_3["pagination"]["has_previous"] is True

    # Search term that does not exist
    no_results = search_main_logs(test_db, "%nonexistent_user%", page=1)
    assert len(no_results["items"]) == 0
    assert no_results["pagination"]["total_count"] == 0
    assert no_results["pagination"]["total_pages"] == 1
    assert no_results["pagination"]["has_next"] is False