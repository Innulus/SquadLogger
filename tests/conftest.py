import os
import uuid
import sqlite3
import pytest
from fastapi.testclient import TestClient

from services.config import settings
from services.db_connection import get_db, create_db_connection
from services.security import verify_api_code_and_log
from src.main import app


@pytest.fixture
def test_db(monkeypatch):
    """
    Creates an isolated in-memory SQLite database for each test,
    ensures required tables exist, and overrides the get_db dependency.
    """
    mem_path = f"file:{uuid.uuid4()}?mode=memory&cache=shared"
    monkeypatch.setattr(settings, "PROD_DB_PATH", mem_path)
    monkeypatch.setattr(settings, "MAX_LOG_CHUNK_SIZE", 5)

    conn = create_db_connection(db_path=mem_path)
    conn.row_factory = sqlite3.Row

    # Create the necessary schema for logs
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS main_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_timestamp TEXT NOT NULL,
                username TEXT NOT NULL,
                SteamID TEXT NOT NULL,
                reason_given TEXT,
                punishment_duration INTEGER NOT NULL,
                server_name TEXT NOT NULL,
                issued_by TEXT,
                review TEXT
            );
            """
        )

    yield conn

    conn.close()


@pytest.fixture
def client(test_db):
    """
    TestClient that overrides the database dependency and defaults
    the API authorization check to succeed.
    """
    # Override get_db to return our isolated test connection
    app.dependency_overrides[get_db] = lambda: test_db

    # Default auth override (mock authorized client)
    app.dependency_overrides[verify_api_code_and_log] = lambda: "mock_authorized_client"

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()