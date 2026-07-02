import { api } from "./api";
import type { Report } from "../types";

export async function getReportsByTask(taskId: string): Promise<Report[]> {
  const { data } = await api.get<Report[]>("/reports", {
    params: { task_id: taskId },
  });
  return data;
}
