
import uuid
import os

UNIQUE_DB_ID = str(uuid.uuid4())
MEM_PATH = f"file:{UNIQUE_DB_ID}?mode=memory&cache=shared"
os.environ["PROD_DB_PATH"] = MEM_PATH

import pytest
from services.config import settings
from services.db_connection import create_db_connection
from services.schema_migrator import apply_migrations

@pytest.fixture
def test_db(monkeypatch):
    mem_path = f"file:{uuid.uuid4()}?mode=memory&cache=shared"

    # Redirect every settings.PROD_DB_PATH lookup (used by create_connection,
    # db_qa.py, etc.) to this test's isolated in-memory db.
    monkeypatch.setattr(settings, "PROD_DB_PATH", mem_path)
    # This app has no per-request auth — routes act as settings.MAIN_USER_ID.

    test_conn = create_db_connection(db_path=mem_path)
    apply_migrations(conn=test_conn)

    yield test_conn

    test_conn.close()

@pytest.fixture
def client(test_db):
    from fastapi.testclient import TestClient
    from src.main import app  
    
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def seeded_admin_db(test_db):
    """An extension fixture that automatically inserts an admin before the test runs."""
    from src.database.db_authentication import add_password_user
    from src.services.security import get_password_hash
    
    # Pre-hash and push a test user into the fresh memory space
    hashed = get_password_hash("TestAdminPassword555!")
    add_password_user(
        conn=test_db,
        email="seeded@spine.com",
        username="seeded_admin",
        hashed_password=hashed,
        permissions="Admin"
    )
    
    # Hand over this pre-seeded database connection
    yield test_db

@pytest.fixture
def seeded_standard_user_db(test_db):
    """An extension fixture that automatically inserts an admin before the test runs."""
    from src.database.db_authentication import add_password_user
    from src.services.security import get_password_hash
    
    hashed = get_password_hash("TestStandardUserPassword555!")
    add_password_user(
        conn = test_db,
        email="standard@spine.com",
        username="standard_user",
        hashed_password=hashed,
        permissions="User"
    )
    
    # Hand over this pre-seeded database connection
    yield test_db

@pytest.fixture
def authenticated_admin_client(client, test_db):
    mock_admin_token = "mock-test-session-uuid-1234"
    mock_admin_id = "fake-user-id-555"
    
    cursor = test_db.cursor()
    cursor.execute(
        """
        INSERT INTO users (id, email, username, permissions, hashed_password)
        VALUES (?, ?, ?, ?, ?);
        """,
        (mock_admin_id, "seeded@spine.com", "seeded_admin", "Admin", "mock-password-hash")
    )

    cursor.execute(
        """
        INSERT INTO sessions (session_token, user_id, email, username, permissions, is_active)
        VALUES (?, ?, ?, ?, ?, 1);
        """,
        (mock_admin_token, mock_admin_id, "seeded@spine.com", "seeded_admin", "Admin")
    )

    test_db.commit()
   
    client.cookies.set("session_token", mock_admin_token)

    # Hand over this pre-seeded logged in database connection
    yield client

@pytest.fixture
def authenticated_standard_client(client, test_db):
   
    mock_user_session_token = "mock-standard-session-uuid-5678"
    mock_user_id = "fake-standard-user-id-999"
    
    cursor = test_db.cursor()
    
    # Insert a standard user into the users table
    cursor.execute(
        """
        INSERT INTO users (id, email, username, permissions, hashed_password)
        VALUES (?, ?, ?, ?, ?);
        """,
        (mock_user_id, "standard@spine.com", "standard_user", "User", "mock-password-hash")
    )

    # 2. Insert an active session matching the standard user
    cursor.execute(
        """
        INSERT INTO sessions (session_token, user_id, email, username, permissions, is_active)
        VALUES (?, ?, ?, ?, ?, 1);
        """,
        (mock_user_session_token, mock_user_id, "standard@spine.com", "standard_user", "User")
    )

    test_db.commit()
   
    # 3. Inject the cookie directly into the TestClient session context
    client.cookies.set("session_token", mock_user_session_token)

    # Hand over the pre-seeded logged-in standard client
    yield client