export type UserRole = "manager" | "field_worker";
export type TaskStatus = "pending" | "in_progress" | "completed" | "cancelled";
export type TaskPriority = "low" | "medium" | "high" | "critical";
export type SyncState = "synced" | "pending_sync" | "conflict";

// ── Local DB row shapes ────────────────────────────────────────────────────

export interface LocalTask {
  id: string;               // server UUID (empty string until first sync)
  client_id: string;        // device-generated UUID — permanent idempotency key
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_to_id: string | null;
  location_address: string | null;
  location_lat: number | null;
  location_lng: number | null;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  deleted_at: string | null;
  server_version: number;
  client_updated_at: string; // ISO — device clock at last local write
  sync_state: SyncState;
  created_at: string;
  updated_at: string;
}

export interface LocalReport {
  id: string;
  client_id: string;
  task_id: string;          // server task UUID
  task_client_id: string;   // client task UUID — used when server ID not yet known
  worker_id: string;
  content: string;
  materials_used: string | null;  // JSON string stored in SQLite
  time_spent_minutes: number | null;
  server_version: number;
  client_updated_at: string;
  sync_state: SyncState;
  created_at: string;
  updated_at: string;
}

export interface LocalPhoto {
  id: string;
  client_id: string;
  task_client_id: string;
  report_client_id: string | null;
  local_uri: string;        // file:// path on device
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_checksum: string;
  client_created_at: string;
  uploaded: number;         // 0 | 1 (SQLite boolean)
  sync_state: SyncState;
}

// ── API response shapes ────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export interface ApiTask {
  id: string;
  client_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_to_id: string | null;
  location_address: string | null;
  location_lat: number | null;
  location_lng: number | null;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  deleted_at: string | null;
  server_version: number;
  created_at: string;
  updated_at: string;
}

export interface ApiReport {
  id: string;
  client_id: string;
  task_id: string;
  worker_id: string;
  content: string;
  materials_used: { name: string; quantity: string }[] | null;
  time_spent_minutes: number | null;
  server_version: number;
  created_at: string;
  updated_at: string;
}

export interface ApiPhoto {
  id: string;
  client_id: string;
  task_id: string;
  report_id: string | null;
  original_filename: string;
  file_path: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_checksum: string;
  client_created_at: string;
  created_at: string;
}

export interface ConflictDetail {
  entity_type: "task" | "report";
  client_id: string;
  server_id: string;
  resolution: string;
  server_version: number;
}

export interface SyncResponse {
  server_timestamp: string;
  tasks: ApiTask[];
  reports: ApiReport[];
  photos: ApiPhoto[];
  conflicts: ConflictDetail[];
  stats: SyncStats;
}

export interface SyncStats {
  tasks_received: number;
  tasks_sent: number;
  reports_received: number;
  reports_sent: number;
  photos_received: number;
  photos_sent: number;
  conflicts_detected: number;
}
