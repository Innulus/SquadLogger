/* Content tables below. */
CREATE TABLE users (
    -- SQLite uses TEXT for UUIDs or INTEGER PRIMARY KEY for auto-increment
    id TEXT PRIMARY KEY,
    
    -- Identity & Contact
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    
    -- Local Password Auth
    hashed_password TEXT, 
    
    -- OAuth Tracking
    oauth_provider TEXT,
    oauth_id TEXT,
    
    --Roles
    permissions TEXT NOT NULL,
    
    -- Account Status (SQLite uses 1/0 for Booleans)
    is_active INTEGER DEFAULT 1,
    is_verified INTEGER DEFAULT 0,
    
    -- Timestamps (Standardized format for SQLite)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,

    -- Constraints
    -- Note: Ensure your SQLite version supports CHECK (most modern ones do)
    CONSTRAINT auth_present CHECK (hashed_password IS NOT NULL OR oauth_id IS NOT NULL)
);

-- Performance Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id);

/* Create schema table to keep track of schema version */
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

INSERT INTO schema_version (version) VALUES (1);