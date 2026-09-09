CREATE TABLE sessions (
    id INTEGER PRIMARY KEY NOT NULL,
    session_token VARCHAR(255),
    user_id TEXT NOT NULL,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100),
    permissions TEXT NOT NULL,
    avatar_hash VARCHAR(255),
    oauth_access_token TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    revoked_at TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

UPDATE schema_version SET version = 2; 