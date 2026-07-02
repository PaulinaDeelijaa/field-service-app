import { getDb } from "./database";
import type { LocalReport } from "../types";

function now(): string {
  return new Date().toISOString();
}

export function getReportByClientId(clientId: string): LocalReport | null {
  const db = getDb();
  return (
    db.getFirstSync<LocalReport>(
      `SELECT * FROM reports WHERE client_id = ?`,
      [clientId]
    ) ?? null
  );
}

export function getReportsByTaskClientId(taskClientId: string): LocalReport[] {
  const db = getDb();
  return db.getAllSync<LocalReport>(
    `SELECT * FROM reports WHERE task_client_id = ? ORDER BY created_at DESC`,
    [taskClientId]
  );
}

export function getPendingSyncReports(): LocalReport[] {
  const db = getDb();
  return db.getAllSync<LocalReport>(
    `SELECT * FROM reports WHERE sync_state = 'pending_sync'`
  );
}

export function insertReport(report: {
  client_id: string;
  task_client_id: string;
  task_id: string;
  worker_id: string;
  content: string;
  materials_used: string | null;
  time_spent_minutes: number | null;
}): LocalReport {
  const db = getDb();
  const ts = now();
  db.runSync(
    `INSERT INTO reports
       (id, client_id, task_id, task_client_id, worker_id, content,
        materials_used, time_spent_minutes, server_version,
        client_updated_at, sync_state, created_at, updated_at)
     VALUES ('', ?, ?, ?, ?, ?, ?, ?, 0, ?, 'pending_sync', ?, ?)`,
    [
      report.client_id,
      report.task_id,
      report.task_client_id,
      report.worker_id,
      report.content,
      report.materials_used,
      report.time_spent_minutes,
      ts,
      ts,
      ts,
    ]
  );
  return db.getFirstSync<LocalReport>(
    `SELECT * FROM reports WHERE client_id = ?`,
    [report.client_id]
  )!;
}

export function markReportSynced(clientId: string, serverId: string): void {
  if (!serverId) return;
  const db = getDb();
  db.runSync(
    `UPDATE reports SET id = ?, sync_state = 'synced' WHERE client_id = ?`,
    [serverId, clientId]
  );
}
