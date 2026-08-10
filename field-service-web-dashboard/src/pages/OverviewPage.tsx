import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getTasks } from "../services/tasks";
import { ClipboardList, Clock, CheckCircle, AlertTriangle } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

function StatCard({ label, count, icon: Icon, color, bg }: { label: string; count: number; icon: React.ElementType; color: string; bg: string }) {
  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500">{label}</p>
        <div className={`rounded-lg p-2 ${bg}`}>
          <Icon className={`h-5 w-5 ${color}`} />
        </div>
      </div>
      <p className="mt-3 text-3xl font-bold text-gray-900">{count}</p>
    </div>
  );
}

export function OverviewPage() {
  const { user } = useAuth();
  const { data: allTasks } = useQuery({ queryKey: ["tasks"], queryFn: () => getTasks(1, 200) });

  const counts = {
    total: allTasks?.total ?? 0,
    pending: allTasks?.items.filter((t) => t.status === "pending").length ?? 0,
    in_progress: allTasks?.items.filter((t) => t.status === "in_progress").length ?? 0,
    completed: allTasks?.items.filter((t) => t.status === "completed").length ?? 0,
  };

  const recent = allTasks?.items.slice(0, 5) ?? [];

  const priorityBadge: Record<string, string> = {
    low: "bg-gray-100 text-gray-600",
    medium: "bg-blue-100 text-blue-700",
    high: "bg-orange-100 text-orange-700",
    critical: "bg-red-100 text-red-700",
  };

  const statusBadge: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    in_progress: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    cancelled: "bg-gray-100 text-gray-600",
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome, {user?.full_name.split(" ")[0]}
        </h1>
        <p className="mt-1 text-sm text-gray-500">Here's your field operations summary.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total Tasks" count={counts.total} icon={ClipboardList} color="text-brand-600" bg="bg-brand-50" />
        <StatCard label="Pending" count={counts.pending} icon={Clock} color="text-yellow-600" bg="bg-yellow-50" />
        <StatCard label="In Progress" count={counts.in_progress} icon={AlertTriangle} color="text-blue-600" bg="bg-blue-50" />
        <StatCard label="Completed" count={counts.completed} icon={CheckCircle} color="text-green-600" bg="bg-green-50" />
      </div>

      {/* Recent tasks */}
      <div className="rounded-xl bg-white shadow-sm ring-1 ring-gray-200">
        <div className="border-b border-gray-100 px-5 py-4">
          <h2 className="font-semibold text-gray-800">Recent Tasks</h2>
        </div>
        {recent.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-gray-400">No tasks yet.</div>
        ) : (
          <ul className="divide-y divide-gray-50">
            {recent.map((task) => (
              <li key={task.id}>
                <Link
                  to={`/tasks/${task.id}`}
                  className="flex items-center justify-between px-5 py-3.5 hover:bg-gray-50"
                >
                <div>
                  <p className="text-sm font-medium text-gray-900">{task.title}</p>
                  <p className="mt-0.5 text-xs text-gray-400">{task.location_address ?? "No location"}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${priorityBadge[task.priority]}`}>
                    {task.priority}
                  </span>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadge[task.status]}`}>
                    {task.status.replace("_", " ")}
                  </span>
                </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
