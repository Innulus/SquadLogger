import os
import sqlite3
from datetime import datetime, timezone
from math import ceil
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from services.config import settings


def create_main_log(
    conn: sqlite3.Connection,
    steam_id: str,
    username: str,
    punishment_duration: int,
    server_name: str,
    reason_given: Optional[str] = None
):
    timestamp = datetime.now(timezone.utc).isoformat()

    with conn:
        cursor = conn.execute(
            """
            INSERT INTO main_logs (
                log_timestamp, username, SteamID, reason_given,
                punishment_duration, server_name
            )
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING *;
            """,
            (
                timestamp,
                username,
                steam_id,
                reason_given,
                punishment_duration,
                server_name
            ),
        )
        new_log = cursor.fetchall()
    return dict(new_log[0]) if new_log else None


def get_paginated_main_logs(
    conn: sqlite3.Connection,
    page: int = 1
) -> Dict[str, Any]:
    """
    Fetches paginated logs from SQLite using LIMIT and OFFSET.
    
    The page size is bounded between 1 and MAX_PAGE_SIZE (from .env).
    """
    # Sanitize page
    page = max(1, page)

    # Sanitize and clamp page size to MAX_PAGE_SIZE
    page_size = settings.MAX_LOG_CHUNK_SIZE

    offset = (page - 1) * page_size

    # Fetch total count for pagination metadata
    count_cursor = conn.execute("SELECT COUNT(*) FROM main_logs")
    total_count = count_cursor.fetchone()[0]

    total_pages = ceil(total_count / page_size) if total_count > 0 else 1

    # Query chunk of logs
    cursor = conn.execute(
        """
        SELECT * FROM main_logs 
        ORDER BY id DESC 
        LIMIT ? OFFSET ?
        """,
        (page_size, offset),
    )
    logs = cursor.fetchall()

    return {
        "items": [dict(row) for row in logs] if logs else [],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
    }


def get_all_main_logs(conn: sqlite3.Connection):
    """Fallback to retrieve all logs without pagination."""
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
    reason_given: Optional[str] = None
):
    with conn:
        cursor = conn.execute(
            """
            UPDATE main_logs 
            SET SteamID = ?, username = ?, punishment_duration = ?, 
                server_name = ?, reason_given = ?
            WHERE id = ?
            RETURNING *;
            """,
            (
                steam_id,
                username,
                punishment_duration,
                server_name,
                reason_given,
                log_id
            ),
        )
        updated_log = cursor.fetchall()
    return dict(updated_log[0]) if updated_log else None


def delete_main_log(conn: sqlite3.Connection, log_id: int):
    try:
        with conn:
            cursor = conn.execute("DELETE FROM main_logs WHERE id = ?", (log_id,))
        return cursor.rowcount > 0
    except sqlite3.Error:
        return False

