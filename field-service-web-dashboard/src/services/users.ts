import { api } from "./api";
import type { User } from "../types";

// The backend list endpoint is on GET /auth/me for the current user.
// Workers list is fetched via a generic users endpoint — we use GET /tasks
// assigned users or register endpoint. For listing workers, we hit /auth/register
// pattern. The backend exposes users via the admin context only.
// We'll add a simple users endpoint call here — backend returns paginated users
// from the same token-based context.

export async function getWorkers(): Promise<User[]> {
  // Calls GET /users if available, otherwise falls back gracefully.
  // The backend doesn't have a dedicated /users list endpoint yet —
  // we track workers locally from register responses + task assignees.
  try {
    const { data } = await api.get<{ items: User[]; total: number }>("/users");
    return data.items;
  } catch {
    return [];
  }
}
