import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, useRouter, useFocusEffect } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { format } from "date-fns";
import {
  getTaskByClientId,
  updateTaskStatus,
} from "../../../src/db/taskRepository";
import { getReportsByTaskClientId } from "../../../src/db/reportRepository";
import { StatusBadge, SyncBadge } from "../../../src/components/StatusBadge";
import { PriorityIndicator } from "../../../src/components/PriorityIndicator";
import { useSync } from "../../../src/hooks/useSync";
import type { LocalTask, LocalReport, TaskStatus } from "../../../src/types";

const PRIORITY_LABELS: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export default function TaskDetailScreen() {
  const { clientId } = useLocalSearchParams<{ clientId: string }>();
  const router = useRouter();
  const { sync } = useSync();

  const [task, setTask] = useState<LocalTask | null>(null);
  const [reports, setReports] = useState<LocalReport[]>([]);
  const [actionLoading, setActionLoading] = useState(false);

  const reload = useCallback(() => {
    if (!clientId) return;
    setTask(getTaskByClientId(clientId));
    setReports(getReportsByTaskClientId(clientId));
  }, [clientId]);

  useFocusEffect(
    useCallback(() => {
      reload();
    }, [reload])
  );

  if (!task) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    );
  }

  const canStart = task.status === "pending";
  const canComplete = task.status === "in_progress";
  const isTerminal = task.status === "completed" || task.status === "cancelled";

  const handleStatusChange = async (nextStatus: TaskStatus) => {
    const now = new Date().toISOString();
    const extra: { started_at?: string; completed_at?: string } = {};
    if (nextStatus === "in_progress") extra.started_at = now;
    if (nextStatus === "completed") extra.completed_at = now;

    Alert.alert(
      "Confirm",
      `Set task to "${nextStatus.replace("_", " ")}"?`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Confirm",
          onPress: async () => {
            setActionLoading(true);
            updateTaskStatus(task.client_id, nextStatus, extra);
            reload();
            await sync();
            reload();
            setActionLoading(false);
          },
        },
      ]
    );
  };

  const formattedDate = (iso: string | null) =>
    iso ? format(new Date(iso), "dd MMM yyyy, HH:mm") : "—";

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Text style={styles.backText}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>
          Task Detail
        </Text>
        <View style={{ width: 60 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {/* Title + status */}
        <View style={styles.card}>
          <View style={styles.titleRow}>
            <PriorityIndicator priority={task.priority} />
            <Text style={styles.title}>{task.title}</Text>
          </View>
          <View style={styles.badgeRow}>
            <StatusBadge status={task.status} />
            <SyncBadge state={task.sync_state} />
          </View>
        </View>

        {/* Details grid */}
        <View style={styles.card}>
          <DetailRow label="Priority" value={PRIORITY_LABELS[task.priority] ?? task.priority} />
          <DetailRow label="Scheduled" value={formattedDate(task.scheduled_at)} />
          <DetailRow label="Started" value={formattedDate(task.started_at)} />
          <DetailRow label="Completed" value={formattedDate(task.completed_at)} />
          {task.location_address ? (
            <DetailRow label="Location" value={task.location_address} />
          ) : null}
        </View>

        {/* Description */}
        {task.description ? (
          <View style={styles.card}>
            <Text style={styles.sectionLabel}>Description</Text>
            <Text style={styles.description}>{task.description}</Text>
          </View>
        ) : null}

        {/* Action buttons */}
        {!isTerminal && (
          <View style={styles.actionRow}>
            {canStart && (
              <ActionButton
                label="▶  Start Task"
                color="#2563eb"
                loading={actionLoading}
                onPress={() => handleStatusChange("in_progress")}
              />
            )}
            {canComplete && (
              <>
                <ActionButton
                  label="✓  Mark Complete"
                  color="#059669"
                  loading={actionLoading}
                  onPress={() => handleStatusChange("completed")}
                />
                <ActionButton
                  label="📝  Submit Report"
                  color="#7c3aed"
                  loading={false}
                  onPress={() =>
                    router.push({
                      pathname: "/(app)/task/[clientId]/report",
                      params: { clientId: task.client_id },
                    })
                  }
                />
              </>
            )}
          </View>
        )}

        {/* Reports */}
        <Text style={styles.sectionLabel}>Reports ({reports.length})</Text>
        {reports.length === 0 ? (
          <View style={styles.emptyReports}>
            <Text style={styles.emptyReportsText}>No reports submitted yet</Text>
          </View>
        ) : (
          reports.map((r) => <ReportCard key={r.client_id} report={r} />)
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{value}</Text>
    </View>
  );
}

function ActionButton({
  label,
  color,
  loading,
  onPress,
}: {
  label: string;
  color: string;
  loading: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={[styles.actionBtn, { backgroundColor: color }, loading && styles.btnDisabled]}
      onPress={onPress}
      disabled={loading}
      activeOpacity={0.85}
    >
      {loading ? (
        <ActivityIndicator color="#fff" size="small" />
      ) : (
        <Text style={styles.actionBtnText}>{label}</Text>
      )}
    </TouchableOpacity>
  );
}

function ReportCard({ report }: { report: LocalReport }) {
  return (
    <View style={styles.reportCard}>
      <Text style={styles.reportContent}>{report.content}</Text>
      {report.time_spent_minutes ? (
        <Text style={styles.reportMeta}>
          ⏱ {report.time_spent_minutes} min
        </Text>
      ) : null}
      <View style={styles.reportFooter}>
        <Text style={styles.reportDate}>
          {format(new Date(report.created_at), "dd MMM, HH:mm")}
        </Text>
        <SyncBadge state={report.sync_state} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f9fafb" },
  centered: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#2563eb",
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  backBtn: { width: 60 },
  backText: { color: "#bfdbfe", fontSize: 15 },
  headerTitle: { color: "#fff", fontSize: 17, fontWeight: "700", flex: 1, textAlign: "center" },
  content: { padding: 16, gap: 12 },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
    gap: 8,
  },
  titleRow: { flexDirection: "row", alignItems: "flex-start", gap: 8 },
  title: { flex: 1, fontSize: 17, fontWeight: "700", color: "#111827" },
  badgeRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  detailRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  detailLabel: { fontSize: 13, color: "#6b7280" },
  detailValue: { fontSize: 13, fontWeight: "500", color: "#111827", flex: 1, textAlign: "right" },
  sectionLabel: { fontSize: 14, fontWeight: "700", color: "#374151", marginTop: 4 },
  description: { fontSize: 14, color: "#374151", lineHeight: 21 },
  actionRow: { gap: 10 },
  actionBtn: {
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
  },
  btnDisabled: { opacity: 0.6 },
  actionBtnText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  emptyReports: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 20,
    alignItems: "center",
  },
  emptyReportsText: { color: "#9ca3af", fontSize: 14 },
  reportCard: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    gap: 6,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 1,
  },
  reportContent: { fontSize: 14, color: "#374151", lineHeight: 20 },
  reportMeta: { fontSize: 12, color: "#6b7280" },
  reportFooter: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  reportDate: { fontSize: 12, color: "#9ca3af" },
});
