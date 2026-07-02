import { api } from "./api";
import type { Photo } from "../types";

export async function getPhotosByTask(taskId: string): Promise<Photo[]> {
  const { data } = await api.get<Photo[]>(`/photos/task/${taskId}`);
  return data;
}

export async function fetchPhotoBlob(photoId: string): Promise<string> {
  const { data } = await api.get<Blob>(`/photos/${photoId}/file`, {
    responseType: "blob",
  });
  return URL.createObjectURL(data);
}
