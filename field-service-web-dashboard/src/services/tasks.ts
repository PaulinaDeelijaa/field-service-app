import { api } from "./api";
import type {
  Task,
  TaskListResponse,
  CreateTaskPayload,
  UpdateTaskPayload,
  TaskStatus,
} from "../types";

export async function getTasks(
  page = 1,
  pageSize = 50,
  status?: TaskStatus
): Promise<TaskListResponse> {
  const params: Record<string, unknown> = { page, page_size: pageSize };
  if (status) params.status = status;
  const { data } = await api.get<TaskListResponse>("/tasks", { params });
  return data;
}

export async function getTask(id: string): Promise<Task> {
  const { data } = await api.get<Task>(`/tasks/${id}`);
  return data;
}

export async function createTask(payload: CreateTaskPayload): Promise<Task> {
  const { data } = await api.post<Task>("/tasks", payload);
  return data;
}

export async function updateTask(
  id: string,
  payload: UpdateTaskPayload
): Promise<Task> {
  const { data } = await api.patch<Task>(`/tasks/${id}`, payload);
  return data;
}

export async function deleteTask(id: string): Promise<void> {
  await api.delete(`/tasks/${id}`);
}
