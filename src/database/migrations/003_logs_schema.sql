CREATE TABLE IF NOT EXISTS main_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_timestamp TEXT,
    username TEXT NOT NULL, 
    SteamID TEXT NOT NULL,
    reason_given TEXT,
    punishment_duration INTEGER NOT NULL,
    server_name TEXT NOT NULL, 
    issued_by TEXT,
    review TEXT
);


CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

INSERT INTO schema_version (version) VALUES (3);