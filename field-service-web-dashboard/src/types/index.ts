export type UserRole = "manager" | "field_worker";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type TaskStatus = "pending" | "in_progress" | "completed" | "cancelled";
export type TaskPriority = "low" | "medium" | "high" | "critical";

export interface Task {
  id: string;
  client_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_to_id: string | null;
  created_by_id: string;
  location_lat: number | null;
  location_lng: number | null;
  location_address: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  deleted_at: string | null;
  server_version: number;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
}

export interface Report {
  id: string;
  client_id: string;
  task_id: string;
  worker_id: string;
  content: string;
  materials_used: { name: string; quantity: number | string; unit?: string }[] | null;
  time_spent_minutes: number | null;
  server_version: number;
  created_at: string;
  updated_at: string;
}

export interface Photo {
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

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface CreateTaskPayload {
  client_id: string;
  title: string;
  description?: string;
  priority: TaskPriority;
  assigned_to_id?: string;
  location_lat?: number;
  location_lng?: number;
  location_address?: string;
  scheduled_at?: string;
}

export interface UpdateTaskPayload {
  expected_version: number;
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  assigned_to_id?: string;
  location_address?: string;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
}

export interface RegisterPayload {
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
}
