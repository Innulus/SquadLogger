import os
import logging
from services.db_connection import get_current_schema_version, get_db_context
from services.config import settings, BASE_DIR
from contextlib import contextmanager

MIGRATIONS_DIR = BASE_DIR / "database" / "migrations"
logging.info(MIGRATIONS_DIR)

def apply_migrations(db_path=settings.PROD_DB_PATH, conn=None):
    # 1. Use the provided connection if it exists; otherwise, use the context manager
    if conn is not None:
        _do_migrations(conn)
    else:
        with get_db_context() as new_conn:
            _do_migrations(new_conn)

def _do_migrations(conn):
    """Internal helper to handle the migration logic using a specific connection"""
    cursor = conn.cursor()

    current_version = get_current_schema_version(conn)
    logging.info(f"Current schema version: {current_version}")

    migration_files = sorted(
        [
            f
            for f in os.listdir(MIGRATIONS_DIR)
            if f.endswith(".sql") and f[:3].isdigit()
        ]
    )

    total_migration_files = len(migration_files)
    completed_files = 0
    
    for file in migration_files:
        version = int(file.split("_")[0])
        if version > current_version:
            completed_files += 1
            filepath = os.path.join(MIGRATIONS_DIR, file)
            logging.info(
                f"Applying migration {file}... [{completed_files}/{total_migration_files}]"
            )

            with open(filepath, "r") as f:
                sql = f.read()
                try:
                    # Use the connection as a context manager for the transaction
                    with conn: 
                        cursor.executescript(sql)
                    
                    logging.info(
                        f"Migration {file} applied successfully. [{completed_files}/{total_migration_files}]"
                    )
                except Exception as e:
                    logging.error(f"Failed to apply {file}: {e}")
                    # No need for manual rollback here because 'with conn' handles it
                    break 

    logging.info("Migration process complete.\n")
