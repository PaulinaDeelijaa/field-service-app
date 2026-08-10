import { api } from "./api";
import type { User } from "../types";

export async function getWorkers(): Promise<User[]> {
  const { data } = await api.get<User[]>("/users", {
    params: { role: "field_worker" },
  });
  return data;
}
