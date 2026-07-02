import * as SQLite from "expo-sqlite";

let _db: SQLite.SQLiteDatabase | null = null;

export function getDb(): SQLite.SQLiteDatabase {
  if (!_db) {
    _db = SQLite.openDatabaseSync("field_service.db");
  }
  return _db;
}

/**
 * Run all CREATE TABLE / ALTER TABLE statements at app startup.
 * This is idempotent — safe to call on every launch.
 */
export function initDatabase(): void {
  const db = getDb();

  db.execSync(`PRAGMA journal_mode = WAL;`);
  db.execSync(`PRAGMA foreign_keys = ON;`);

  // ── tasks ──────────────────────────────────────────────────────────────────
  db.execSync(`
    CREATE TABLE IF NOT EXISTS tasks (
      id                TEXT NOT NULL DEFAULT '',
      client_id         TEXT NOT NULL PRIMARY KEY,
      title             TEXT NOT NULL,
      description       TEXT,
      status            TEXT NOT NULL DEFAULT 'pending',
      priority          TEXT NOT NULL DEFAULT 'medium',
      assigned_to_id    TEXT,
      location_address  TEXT,
      location_lat      REAL,
      location_lng      REAL,
      scheduled_at      TEXT,
      started_at        TEXT,
      completed_at      TEXT,
      deleted_at        TEXT,
      server_version    INTEGER NOT NULL DEFAULT 0,
      client_updated_at TEXT NOT NULL,
      sync_state        TEXT NOT NULL DEFAULT 'pending_sync',
      created_at        TEXT NOT NULL,
      updated_at        TEXT NOT NULL
    );
  `);

  db.execSync(`
    CREATE INDEX IF NOT EXISTS ix_tasks_status
    ON tasks (status);
  `);

  db.execSync(`
    CREATE INDEX IF NOT EXISTS ix_tasks_sync_state
    ON tasks (sync_state);
  `);

  // ── reports ────────────────────────────────────────────────────────────────
  db.execSync(`
    CREATE TABLE IF NOT EXISTS reports (
      id                  TEXT NOT NULL DEFAULT '',
      client_id           TEXT NOT NULL PRIMARY KEY,
      task_id             TEXT NOT NULL DEFAULT '',
      task_client_id      TEXT NOT NULL,
      worker_id           TEXT NOT NULL DEFAULT '',
      content             TEXT NOT NULL,
      materials_used      TEXT,
      time_spent_minutes  INTEGER,
      server_version      INTEGER NOT NULL DEFAULT 0,
      client_updated_at   TEXT NOT NULL,
      sync_state          TEXT NOT NULL DEFAULT 'pending_sync',
      created_at          TEXT NOT NULL,
      updated_at          TEXT NOT NULL
    );
  `);

  // ── photos ─────────────────────────────────────────────────────────────────
  db.execSync(`
    CREATE TABLE IF NOT EXISTS photos (
      id                  TEXT NOT NULL DEFAULT '',
      client_id           TEXT NOT NULL PRIMARY KEY,
      task_client_id      TEXT NOT NULL,
      report_client_id    TEXT,
      local_uri           TEXT NOT NULL,
      original_filename   TEXT NOT NULL,
      mime_type           TEXT NOT NULL DEFAULT 'image/jpeg',
      file_size_bytes     INTEGER NOT NULL DEFAULT 0,
      sha256_checksum     TEXT NOT NULL DEFAULT '',
      client_created_at   TEXT NOT NULL,
      uploaded            INTEGER NOT NULL DEFAULT 0,
      sync_state          TEXT NOT NULL DEFAULT 'pending_sync'
    );
  `);

  // ── sync_watermark ─────────────────────────────────────────────────────────
  // Single-row table that stores the last server_timestamp we synced against.
  db.execSync(`
    CREATE TABLE IF NOT EXISTS sync_watermark (
      id              INTEGER PRIMARY KEY CHECK (id = 1),
      last_synced_at  TEXT,
      device_id       TEXT NOT NULL
    );
  `);
}
