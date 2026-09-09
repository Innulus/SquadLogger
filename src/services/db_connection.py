import sqlite3
from services.config import settings
from fastapi import Request
from typing import Optional
from contextlib import contextmanager


def create_db_connection(db_path: str):
    conn = sqlite3.connect(db_path, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db_context(db_path: str = None):
    target_path = db_path or settings.PROD_DB_PATH
    conn = create_db_connection(target_path)
    try:
        yield conn
    finally:
        conn.close()


def get_db():
    conn = create_db_connection(db_path=settings.PROD_DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def get_current_schema_version(conn=None):
    if conn is not None:
        return _fetch_version(conn)
    
    with get_db_context() as new_conn:
        return _fetch_version(new_conn)

def _fetch_version(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_version")
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.OperationalError:
        return 0