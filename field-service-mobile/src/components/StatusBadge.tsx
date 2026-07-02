import React from "react";
import { View, Text, StyleSheet } from "react-native";
import type { TaskStatus, SyncState } from "../types";

type Props = { status: TaskStatus };

const CONFIG: Record<TaskStatus, { bg: string; text: string; label: string }> = {
  pending:     { bg: "#fef3c7", text: "#92400e", label: "Pending" },
  in_progress: { bg: "#dbeafe", text: "#1e40af", label: "In Progress" },
  completed:   { bg: "#d1fae5", text: "#065f46", label: "Completed" },
  cancelled:   { bg: "#f3f4f6", text: "#6b7280", label: "Cancelled" },
};

export function StatusBadge({ status }: Props) {
  const c = CONFIG[status] ?? CONFIG.pending;
  return (
    <View style={[styles.badge, { backgroundColor: c.bg }]}>
      <Text style={[styles.text, { color: c.text }]}>{c.label}</Text>
    </View>
  );
}

type SyncBadgeProps = { state: SyncState };
const SYNC_CONFIG: Record<SyncState, { text: string; color: string }> = {
  synced:       { text: "Synced", color: "#10b981" },
  pending_sync: { text: "Pending sync", color: "#f59e0b" },
  conflict:     { text: "Conflict", color: "#ef4444" },
};

export function SyncBadge({ state }: SyncBadgeProps) {
  const c = SYNC_CONFIG[state];
  return (
    <Text style={[styles.syncText, { color: c.color }]}>● {c.text}</Text>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: 99,
    paddingHorizontal: 10,
    paddingVertical: 3,
    alignSelf: "flex-start",
  },
  text: { fontSize: 12, fontWeight: "600" },
  syncText: { fontSize: 11, fontWeight: "500" },
});
