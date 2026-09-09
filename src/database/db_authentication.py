import sqlite3
import uuid
from services.config import settings


def _create_user_record(
    conn: sqlite3.Connection, 
    email: str, 
    username: str, 
    permissions: str, 
    hashed_password: str = None, 
    oauth_provider: str = None, 
    oauth_id: str = None
): 
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO users (id, email, username, hashed_password, permissions, oauth_provider, oauth_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING *;
            """,
            (str(uuid.uuid4()), email, username, hashed_password, permissions, oauth_provider, oauth_id)
        )
        new_user = cursor.fetchall()
        
    return dict(new_user[0]) if new_user else None

def add_password_user(
    conn: sqlite3.Connection, 
    email: str, 
    username: str, 
    hashed_password: str, 
    permissions: str
):
    return _create_user_record(
        conn=conn,
        email=email, 
        username=username, 
        hashed_password=hashed_password, 
        permissions=permissions
    )

def add_oauth_user(
    conn: sqlite3.Connection, 
    email: str, 
    username: str, 
    permissions: str, 
    oauth_provider: str, 
    oauth_id: str
):
    return _create_user_record(
        conn=conn,
        email=email, 
        username=username, 
        permissions=permissions,
        oauth_provider=oauth_provider, 
        oauth_id=oauth_id
    )

def fetch_user_by_username(conn: sqlite3.Connection, username: str):
    cursor = conn.execute(
        "SELECT * FROM users WHERE username = ?", 
        (username,)
    )
    user = cursor.fetchone()
    return dict(user) if user else None

def fetch_user_permissions_by_id(conn: sqlite3.Connection, user_id: str):
    cursor = conn.execute(
        "SELECT permissions FROM users WHERE id = ?", 
        (user_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else None

def _create_user_session(
    conn: sqlite3.Connection,
    user_id: str, 
    email: str, 
    username: str, 
    permissions: str,
    avatar_hash: str = None, 
    oauth_access_token: str = None, 
    ip_address: str = None, 
    user_agent: str = None
):
    session_token = str(uuid.uuid4())
    with conn:
        conn.execute(
            """
            INSERT INTO sessions (session_token, user_id, email, username, permissions, avatar_hash, oauth_access_token, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_token, user_id, email, username, permissions, avatar_hash, oauth_access_token, ip_address, user_agent)
        )
        
    return session_token

def create_password_session(
    conn: sqlite3.Connection, 
    user_id: str, 
    email: str, 
    username: str, 
    permissions: str, 
    ip_address: str, 
    user_agent: str
):
    return _create_user_session(
        conn=conn,
        user_id=user_id,
        email=email,
        username=username,
        permissions=permissions,
        ip_address=ip_address,
        user_agent=user_agent
    )

def create_oauth_session(
    conn: sqlite3.Connection, 
    user_id: str, 
    email: str, 
    username: str, 
    permissions: str,
    avatar_url: str, 
    oauth_token: str, 
    ip_address: str, 
    user_agent: str
):
    return _create_user_session(
        conn=conn,
        user_id=user_id,
        email=email,
        username=username,
        permissions=permissions,
        avatar_hash=avatar_url, 
        oauth_access_token=oauth_token,
        ip_address=ip_address,
        user_agent=user_agent
    )

def fetch_user_session(conn: sqlite3.Connection, session_token: str):
    cursor = conn.execute(
        """
        SELECT 
        id, session_token, user_id, email, username, permissions, avatar_hash, oauth_access_token, ip_address, user_agent, created_at, is_active
        FROM sessions 
        WHERE session_token = ?
        """,
        (session_token,),
    )
    session_data = cursor.fetchone()
    return dict(session_data) if session_data else None

def fetch_user_session_by_id(conn: sqlite3.Connection, id: int):
    cursor = conn.execute(
        """
        SELECT 
        id, session_token, user_id, email, username, permissions, avatar_hash, oauth_access_token, ip_address, user_agent, created_at, is_active
        FROM sessions 
        WHERE id = ?
        """,
        (id,),
    )
    session_data = cursor.fetchone()
    return dict(session_data) if session_data else None

def revoke_user_session(conn: sqlite3.Connection, session_token: str):
    with conn:
        conn.execute(
            """
            UPDATE sessions SET
                is_active = 0,
                revoked_at = CURRENT_TIMESTAMP
            WHERE session_token = ?
            """, 
            (session_token,)
        )

def fetch_all_active_sessions(conn: sqlite3.Connection):
    cursor = conn.execute(
        """
        SELECT  
        id, session_token, user_id, email, username, permissions, avatar_hash, oauth_access_token, ip_address, user_agent, created_at, is_active
        FROM sessions 
        WHERE is_active = 1
        """
    )
    session_data = cursor.fetchall()
    return [dict(row) for row in session_data] if session_data else []

def count_total_users(conn: sqlite3.Connection):
    cursor = conn.execute(
        """
        SELECT COUNT(*) FROM users;
        """
    )
    total_users = cursor.fetchone()[0]
    return total_users if total_users else 0

def fetch_all_users(conn: sqlite3.Connection):
    cursor = conn.execute(
        """
        SELECT id, email, username, permissions, created_at
        FROM users
        """
    )
    all_users = cursor.fetchall()
    return [dict(row) for row in all_users] if all_users else []