import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
  Image,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import * as ImagePicker from "expo-image-picker";
import { v4 as uuidv4 } from "uuid";
import { getTaskByClientId } from "../../../../src/db/taskRepository";
import { insertReport } from "../../../../src/db/reportRepository";
import { insertPhoto } from "../../../../src/db/photoRepository";
import { getPhotoMetadata } from "../../../../src/services/photoService";
import { useAuth } from "../../../../src/contexts/AuthContext";
import { useSync } from "../../../../src/hooks/useSync";

type Material = { name: string; quantity: string };

export default function ReportScreen() {
  const { clientId } = useLocalSearchParams<{ clientId: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const { sync } = useSync();

  const [content, setContent] = useState("");
  const [timeSpent, setTimeSpent] = useState("");
  const [materials, setMaterials] = useState<Material[]>([]);
  const [photos, setPhotos] = useState<{ uri: string; filename: string }[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const task = clientId ? getTaskByClientId(clientId) : null;

  const addMaterial = () => setMaterials((m) => [...m, { name: "", quantity: "" }]);
  const removeMaterial = (i: number) =>
    setMaterials((m) => m.filter((_, idx) => idx !== i));
  const updateMaterial = (i: number, field: keyof Material, value: string) =>
    setMaterials((m) =>
      m.map((item, idx) => (idx === i ? { ...item, [field]: value } : item))
    );

  const pickPhoto = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== "granted") {
      Alert.alert("Permission required", "Allow access to your photo library.");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsMultipleSelection: true,
      quality: 0.8,
    });
    if (!result.canceled) {
      const newPhotos = result.assets.map((a) => ({
        uri: a.uri,
        filename: a.fileName ?? `photo_${Date.now()}.jpg`,
      }));
      setPhotos((p) => [...p, ...newPhotos]);
    }
  };

  const takePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== "granted") {
      Alert.alert("Permission required", "Allow access to your camera.");
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ quality: 0.8 });
    if (!result.canceled && result.assets[0]) {
      setPhotos((p) => [
        ...p,
        {
          uri: result.assets[0].uri,
          filename: `photo_${Date.now()}.jpg`,
        },
      ]);
    }
  };

  const handleSubmit = async () => {
    if (!content.trim()) {
      Alert.alert("Required", "Please describe the work performed.");
      return;
    }
    if (!task || !user) return;

    setSubmitting(true);
    try {
      const materialsJson =
        materials.length > 0 ? JSON.stringify(materials) : null;
      const reportClientId = uuidv4();

      insertReport({
        client_id: reportClientId,
        task_client_id: task.client_id,
        task_id: task.id ?? "",
        worker_id: user.id,
        content: content.trim(),
        materials_used: materialsJson,
        time_spent_minutes: timeSpent ? parseInt(timeSpent, 10) : null,
      });

      for (const photo of photos) {
        const meta = await getPhotoMetadata(photo.uri, photo.filename);
        insertPhoto({
          client_id: uuidv4(),
          task_client_id: task.client_id,
          report_client_id: reportClientId,
          local_uri: photo.uri,
          original_filename: photo.filename,
          mime_type: meta.mime_type,
          file_size_bytes: meta.file_size_bytes,
          sha256_checksum: meta.sha256_checksum,
        });
      }

      sync().catch(() => null);

      Alert.alert("Report saved", "Your report has been saved and will sync automatically.", [
        { text: "OK", onPress: () => router.back() },
      ]);
    } catch (err) {
      Alert.alert("Error", "Failed to save report. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Text style={styles.backText}>← Cancel</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Submit Report</Text>
        <View style={{ width: 70 }} />
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          {task && (
            <View style={styles.taskInfo}>
              <Text style={styles.taskInfoLabel}>Task</Text>
              <Text style={styles.taskInfoTitle}>{task.title}</Text>
            </View>
          )}

          {/* Work description */}
          <View style={styles.section}>
            <Text style={styles.label}>Work performed *</Text>
            <TextInput
              style={[styles.input, styles.textarea]}
              value={content}
              onChangeText={setContent}
              placeholder="Describe what was done, any issues encountered, safety observations…"
              placeholderTextColor="#9ca3af"
              multiline
              numberOfLines={5}
              textAlignVertical="top"
            />
          </View>

          {/* Time spent */}
          <View style={styles.section}>
            <Text style={styles.label}>Time spent (minutes)</Text>
            <TextInput
              style={styles.input}
              value={timeSpent}
              onChangeText={setTimeSpent}
              placeholder="e.g. 90"
              placeholderTextColor="#9ca3af"
              keyboardType="number-pad"
            />
          </View>

          {/* Materials */}
          <View style={styles.section}>
            <View style={styles.rowBetween}>
              <Text style={styles.label}>Materials used</Text>
              <TouchableOpacity onPress={addMaterial}>
                <Text style={styles.addLink}>+ Add</Text>
              </TouchableOpacity>
            </View>
            {materials.map((m, i) => (
              <View key={i} style={styles.materialRow}>
                <TextInput
                  style={[styles.input, { flex: 2 }]}
                  value={m.name}
                  onChangeText={(v) => updateMaterial(i, "name", v)}
                  placeholder="Material name"
                  placeholderTextColor="#9ca3af"
                />
                <TextInput
                  style={[styles.input, { flex: 1, marginHorizontal: 8 }]}
                  value={m.quantity}
                  onChangeText={(v) => updateMaterial(i, "quantity", v)}
                  placeholder="Qty"
                  placeholderTextColor="#9ca3af"
                />
                <TouchableOpacity onPress={() => removeMaterial(i)}>
                  <Text style={styles.removeLink}>✕</Text>
                </TouchableOpacity>
              </View>
            ))}
            {materials.length === 0 && (
              <Text style={styles.emptyHint}>No materials added</Text>
            )}
          </View>

          {/* Photos */}
          <View style={styles.section}>
            <Text style={styles.label}>Photos</Text>
            <View style={styles.photoActions}>
              <TouchableOpacity style={styles.photoBtn} onPress={takePhoto}>
                <Text style={styles.photoBtnText}>📷 Camera</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.photoBtn} onPress={pickPhoto}>
                <Text style={styles.photoBtnText}>🖼 Gallery</Text>
              </TouchableOpacity>
            </View>
            {photos.length > 0 && (
              <ScrollView horizontal style={styles.photoScroll} showsHorizontalScrollIndicator={false}>
                {photos.map((p, i) => (
                  <View key={i} style={styles.photoThumbWrapper}>
                    <Image source={{ uri: p.uri }} style={styles.photoThumb} />
                    <TouchableOpacity
                      style={styles.photoRemove}
                      onPress={() => setPhotos((ps) => ps.filter((_, idx) => idx !== i))}
                    >
                      <Text style={styles.photoRemoveText}>✕</Text>
                    </TouchableOpacity>
                  </View>
                ))}
              </ScrollView>
            )}
          </View>

          {/* Submit */}
          <TouchableOpacity
            style={[styles.submitBtn, submitting && styles.submitBtnDisabled]}
            onPress={handleSubmit}
            disabled={submitting}
            activeOpacity={0.85}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.submitBtnText}>Submit Report</Text>
            )}
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f9fafb" },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#7c3aed",
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  backBtn: { width: 70 },
  backText: { color: "#ddd6fe", fontSize: 15 },
  headerTitle: { color: "#fff", fontSize: 17, fontWeight: "700" },
  content: { padding: 16, gap: 4, paddingBottom: 40 },
  taskInfo: {
    backgroundColor: "#ede9fe",
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
  },
  taskInfoLabel: { fontSize: 11, fontWeight: "600", color: "#7c3aed", textTransform: "uppercase" },
  taskInfoTitle: { fontSize: 15, fontWeight: "600", color: "#1e1b4b", marginTop: 2 },
  section: { marginBottom: 16 },
  label: { fontSize: 13, fontWeight: "600", color: "#374151", marginBottom: 8 },
  input: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 11,
    fontSize: 14,
    color: "#111827",
  },
  textarea: { minHeight: 120 },
  rowBetween: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  addLink: { color: "#7c3aed", fontWeight: "600", fontSize: 14 },
  materialRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 8,
  },
  removeLink: { color: "#ef4444", fontSize: 18, fontWeight: "700" },
  emptyHint: { fontSize: 13, color: "#9ca3af", marginTop: 4 },
  photoActions: { flexDirection: "row", gap: 10, marginBottom: 10 },
  photoBtn: {
    flex: 1,
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
  },
  photoBtnText: { fontSize: 14, fontWeight: "600", color: "#374151" },
  photoScroll: { marginTop: 4 },
  photoThumbWrapper: { position: "relative", marginRight: 8 },
  photoThumb: { width: 80, height: 80, borderRadius: 8 },
  photoRemove: {
    position: "absolute",
    top: -6,
    right: -6,
    backgroundColor: "#ef4444",
    width: 20,
    height: 20,
    borderRadius: 10,
    justifyContent: "center",
    alignItems: "center",
  },
  photoRemoveText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  submitBtn: {
    backgroundColor: "#7c3aed",
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 12,
  },
  submitBtnDisabled: { opacity: 0.6 },
  submitBtnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
