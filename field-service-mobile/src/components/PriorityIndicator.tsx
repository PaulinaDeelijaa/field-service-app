import React from "react";
import { View, StyleSheet } from "react-native";
import type { TaskPriority } from "../types";

const COLORS: Record<TaskPriority, string> = {
  low:      "#10b981",
  medium:   "#f59e0b",
  high:     "#ef4444",
  critical: "#7c3aed",
};

export function PriorityIndicator({ priority }: { priority: TaskPriority }) {
  return (
    <View style={[styles.dot, { backgroundColor: COLORS[priority] ?? "#9ca3af" }]} />
  );
}

const styles = StyleSheet.create({
  dot: { width: 10, height: 10, borderRadius: 5 },
});
