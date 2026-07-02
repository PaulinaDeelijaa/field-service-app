import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getTask, updateTask } from "../services/tasks";
import { getReportsByTask } from "../services/reports";
import { getPhotosByTask } from "../services/photos";
import { AuthenticatedPhoto } from "../components/AuthenticatedPhoto";
import { ArrowLeft, MapPin, Calendar, Clock, User, AlertTriangle, FileText } from "lucide-react";
import { format } from "date-fns";
import type { TaskStatus, TaskPriority } from "../types";

const priorityBadge: Record<TaskPriority, string> = {
  low: "bg-gray-100 text-gray-600",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};

const statusBadge: Record<TaskStatus, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  in_progress: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-600",
};

function InfoRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 rounded-lg bg-gray-100 p-1.5">
        <Icon className="h-4 w-4 text-gray-500" />
      </div>
      <div>
        <p className="text-xs font-medium text-gray-400">{label}</p>
        <p className="mt-0.5 text-sm text-gray-800">{value}</p>
      </div>
    </div>
  );
}

export function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: task, isLoading } = useQuery({
    queryKey: ["task", id],
    queryFn: () => getTask(id!),
    enabled: !!id,
  });

  const { data: reports = [] } = useQuery({
    queryKey: ["reports", id],
    queryFn: () => getReportsByTask(id!),
    enabled: !!id,
  });

  const { data: photos = [] } = useQuery({
    queryKey: ["photos", id],
    queryFn: () => getPhotosByTask(id!),
    enabled: !!id,
  });

  const updateMutation = useMutation({
    mutationFn: ({ status }: { status: TaskStatus }) =>
      updateTask(id!, { expected_version: task!.server_version, status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["task", id] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-7 w-7 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (!task) {
    return <div className="text-sm text-gray-400">Task not found.</div>;
  }

  const nextStatus: Partial<Record<TaskStatus, TaskStatus>> = {
    pending: "in_progress",
    in_progress: "completed",
  };
  const nextStatusLabel: Partial<Record<TaskStatus, string>> = {
    pending: "Mark In Progress",
    in_progress: "Mark Completed",
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Back */}
      <button
        onClick={() => navigate("/tasks")}
        className="flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-800"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Tasks
      </button>

      {/* Header card */}
      <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-xl font-bold text-gray-900">{task.title}</h1>
            {task.description && (
              <p className="mt-2 text-sm text-gray-500">{task.description}</p>
            )}
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadge[task.status]}`}>
              {task.status.replace("_", " ")}
            </span>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${priorityBadge[task.priority]}`}>
              {task.priority}
            </span>
          </div>
        </div>

        {/* Info rows */}
        <div className="mt-5 grid grid-cols-1 gap-4 border-t border-gray-100 pt-5 sm:grid-cols-2">
          {task.location_address && (
            <InfoRow icon={MapPin} label="Location" value={task.location_address} />
          )}
          {task.scheduled_at && (
            <InfoRow
              icon={Calendar}
              label="Scheduled"
              value={format(new Date(task.scheduled_at), "dd MMM yyyy, HH:mm")}
            />
          )}
          {task.started_at && (
            <InfoRow
              icon={Clock}
              label="Started"
              value={format(new Date(task.started_at), "dd MMM yyyy, HH:mm")}
            />
          )}
          {task.completed_at && (
            <InfoRow
              icon={Clock}
              label="Completed"
              value={format(new Date(task.completed_at), "dd MMM yyyy, HH:mm")}
            />
          )}
          {task.assigned_to_id && (
            <InfoRow icon={User} label="Assigned to" value={task.assigned_to_id.slice(0, 12) + "…"} />
          )}
          <InfoRow icon={AlertTriangle} label="Version" value={`v${task.server_version}`} />
        </div>

        {/* Actions */}
        {nextStatus[task.status] && (
          <div className="mt-5 border-t border-gray-100 pt-5">
            <button
              onClick={() => updateMutation.mutate({ status: nextStatus[task.status]! })}
              disabled={updateMutation.isPending}
              className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {updateMutation.isPending ? "Updating…" : nextStatusLabel[task.status]}
            </button>
          </div>
        )}
      </div>

      {/* Reports */}
      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <div className="mb-4 flex items-center gap-2">
          <FileText className="h-4 w-4 text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-700">
            Field Reports ({reports.length})
          </h2>
        </div>

        {reports.length === 0 ? (
          <p className="text-sm text-gray-400">No reports submitted yet.</p>
        ) : (
          <div className="space-y-4">
            {reports.map((report) => (
              <div key={report.id} className="rounded-lg border border-gray-100 p-4">
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{report.content}</p>
                {report.time_spent_minutes != null && (
                  <p className="mt-2 text-xs text-gray-400">
                    Time spent: {report.time_spent_minutes} min
                  </p>
                )}
                {report.materials_used && report.materials_used.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {report.materials_used.map((m, i) => (
                      <span
                        key={i}
                        className="rounded-full bg-gray-100 px-2.5 py-1 text-xs text-gray-600"
                      >
                        {m.name} × {m.quantity}
                        {m.unit ? ` ${m.unit}` : ""}
                      </span>
                    ))}
                  </div>
                )}
                <p className="mt-2 text-xs text-gray-400">
                  {format(new Date(report.created_at), "dd MMM yyyy, HH:mm")}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Photos */}
      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <h2 className="mb-4 text-sm font-semibold text-gray-700">
          Photos ({photos.filter((p) => !p.file_path.startsWith("pending/")).length})
        </h2>

        {photos.filter((p) => !p.file_path.startsWith("pending/")).length === 0 ? (
          <p className="text-sm text-gray-400">No photos uploaded yet.</p>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {photos
              .filter((p) => !p.file_path.startsWith("pending/"))
              .map((photo) => (
                <AuthenticatedPhoto
                  key={photo.id}
                  photoId={photo.id}
                  alt={photo.original_filename}
                  className="h-32 w-full rounded-lg object-cover"
                />
              ))}
          </div>
        )}
      </div>

      {/* Timestamps */}
      <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Audit</h2>
        <div className="space-y-1 text-xs text-gray-400">
          <p>Created: {format(new Date(task.created_at), "dd MMM yyyy HH:mm:ss")}</p>
          <p>Updated: {format(new Date(task.updated_at), "dd MMM yyyy HH:mm:ss")}</p>
          <p>Task ID: <code className="rounded bg-gray-100 px-1.5 py-0.5 text-gray-600">{task.id}</code></p>
        </div>
      </div>
    </div>
  );
}
