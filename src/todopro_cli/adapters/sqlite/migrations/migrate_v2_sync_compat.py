"""
Database schema migration to v2 - Sync compatibility fixes

This migration adds missing fields needed for reliable sync with the backend:
- Adds updated_at, deleted_at, version to labels and contexts
- Adds color and icon to contexts
- Adds updated_at to filters
- Fixes task priority default from 3 to 1
- Adds missing task fields for recurring tasks, time tracking, and assignment
- Standardizes reminder field names
"""

from __future__ import annotations

MIGRATION_VERSION = 2

# SQLite doesn't support ALTER COLUMN DEFAULT or RENAME COLUMN easily
# We'll need to recreate tables with correct schemas

# ============================================
# NEW TABLE DEFINITIONS (v2)
# ============================================

CREATE_LABELS_TABLE_V2 = """
CREATE TABLE IF NOT EXISTS labels_v2 (
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

CREATE_CONTEXTS_TABLE_V2 = """
CREATE TABLE IF NOT EXISTS contexts_v2 (
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

CREATE_TASKS_TABLE_V2 = """
CREATE TABLE IF NOT EXISTS tasks_v2 (
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
    is_urgent BOOLEAN DEFAULT NULL,
    is_important BOOLEAN DEFAULT NULL,
    
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

CREATE_REMINDERS_TABLE_V2 = """
CREATE TABLE IF NOT EXISTS reminders_v2 (
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

CREATE_FILTERS_TABLE_V2 = """
CREATE TABLE IF NOT EXISTS filters_v2 (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    query TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
"""

# ============================================
# DATA MIGRATION QUERIES
# ============================================

MIGRATE_LABELS = """
INSERT INTO labels_v2 (
    id, name, color, user_id, created_at, updated_at, deleted_at, version
)
SELECT 
    id, 
    name, 
    COALESCE(color, '#808080'),
    user_id, 
    created_at,
    created_at as updated_at,
    NULL as deleted_at,
    1 as version
FROM labels
"""

MIGRATE_CONTEXTS = """
INSERT INTO contexts_v2 (
    id, name, color, icon, latitude, longitude, radius, user_id,
    created_at, updated_at, deleted_at, version
)
SELECT 
    id, 
    name,
    '#808080' as color,
    NULL as icon,
    latitude, 
    longitude, 
    radius,
    user_id,
    created_at,
    created_at as updated_at,
    NULL as deleted_at,
    1 as version
FROM contexts
"""

MIGRATE_TASKS = """
INSERT INTO tasks_v2 (
    id, content, description, is_completed, due_date, priority,
    project_id, user_id, assigned_to_id, assigned_by_id, assigned_at,
    created_at, updated_at, completed_at, deleted_at, version,
    content_encrypted, description_encrypted,
    is_urgent, is_important,
    is_recurring, recurrence_rule, recurrence_end, next_occurrence,
    parent_task_id, is_skipped, skipped_at, is_paused, paused_at, 
    resumed_at, is_exception,
    estimated_time, actual_time, pomodoros_completed
)
SELECT 
    id, content, description, is_completed, due_date,
    -- Priority: default 3 in old schema, change to 1 for new rows
    CASE WHEN priority = 3 THEN 1 ELSE priority END,
    project_id, user_id, assigned_to_id,
    NULL as assigned_by_id,
    NULL as assigned_at,
    created_at, updated_at, completed_at, deleted_at, version,
    content_encrypted, description_encrypted,
    -- Convert default 0 to NULL for auto-classification
    CASE WHEN is_urgent = 0 THEN NULL ELSE is_urgent END,
    CASE WHEN is_important = 0 THEN NULL ELSE is_important END,
    CASE WHEN recurrence_rule IS NOT NULL THEN 1 ELSE 0 END as is_recurring,
    recurrence_rule,
    NULL as recurrence_end,
    NULL as next_occurrence,
    parent_task_id,
    0 as is_skipped, NULL as skipped_at,
    0 as is_paused, NULL as paused_at, NULL as resumed_at,
    0 as is_exception,
    NULL as estimated_time,
    NULL as actual_time,
    0 as pomodoros_completed
FROM tasks
"""

MIGRATE_REMINDERS = """
INSERT INTO reminders_v2 (
    id, task_id, reminder_date, is_sent, is_snoozed,
    snoozed_until, snoozed_from_id, created_at
)
SELECT 
    id,
    task_id,
    remind_at,
    is_triggered,
    0 as is_snoozed,
    NULL as snoozed_until,
    NULL as snoozed_from_id,
    created_at
FROM reminders
"""

MIGRATE_FILTERS = """
INSERT INTO filters_v2 (
    id, name, query, user_id, created_at, updated_at
)
SELECT 
    id,
    name,
    query,
    user_id,
    created_at,
    created_at as updated_at
FROM filters
"""

# ============================================
# INDEX RECREATION
# ============================================

CREATE_LABELS_INDEXES_V2 = [
    "CREATE INDEX IF NOT EXISTS idx_labels_v2_user ON labels_v2(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_labels_v2_name ON labels_v2(name)",
    "CREATE INDEX IF NOT EXISTS idx_labels_v2_deleted ON labels_v2(deleted_at)",
]

CREATE_CONTEXTS_INDEXES_V2 = [
    "CREATE INDEX IF NOT EXISTS idx_contexts_v2_user ON contexts_v2(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_contexts_v2_deleted ON contexts_v2(deleted_at)",
]

CREATE_TASKS_INDEXES_V2 = [
    "CREATE INDEX IF NOT EXISTS idx_tasks_v2_due_date ON tasks_v2(due_date)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_v2_project ON tasks_v2(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_v2_user ON tasks_v2(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_v2_completed ON tasks_v2(is_completed, deleted_at)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_v2_updated ON tasks_v2(updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_v2_priority ON tasks_v2(priority)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_v2_user_completed ON tasks_v2(user_id, is_completed, deleted_at)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_v2_recurring ON tasks_v2(is_recurring, is_paused)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_v2_eisenhower ON tasks_v2(is_urgent, is_important)",
]

# ============================================
# MIGRATION EXECUTION STEPS
# ============================================


def run_migration(connection):
    """
    Execute migration from schema v1 to v2.

    Args:
        connection: sqlite3.Connection object

    Returns:
        bool: True if migration successful
    """
    cursor = connection.cursor()

    try:
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")

        print("Creating new table schemas (v2)...")

        # Create new tables
        cursor.execute(CREATE_LABELS_TABLE_V2)
        cursor.execute(CREATE_CONTEXTS_TABLE_V2)
        cursor.execute(CREATE_TASKS_TABLE_V2)
        cursor.execute(CREATE_REMINDERS_TABLE_V2)
        cursor.execute(CREATE_FILTERS_TABLE_V2)

        print("Migrating data from v1 to v2...")

        # Migrate data
        cursor.execute(MIGRATE_LABELS)
        labels_migrated = cursor.rowcount
        print(f"  ✓ Migrated {labels_migrated} labels")

        cursor.execute(MIGRATE_CONTEXTS)
        contexts_migrated = cursor.rowcount
        print(f"  ✓ Migrated {contexts_migrated} contexts")

        cursor.execute(MIGRATE_TASKS)
        tasks_migrated = cursor.rowcount
        print(f"  ✓ Migrated {tasks_migrated} tasks")

        cursor.execute(MIGRATE_REMINDERS)
        reminders_migrated = cursor.rowcount
        print(f"  ✓ Migrated {reminders_migrated} reminders")

        cursor.execute(MIGRATE_FILTERS)
        filters_migrated = cursor.rowcount
        print(f"  ✓ Migrated {filters_migrated} filters")

        print("Creating indexes...")

        # Create indexes
        for idx in CREATE_LABELS_INDEXES_V2:
            cursor.execute(idx)
        for idx in CREATE_CONTEXTS_INDEXES_V2:
            cursor.execute(idx)
        for idx in CREATE_TASKS_INDEXES_V2:
            cursor.execute(idx)

        print("Dropping old tables...")

        # Drop old tables (FK constraints handled by CASCADE)
        cursor.execute("DROP TABLE IF EXISTS task_labels")
        cursor.execute("DROP TABLE IF EXISTS task_contexts")
        cursor.execute("DROP TABLE IF EXISTS reminders")
        cursor.execute("DROP TABLE IF EXISTS tasks")
        cursor.execute("DROP TABLE IF EXISTS filters")
        cursor.execute("DROP TABLE IF EXISTS labels")
        cursor.execute("DROP TABLE IF EXISTS contexts")

        print("Renaming new tables...")

        # Rename new tables to original names
        cursor.execute("ALTER TABLE labels_v2 RENAME TO labels")
        cursor.execute("ALTER TABLE contexts_v2 RENAME TO contexts")
        cursor.execute("ALTER TABLE tasks_v2 RENAME TO tasks")
        cursor.execute("ALTER TABLE reminders_v2 RENAME TO reminders")
        cursor.execute("ALTER TABLE filters_v2 RENAME TO filters")

        print("Recreating junction tables...")

        # Recreate junction tables with correct FKs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_labels (
                task_id TEXT NOT NULL,
                label_id TEXT NOT NULL,
                PRIMARY KEY (task_id, label_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_contexts (
                task_id TEXT NOT NULL,
                context_id TEXT NOT NULL,
                PRIMARY KEY (task_id, context_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (context_id) REFERENCES contexts(id) ON DELETE CASCADE
            )
        """)

        print("Updating schema version...")

        # Update schema version
        cursor.execute(
            "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
            (MIGRATION_VERSION,),
        )

        # Commit transaction
        connection.commit()

        print(f"\n✅ Migration to schema v{MIGRATION_VERSION} completed successfully!")
        print(
            f"   Labels: {labels_migrated}, Contexts: {contexts_migrated}, Tasks: {tasks_migrated}"
        )
        print(f"   Reminders: {reminders_migrated}, Filters: {filters_migrated}")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        connection.rollback()
        return False


def verify_migration(connection):
    """
    Verify migration completed successfully.

    Args:
        connection: sqlite3.Connection object

    Returns:
        bool: True if verification passed
    """
    cursor = connection.cursor()

    try:
        # Check schema version
        cursor.execute("SELECT MAX(version) FROM schema_version")
        version = cursor.fetchone()[0]

        if version != MIGRATION_VERSION:
            print(
                f"❌ Schema version mismatch: expected {MIGRATION_VERSION}, got {version}"
            )
            return False

        # Check new columns exist
        checks = [
            ("labels", ["updated_at", "deleted_at", "version", "color"]),
            ("contexts", ["updated_at", "deleted_at", "version", "color", "icon"]),
            (
                "tasks",
                ["assigned_by_id", "assigned_at", "is_recurring", "estimated_time"],
            ),
            ("reminders", ["is_snoozed", "snoozed_until"]),
            ("filters", ["updated_at"]),
        ]

        for table, columns in checks:
            cursor.execute(f"PRAGMA table_info({table})")
            table_columns = {row[1] for row in cursor.fetchall()}

            for col in columns:
                if col not in table_columns:
                    print(f"❌ Column {table}.{col} not found")
                    return False

        print("✅ Migration verification passed")
        return True

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


# ============================================
# ROLLBACK (if needed)
# ============================================


def rollback_migration(connection):
    """
    Rollback migration from v2 to v1.

    NOTE: This will lose data added to new fields!

    Args:
        connection: sqlite3.Connection object

    Returns:
        bool: True if rollback successful
    """
    # Import v1 schema
    from todopro_cli.adapters.sqlite.schema import (
        ALL_INDEXES,
        CREATE_CONTEXTS_TABLE,
        CREATE_FILTERS_TABLE,
        CREATE_LABELS_TABLE,
        CREATE_REMINDERS_TABLE,
        CREATE_TASK_CONTEXTS_TABLE,
        CREATE_TASK_LABELS_TABLE,
        CREATE_TASKS_TABLE,
    )

    cursor = connection.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION")

        print("WARNING: Rolling back to schema v1. New field data will be lost!")

        # Create v1 tables with temp names
        cursor.execute(CREATE_LABELS_TABLE.replace("labels", "labels_v1"))
        cursor.execute(CREATE_CONTEXTS_TABLE.replace("contexts", "contexts_v1"))
        cursor.execute(CREATE_TASKS_TABLE.replace("tasks", "tasks_v1"))
        cursor.execute(CREATE_REMINDERS_TABLE.replace("reminders", "reminders_v1"))
        cursor.execute(CREATE_FILTERS_TABLE.replace("filters", "filters_v1"))

        # Migrate back (drop new fields)
        cursor.execute("""
            INSERT INTO labels_v1 SELECT id, name, color, user_id, created_at FROM labels
        """)

        cursor.execute("""
            INSERT INTO contexts_v1 
            SELECT id, name, latitude, longitude, radius, user_id, created_at FROM contexts
        """)

        cursor.execute("""
            INSERT INTO tasks_v1 
            SELECT 
                id, content, description, is_completed, due_date, priority,
                project_id, user_id, assigned_to_id, created_at, updated_at,
                completed_at, deleted_at, version, content_encrypted, description_encrypted,
                is_urgent, is_important, recurrence_rule, parent_task_id
            FROM tasks
        """)

        cursor.execute("""
            INSERT INTO reminders_v1 
            SELECT id, task_id, reminder_date, is_sent, created_at FROM reminders
        """)

        cursor.execute("""
            INSERT INTO filters_v1 
            SELECT id, name, query, user_id, created_at FROM filters
        """)

        # Drop v2 tables
        cursor.execute("DROP TABLE task_labels")
        cursor.execute("DROP TABLE task_contexts")
        cursor.execute("DROP TABLE tasks")
        cursor.execute("DROP TABLE reminders")
        cursor.execute("DROP TABLE filters")
        cursor.execute("DROP TABLE labels")
        cursor.execute("DROP TABLE contexts")

        # Rename v1 tables back
        cursor.execute("ALTER TABLE labels_v1 RENAME TO labels")
        cursor.execute("ALTER TABLE contexts_v1 RENAME TO contexts")
        cursor.execute("ALTER TABLE tasks_v1 RENAME TO tasks")
        cursor.execute("ALTER TABLE reminders_v1 RENAME TO reminders")
        cursor.execute("ALTER TABLE filters_v1 RENAME TO filters")

        # Recreate junction tables
        cursor.execute(CREATE_TASK_LABELS_TABLE)
        cursor.execute(CREATE_TASK_CONTEXTS_TABLE)

        # Recreate indexes
        for idx in ALL_INDEXES:
            cursor.execute(idx)

        # Update schema version
        cursor.execute(
            "UPDATE schema_version SET version = 1, applied_at = datetime('now') WHERE version = ?",
            (MIGRATION_VERSION,),
        )

        connection.commit()

        print("✅ Rollback to schema v1 completed")
        return True

    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        connection.rollback()
        return False
