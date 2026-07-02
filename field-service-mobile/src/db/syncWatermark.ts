import { getDb } from "./database";
import { v4 as uuidv4 } from "uuid";

function ensureRow(deviceId: string): void {
  const db = getDb();
  db.runSync(
    `INSERT OR IGNORE INTO sync_watermark (id, last_synced_at, device_id)
     VALUES (1, NULL, ?)`,
    [deviceId]
  );
}

export function getDeviceId(): string {
  const db = getDb();
  const row = db.getFirstSync<{ device_id: string }>(
    `SELECT device_id FROM sync_watermark WHERE id = 1`
  );
  if (row) return row.device_id;
  const id = uuidv4();
  ensureRow(id);
  return id;
}

export function getLastSyncedAt(): string | null {
  const db = getDb();
  const row = db.getFirstSync<{ last_synced_at: string | null }>(
    `SELECT last_synced_at FROM sync_watermark WHERE id = 1`
  );
  return row?.last_synced_at ?? null;
}

export function setLastSyncedAt(ts: string): void {
  const db = getDb();
  db.runSync(
    `UPDATE sync_watermark SET last_synced_at = ? WHERE id = 1`,
    [ts]
  );
}
