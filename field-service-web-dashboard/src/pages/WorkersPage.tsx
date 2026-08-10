import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus, Copy, Check } from "lucide-react";
import { register } from "../services/auth";
import { getWorkers } from "../services/users";
import type { RegisterPayload } from "../types";
import { format } from "date-fns";

export function WorkersPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [form, setForm] = useState({ email: "", full_name: "", password: "Password1" });

  const { data: workers = [], isLoading } = useQuery({
    queryKey: ["workers"],
    queryFn: getWorkers,
  });

  const createMutation = useMutation({
    mutationFn: (payload: RegisterPayload) => register(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workers"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
      setShowCreate(false);
      setForm({ email: "", full_name: "", password: "Password1" });
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({ ...form, role: "field_worker" });
  };

  const copyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Workers</h1>
          <p className="mt-0.5 text-sm text-gray-500">{workers.length} registered</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
        >
          <UserPlus className="h-4 w-4" />
          Add Worker
        </button>
      </div>

      <div className="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-gray-200">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <div className="h-7 w-7 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
          </div>
        ) : workers.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-sm text-gray-400">No workers registered yet.</p>
            <button
              onClick={() => setShowCreate(true)}
              className="mt-3 text-sm font-medium text-brand-600 hover:underline"
            >
              Add the first worker →
            </button>
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-100 bg-gray-50">
              <tr>
                <th className="px-5 py-3.5 font-medium text-gray-500">Name</th>
                <th className="hidden px-5 py-3.5 font-medium text-gray-500 md:table-cell">Email</th>
                <th className="px-5 py-3.5 font-medium text-gray-500">Worker ID</th>
                <th className="hidden px-5 py-3.5 font-medium text-gray-500 lg:table-cell">Registered</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {workers.map((w) => (
                <tr key={w.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
                        {w.full_name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{w.full_name}</p>
                        <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                          {w.is_active ? "Active" : "Inactive"}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="hidden px-5 py-3.5 text-gray-500 md:table-cell">{w.email}</td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <code className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                        {w.id.slice(0, 8)}…
                      </code>
                      <button
                        onClick={() => copyId(w.id)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                        title="Copy full ID"
                      >
                        {copied === w.id ? (
                          <Check className="h-3.5 w-3.5 text-green-500" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                  </td>
                  <td className="hidden px-5 py-3.5 text-gray-400 lg:table-cell">
                    {format(new Date(w.created_at), "dd MMM yyyy")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h2 className="mb-5 text-lg font-bold text-gray-900">Add Field Worker</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Full Name *</label>
                <input
                  required
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  placeholder="e.g. Arben Krasniqi"
                  className="w-full rounded-lg border border-gray-300 px-3.5 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Email *</label>
                <input
                  required
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="worker@company.com"
                  className="w-full rounded-lg border border-gray-300 px-3.5 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Password *</label>
                <input
                  required
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3.5 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
                <p className="mt-1 text-xs text-gray-400">Min 8 chars, 1 uppercase, 1 number.</p>
              </div>

              {createMutation.isError && (
                <p className="rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-600">
                  Failed to create worker. Email may already be taken.
                </p>
              )}

              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="flex-1 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
                >
                  {createMutation.isPending ? "Creating…" : "Create Worker"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
