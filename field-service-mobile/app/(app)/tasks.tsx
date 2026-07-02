import React, { useState, useCallback, useEffect } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  TextInput,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { useFocusEffect } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuth } from "../../src/contexts/AuthContext";
import { useSync } from "../../src/hooks/useSync";
import { getAllTasks } from "../../src/db/taskRepository";
import { StatusBadge, SyncBadge } from "../../src/components/StatusBadge";
import { PriorityIndicator } from "../../src/components/PriorityIndicator";
import type { LocalTask, TaskStatus } from "../../src/types";
import { format } from "date-fns";

const STATUS_FILTERS: { label: string; value: TaskStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Pending", value: "pending" },
  { label: "In Progress", value: "in_progress" },
  { label: "Completed", value: "completed" },
];

export default function TasksScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { status: syncStatus, sync } = useSync();

  const [tasks, setTasks] = useState<LocalTask[]>([]);
  const [filter, setFilter] = useState<TaskStatus | "all">("all");
  const [search, setSearch] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const loadTasks = useCallback(() => {
    const all = getAllTasks();
    setTasks(all);
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadTasks();
    }, [loadTasks])
  );

  // Sync on first mount
  useEffect(() => {
    sync().then(loadTasks);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await sync();
    loadTasks();
    setRefreshing(false);
  };

  const filtered = tasks.filter((t) => {
    const matchStatus = filter === "all" || t.status === filter;
    const matchSearch =
      search.trim() === "" ||
      t.title.toLowerCase().includes(search.toLowerCase()) ||
      (t.location_address ?? "").toLowerCase().includes(search.toLowerCase());
    return matchStatus && matchSearch;
  });

  const renderItem = ({ item }: { item: LocalTask }) => (
    <TouchableOpacity
      style={styles.card}
      activeOpacity={0.8}
      onPress={() =>
        router.push({ pathname: "/(app)/task/[clientId]", params: { clientId: item.client_id } })
      }
    >
      <View style={styles.cardHeader}>
        <PriorityIndicator priority={item.priority} />
        <Text style={styles.cardTitle} numberOfLines={2}>
          {item.title}
        </Text>
        <StatusBadge status={item.status} />
      </View>

      {item.location_address ? (
        <Text style={styles.location} numberOfLines={1}>
          📍 {item.location_address}
        </Text>
      ) : null}

      <View style={styles.cardFooter}>
        {item.scheduled_at ? (
          <Text style={styles.metaText}>
            🗓 {format(new Date(item.scheduled_at), "dd MMM, HH:mm")}
          </Text>
        ) : null}
        <SyncBadge state={item.sync_state} />
      </View>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>My Tasks</Text>
          <Text style={styles.headerSub}>
            {user?.full_name ?? "Field Worker"}
          </Text>
        </View>
        <TouchableOpacity onPress={logout} style={styles.logoutBtn}>
          <Text style={styles.logoutText}>Sign Out</Text>
        </TouchableOpacity>
      </View>

      {/* Sync indicator */}
      {syncStatus === "syncing" && (
        <View style={styles.syncBar}>
          <ActivityIndicator size="small" color="#2563eb" />
          <Text style={styles.syncText}>Syncing…</Text>
        </View>
      )}

      {/* Search */}
      <View style={styles.searchRow}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search tasks…"
          placeholderTextColor="#9ca3af"
          value={search}
          onChangeText={setSearch}
          returnKeyType="search"
        />
      </View>

      {/* Status filter tabs */}
      <View style={styles.filterRow}>
        {STATUS_FILTERS.map((f) => (
          <TouchableOpacity
            key={f.value}
            style={[styles.filterTab, filter === f.value && styles.filterTabActive]}
            onPress={() => setFilter(f.value)}
          >
            <Text
              style={[
                styles.filterTabText,
                filter === f.value && styles.filterTabTextActive,
              ]}
            >
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Task list */}
      <FlatList
        data={filtered}
        keyExtractor={(item) => item.client_id}
        renderItem={renderItem}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={["#2563eb"]}
            tintColor="#2563eb"
          />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>📋</Text>
            <Text style={styles.emptyText}>No tasks found</Text>
            <Text style={styles.emptyHint}>Pull down to sync with the server</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f9fafb" },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#2563eb",
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  headerTitle: { fontSize: 20, fontWeight: "800", color: "#fff" },
  headerSub: { fontSize: 13, color: "#bfdbfe", marginTop: 2 },
  logoutBtn: {
    backgroundColor: "#1d4ed8",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  logoutText: { color: "#fff", fontSize: 13, fontWeight: "600" },
  syncBar: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    backgroundColor: "#eff6ff",
    paddingHorizontal: 16,
    paddingVertical: 6,
  },
  syncText: { color: "#2563eb", fontSize: 13 },
  searchRow: { paddingHorizontal: 16, paddingTop: 12 },
  searchInput: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 14,
    color: "#111827",
  },
  filterRow: {
    flexDirection: "row",
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 4,
    gap: 6,
  },
  filterTab: {
    borderRadius: 99,
    paddingHorizontal: 14,
    paddingVertical: 6,
    backgroundColor: "#e5e7eb",
  },
  filterTabActive: { backgroundColor: "#2563eb" },
  filterTabText: { fontSize: 13, color: "#374151", fontWeight: "500" },
  filterTabTextActive: { color: "#fff" },
  listContent: { padding: 16, gap: 12 },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
    gap: 6,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
  },
  cardTitle: {
    flex: 1,
    fontSize: 15,
    fontWeight: "600",
    color: "#111827",
  },
  location: { fontSize: 13, color: "#6b7280" },
  cardFooter: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 4,
  },
  metaText: { fontSize: 12, color: "#9ca3af" },
  empty: { alignItems: "center", paddingTop: 60, gap: 8 },
  emptyIcon: { fontSize: 40 },
  emptyText: { fontSize: 16, fontWeight: "600", color: "#374151" },
  emptyHint: { fontSize: 13, color: "#9ca3af" },
});
