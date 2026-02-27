"""Database schema definitions for local SQLite vault.

This module defines all table schemas matching the Django backend models
to ensure data compatibility and enable future sync capabilities.
"""

from __future__ import annotations

# Schema version tracking
SCHEMA_VERSION = 1

# Users table - local user profile
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    timezone TEXT DEFAULT 'UTC',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
)
"""

# Projects table
CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT,
    is_favorite BOOLEAN DEFAULT 0,
    is_archived BOOLEAN DEFAULT 0,
    protected BOOLEAN DEFAULT 0,
    user_id TEXT NOT NULL,
    workspace_id TEXT,
    display_order INTEGER,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted_at DATETIME,
    version INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
"""

# Labels table
CREATE_LABELS_TABLE = """
CREATE TABLE IF NOT EXISTS labels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#808080',
    user_id TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted_at DATETIME,
    version INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, name)
)
"""

# Contexts table (location-based)
CREATE_CONTEXTS_TABLE = """
CREATE TABLE IF NOT EXISTS contexts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT DEFAULT '#808080',
    icon TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    radius REAL NOT NULL DEFAULT 100.0,
    user_id TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted_at DATETIME,
    version INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
"""

# Tasks table - main task entity
CREATE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    description TEXT,
    is_completed BOOLEAN DEFAULT 0,
    due_date DATETIME,
    priority INTEGER DEFAULT 1,
    project_id TEXT,
    user_id TEXT NOT NULL,
    assigned_to_id TEXT,
    assigned_by_id TEXT,
    assigned_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    completed_at DATETIME,
    deleted_at DATETIME,
    version INTEGER DEFAULT 1,
    
    -- E2EE fields (JSON stored as TEXT)
    content_encrypted TEXT,
    description_encrypted TEXT,
    
    -- Eisenhower matrix
    is_urgent BOOLEAN,
    is_important BOOLEAN,
    
    -- Recurring tasks
    is_recurring BOOLEAN DEFAULT 0,
    recurrence_rule TEXT,
    recurrence_end DATETIME,
    next_occurrence DATETIME,
    parent_task_id TEXT,
    is_skipped BOOLEAN DEFAULT 0,
    skipped_at DATETIME,
    is_paused BOOLEAN DEFAULT 0,
    paused_at DATETIME,
    resumed_at DATETIME,
    is_exception BOOLEAN DEFAULT 0,
    
    -- Time tracking / Pomodoro
    estimated_time INTEGER,
    actual_time INTEGER,
    pomodoros_completed INTEGER DEFAULT 0,
    
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE CASCADE
)
"""

# Task-Label junction table (many-to-many)
CREATE_TASK_LABELS_TABLE = """
CREATE TABLE IF NOT EXISTS task_labels (
    task_id TEXT NOT NULL,
    label_id TEXT NOT NULL,
    PRIMARY KEY (task_id, label_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE
)
"""

# Task-Context junction table (many-to-many)
CREATE_TASK_CONTEXTS_TABLE = """
CREATE TABLE IF NOT EXISTS task_contexts (
    task_id TEXT NOT NULL,
    context_id TEXT NOT NULL,
    PRIMARY KEY (task_id, context_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (context_id) REFERENCES contexts(id) ON DELETE CASCADE
)
"""

# Reminders table (future feature)
CREATE_REMINDERS_TABLE = """
CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    reminder_date DATETIME NOT NULL,
    is_sent BOOLEAN DEFAULT 0,
    is_snoozed BOOLEAN DEFAULT 0,
    snoozed_until DATETIME,
    snoozed_from_id TEXT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (snoozed_from_id) REFERENCES reminders(id) ON DELETE SET NULL
)
"""

# Filters table (saved views)
CREATE_FILTERS_TABLE = """
CREATE TABLE IF NOT EXISTS filters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    query TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
"""

# Schema version tracking
CREATE_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME NOT NULL
)
"""

# Indexes for performance

# Tasks indexes
CREATE_TASK_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(is_completed, deleted_at)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_updated ON tasks(updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)",
    # Composite index for common queries
    "CREATE INDEX IF NOT EXISTS idx_tasks_user_completed ON tasks(user_id, is_completed, deleted_at)",
    # New indexes for v2 fields
    "CREATE INDEX IF NOT EXISTS idx_tasks_recurring ON tasks(is_recurring, is_paused)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_eisenhower ON tasks(is_urgent, is_important)",
]

# Projects indexes
CREATE_PROJECT_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_projects_favorite ON projects(is_favorite)",
    "CREATE INDEX IF NOT EXISTS idx_projects_archived ON projects(is_archived)",
]

# Labels indexes
CREATE_LABEL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_labels_user ON labels(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_labels_name ON labels(name)",
    "CREATE INDEX IF NOT EXISTS idx_labels_deleted ON labels(deleted_at)",
]

# Contexts indexes
CREATE_CONTEXT_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_contexts_user ON contexts(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_contexts_deleted ON contexts(deleted_at)",
]

# All table creation statements in order
ALL_TABLES = [
    CREATE_SCHEMA_VERSION_TABLE,
    CREATE_USERS_TABLE,
    CREATE_PROJECTS_TABLE,
    CREATE_LABELS_TABLE,
    CREATE_CONTEXTS_TABLE,
    CREATE_TASKS_TABLE,
    CREATE_TASK_LABELS_TABLE,
    CREATE_TASK_CONTEXTS_TABLE,
    CREATE_REMINDERS_TABLE,
    CREATE_FILTERS_TABLE,
]

# All index creation statements
ALL_INDEXES = (
    CREATE_TASK_INDEXES
    + CREATE_PROJECT_INDEXES
    + CREATE_LABEL_INDEXES
    + CREATE_CONTEXT_INDEXES
)


def initialize_schema(connection) -> None:
    """Initialize database schema with all tables and indexes.

    Args:
        connection: sqlite3.Connection object
    """
    cursor = connection.cursor()

    # Create all tables
    for create_statement in ALL_TABLES:
        cursor.execute(create_statement)

    # Create all indexes
    for index_statement in ALL_INDEXES:
        cursor.execute(index_statement)

    # Record schema version
    cursor.execute(
        "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
        (SCHEMA_VERSION,),
    )

    connection.commit()


def get_schema_version(connection) -> int:
    """Get current schema version from database.

    Args:
        connection: sqlite3.Connection object

    Returns:
        Schema version number, or 0 if not initialized
    """
    try:
        cursor = connection.execute("SELECT MAX(version) FROM schema_version")
        result = cursor.fetchone()
        return result[0] if result[0] is not None else 0
    except Exception:
        return 0
