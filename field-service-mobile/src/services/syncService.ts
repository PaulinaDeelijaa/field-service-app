/**
 * Bidirectional sync engine.
 *
 * Flow:
 * 1. Check connectivity — abort silently if offline.
 * 2. Collect all locally-modified records (sync_state = 'pending_sync').
 * 3. POST /sync with the pending payload + last_synced_at watermark.
 * 4. Merge the server delta into local SQLite (upsert on client_id).
 * 5. Upload photo binaries for synced metadata.
 * 6. Mark sent records as 'synced'. Update watermark.
 */

import NetInfo from "@react-native-community/netinfo";
import { api } from "./api";
import {
  getPendingSyncTasks,
  upsertTaskFromServer,
  markTaskSynced,
} from "../db/taskRepository";
import {
  getPendingSyncReports,
  getReportByClientId,
  markReportSynced,
} from "../db/reportRepository";
import {
  getPendingSyncPhotos,
  getPhotosPendingUpload,
  markPhotoSynced,
  markPhotoUploaded,
  upsertPhotoFromServer,
} from "../db/photoRepository";
import {
  getDeviceId,
  getLastSyncedAt,
  setLastSyncedAt,
} from "../db/syncWatermark";
import { uploadPhotoFile } from "./photoService";
import type { SyncResponse } from "../types";

export type SyncResult = {
  success: boolean;
  tasksReceived: number;
  conflictsDetected: number;
  error?: string;
};

export async function runSync(): Promise<SyncResult> {
  const net = await NetInfo.fetch();
  if (!net.isConnected) {
    return { success: false, tasksReceived: 0, conflictsDetected: 0, error: "offline" };
  }

  try {
    const deviceId = getDeviceId();
    const lastSyncedAt = getLastSyncedAt();

    const pendingTasks = getPendingSyncTasks();
    const pendingReports = getPendingSyncReports();
    const pendingPhotos = getPendingSyncPhotos();

    const taskPayloads = pendingTasks.map((t) => ({
      client_id: t.client_id,
      title: t.title,
      description: t.description,
      status: t.status,
      priority: t.priority,
      assigned_to_id: t.assigned_to_id,
      location_address: t.location_address,
      location_lat: t.location_lat,
      location_lng: t.location_lng,
      scheduled_at: t.scheduled_at,
      started_at: t.started_at,
      completed_at: t.completed_at,
      client_updated_at: t.client_updated_at,
      client_version: t.server_version,
    }));

    const reportPayloads = pendingReports.map((r) => ({
      client_id: r.client_id,
      task_client_id: r.task_client_id,
      content: r.content,
      materials_used: r.materials_used ? JSON.parse(r.materials_used) : null,
      time_spent_minutes: r.time_spent_minutes,
      client_updated_at: r.client_updated_at,
      client_version: r.server_version,
    }));

    const photoPayloads = pendingPhotos.map((p) => ({
      client_id: p.client_id,
      task_client_id: p.task_client_id,
      report_client_id: p.report_client_id,
      original_filename: p.original_filename,
      mime_type: p.mime_type,
      file_size_bytes: p.file_size_bytes,
      sha256_checksum: p.sha256_checksum,
      client_created_at: p.client_created_at,
    }));

    const { data: response } = await api.post<SyncResponse>("/sync", {
      device_id: deviceId,
      last_synced_at: lastSyncedAt,
      tasks: taskPayloads,
      reports: reportPayloads,
      photos: photoPayloads,
    });

    for (const task of response.tasks) {
      upsertTaskFromServer(task);
    }

    for (const report of response.reports) {
      markReportSynced(report.client_id, report.id);
    }

    for (const photo of response.photos) {
      upsertPhotoFromServer(photo);
    }

    for (const task of pendingTasks) {
      const serverTask = response.tasks.find((t) => t.client_id === task.client_id);
      if (serverTask) {
        markTaskSynced(task.client_id, serverTask.id, serverTask.server_version);
      } else if (task.id) {
        markTaskSynced(task.client_id, task.id, task.server_version);
      }
    }

    for (const report of pendingReports) {
      const serverReport = response.reports.find((r) => r.client_id === report.client_id);
      if (serverReport) {
        markReportSynced(report.client_id, serverReport.id);
      }
    }

    for (const photo of pendingPhotos) {
      const serverPhoto = response.photos.find((p) => p.client_id === photo.client_id);
      if (serverPhoto) {
        markPhotoSynced(photo.client_id, serverPhoto.id);
      }
    }

    await uploadPendingPhotoFiles();

    setLastSyncedAt(response.server_timestamp);

    return {
      success: true,
      tasksReceived: response.stats.tasks_sent,
      conflictsDetected: response.stats.conflicts_detected,
    };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Unknown sync error";
    return {
      success: false,
      tasksReceived: 0,
      conflictsDetected: 0,
      error: msg,
    };
  }
}

async function uploadPendingPhotoFiles(): Promise<void> {
  const photos = getPhotosPendingUpload();

  for (const photo of photos) {
    if (!photo.report_client_id) continue;

    const report = getReportByClientId(photo.report_client_id);
    if (!report?.id) continue;

    try {
      await uploadPhotoFile(report.id, photo);
      markPhotoUploaded(photo.client_id);
    } catch {
      // Keep for retry on next sync.
    }
  }
}
