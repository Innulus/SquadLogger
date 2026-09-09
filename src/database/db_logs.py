import sqlite3
from datetime import datetime, timezone
from typing import Optional

def create_main_log(
    conn: sqlite3.Connection, 
    steam_id: str, 
    username: str, 
    punishment_duration: int, 
    server_name: str,
    reason_given: Optional[str] = None,
    issued_by: Optional[str] = None,
    review: Optional[str] = None
):
    timestamp = datetime.now(timezone.utc).isoformat()
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO main_logs (log_timestamp, username, SteamID, reason_given, punishment_duration, server_name, issued_by, review)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *;
            """,
            (timestamp, username, steam_id, reason_given, punishment_duration, server_name, issued_by, review)
        )
        new_log = cursor.fetchall()
    return dict(new_log[0]) if new_log else None


def get_all_main_logs(conn: sqlite3.Connection):
    cursor = conn.execute("SELECT * FROM main_logs ORDER BY id DESC")
    logs = cursor.fetchall()
    return [dict(row) for row in logs] if logs else []


def get_main_log_by_id(conn: sqlite3.Connection, log_id: int):
    cursor = conn.execute("SELECT * FROM main_logs WHERE id = ?", (log_id,))
    log = cursor.fetchone()
    return dict(log) if log else None


def update_main_log(
    conn: sqlite3.Connection, 
    log_id: int, 
    steam_id: str, 
    username: str, 
    punishment_duration: int, 
    server_name: str,
    reason_given: Optional[str] = None,
    issued_by: Optional[str] = None,
    review: Optional[str] = None
):
    with conn:
        cursor = conn.execute(
            """
            UPDATE main_logs 
            SET SteamID = ?, username = ?, punishment_duration = ?, server_name = ?, reason_given = ?, issued_by = ?, review = ?
            WHERE id = ?
            RETURNING *;
            """,
            (steam_id, username, punishment_duration, server_name, reason_given, issued_by, review, log_id)
        )
        updated_log = cursor.fetchall()
    return dict(updated_log[0]) if updated_log else None


def delete_main_log(conn: sqlite3.Connection, log_id: int):
    try:
        with conn:
            conn.execute("DELETE FROM main_logs WHERE id = ?", (log_id,))
        return True
    except sqlite3.Error:
        return False

def review_main_log(conn: sqlite3.Connection, log_id: int, reviewer: str):
    with conn:
        cursor = conn.execute(
            """
            UPDATE main_logs 
            SET review = ?
            WHERE id = ?
            RETURNING *;
            """,
            (reviewer, log_id)
        )
        updated_log = cursor.fetchall()
    return dict(updated_log[0]) if updated_log else None