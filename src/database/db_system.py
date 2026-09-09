import sqlite3
import uuid
from datetime import datetime

def fetch_user_by_user_id(conn: sqlite3.Connection, user_id: str):
    cursor = conn.execute(
        "SELECT * FROM users WHERE id = ?", 
        (user_id,)
    )
    user = cursor.fetchone()
    return dict(user) if user else None

def update_user_by_user_id(
    conn: sqlite3.Connection, 
    user_id: str, 
    username: str, 
    email: str, 
    permissions: str
):
    with conn:
        conn.execute(
            """ 
            UPDATE users 
            SET username = ?, email = ?, permissions = ?
            WHERE id = ?;
            """,
            (username, email, permissions, user_id),
        )

def delete_user_by_user_id(conn: sqlite3.Connection, user_id: str):
    try:
        with conn:
            conn.execute(
                """
                DELETE FROM users 
                WHERE id = ?;
                """,
                (user_id,)
            )
        return True
    except sqlite3.Error:
        return False

def update_all_active_session_permissions_by_user_id(
    conn: sqlite3.Connection, 
    user_id: str, 
    permissions: str
):
    with conn:
        cursor = conn.execute(
            """
            UPDATE sessions
            SET permissions = ?
            WHERE user_id = ? 
              AND is_active = 1 
              AND revoked_at IS NULL 
              AND created_at >= datetime('now', '-1 day');
            """,
            (permissions, user_id)
        )
    return cursor.rowcount  # Returns total count of updated sessions