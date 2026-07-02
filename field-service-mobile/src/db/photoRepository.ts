import { getDb } from "./database";
import type { LocalPhoto } from "../types";

function now(): string {
  return new Date().toISOString();
}

export function getPhotosByReportClientId(reportClientId: string): LocalPhoto[] {
  const db = getDb();
  return db.getAllSync<LocalPhoto>(
    `SELECT * FROM photos WHERE report_client_id = ? ORDER BY client_created_at ASC`,
    [reportClientId]
  );
}

export function getPendingSyncPhotos(): LocalPhoto[] {
  const db = getDb();
  return db.getAllSync<LocalPhoto>(
    `SELECT * FROM photos WHERE sync_state = 'pending_sync'`
  );
}

export function getPhotosPendingUpload(): LocalPhoto[] {
  const db = getDb();
  return db.getAllSync<LocalPhoto>(
    `SELECT * FROM photos WHERE uploaded = 0 AND sync_state = 'synced'`
  );
}

export function insertPhoto(photo: {
  client_id: string;
  task_client_id: string;
  report_client_id: string;
  local_uri: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_checksum: string;
}): LocalPhoto {
  const db = getDb();
  const ts = now();
  db.runSync(
    `INSERT INTO photos
       (id, client_id, task_client_id, report_client_id, local_uri,
        original_filename, mime_type, file_size_bytes, sha256_checksum,
        client_created_at, uploaded, sync_state)
     VALUES ('', ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'pending_sync')`,
    [
      photo.client_id,
      photo.task_client_id,
      photo.report_client_id,
      photo.local_uri,
      photo.original_filename,
      photo.mime_type,
      photo.file_size_bytes,
      photo.sha256_checksum,
      ts,
    ]
  );
  return db.getFirstSync<LocalPhoto>(
    `SELECT * FROM photos WHERE client_id = ?`,
    [photo.client_id]
  )!;
}

export function markPhotoSynced(clientId: string, serverId: string): void {
  if (!serverId) return;
  const db = getDb();
  db.runSync(
    `UPDATE photos SET id = ?, sync_state = 'synced' WHERE client_id = ?`,
    [serverId, clientId]
  );
}

export function markPhotoUploaded(clientId: string): void {
  const db = getDb();
  db.runSync(
    `UPDATE photos SET uploaded = 1 WHERE client_id = ?`,
    [clientId]
  );
}

export function upsertPhotoFromServer(photo: {
  id: string;
  client_id: string;
  task_client_id?: string;
  report_id: string | null;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_checksum: string;
  client_created_at: string;
  created_at: string;
}): void {
  const db = getDb();
  db.runSync(
    `INSERT INTO photos
       (id, client_id, task_client_id, report_client_id, local_uri,
        original_filename, mime_type, file_size_bytes, sha256_checksum,
        client_created_at, uploaded, sync_state)
     VALUES (?, ?, '', ?, '', ?, ?, ?, ?, ?, 1, 'synced')
     ON CONFLICT(client_id) DO UPDATE SET
       id = excluded.id,
       sync_state = 'synced',
       uploaded = 1
     WHERE sync_state != 'pending_sync'`,
    [
      photo.id,
      photo.client_id,
      photo.report_id ?? "",
      photo.original_filename,
      photo.mime_type,
      photo.file_size_bytes,
      photo.sha256_checksum,
      photo.client_created_at,
    ]
  );
}
