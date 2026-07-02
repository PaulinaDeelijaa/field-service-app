import { getDb } from "./database";
import type { LocalTask, TaskStatus } from "../types";

function now(): string {
  return new Date().toISOString();
}

export function getAllTasks(): LocalTask[] {
  const db = getDb();
  return db.getAllSync<LocalTask>(
    `SELECT * FROM tasks WHERE deleted_at IS NULL ORDER BY
     CASE status WHEN 'in_progress' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END,
     scheduled_at ASC NULLS LAST,
     created_at DESC`
  );
}

export function getTaskByClientId(clientId: string): LocalTask | null {
  const db = getDb();
  return db.getFirstSync<LocalTask>(
    `SELECT * FROM tasks WHERE client_id = ?`,
    [clientId]
  ) ?? null;
}

export function getTasksByStatus(status: TaskStatus): LocalTask[] {
  const db = getDb();
  return db.getAllSync<LocalTask>(
    `SELECT * FROM tasks WHERE status = ? AND deleted_at IS NULL`,
    [status]
  );
}

export function getPendingSyncTasks(): LocalTask[] {
  const db = getDb();
  return db.getAllSync<LocalTask>(
    `SELECT * FROM tasks WHERE sync_state = 'pending_sync'`
  );
}

export function upsertTaskFromServer(task: {
  id: string;
  client_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: string;
  assigned_to_id: string | null;
  location_address: string | null;
  location_lat: number | null;
  location_lng: number | null;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  deleted_at: string | null;
  server_version: number;
  updated_at: string;
  created_at: string;
}): void {
  const db = getDb();
  db.runSync(
    `INSERT INTO tasks (
        id, client_id, title, description, status, priority,
        assigned_to_id, location_address, location_lat, location_lng,
        scheduled_at, started_at, completed_at, deleted_at,
        server_version, client_updated_at, sync_state, created_at, updated_at
      ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(client_id) DO UPDATE SET
        id               = excluded.id,
        title            = excluded.title,
        description      = excluded.description,
        status           = excluded.status,
        priority         = excluded.priority,
        assigned_to_id   = excluded.assigned_to_id,
        location_address = excluded.location_address,
        location_lat     = excluded.location_lat,
        location_lng     = excluded.location_lng,
        scheduled_at     = excluded.scheduled_at,
        started_at       = excluded.started_at,
        completed_at     = excluded.completed_at,
        deleted_at       = excluded.deleted_at,
        server_version   = excluded.server_version,
        sync_state       = 'synced',
        updated_at       = excluded.updated_at
      WHERE sync_state != 'pending_sync'`,
    [
      task.id,
      task.client_id,
      task.title,
      task.description,
      task.status,
      task.priority,
      task.assigned_to_id,
      task.location_address,
      task.location_lat,
      task.location_lng,
      task.scheduled_at,
      task.started_at,
      task.completed_at,
      task.deleted_at,
      task.server_version,
      task.updated_at,
      "synced",
      task.created_at,
      task.updated_at,
    ]
  );
}

export function updateTaskStatus(
  clientId: string,
  status: TaskStatus,
  extra?: { started_at?: string; completed_at?: string }
): void {
  const db = getDb();
  const ts = now();
  db.runSync(
    `UPDATE tasks SET
       status           = ?,
       started_at       = COALESCE(?, started_at),
       completed_at     = COALESCE(?, completed_at),
       client_updated_at = ?,
       sync_state        = 'pending_sync',
       updated_at        = ?
     WHERE client_id = ?`,
    [
      status,
      extra?.started_at ?? null,
      extra?.completed_at ?? null,
      ts,
      ts,
      clientId,
    ]
  );
}

export function markTaskSynced(clientId: string, serverId: string, serverVersion: number): void {
  const db = getDb();
  db.runSync(
    `UPDATE tasks SET id = ?, server_version = ?, sync_state = 'synced' WHERE client_id = ?`,
    [serverId, serverVersion, clientId]
  );
}
