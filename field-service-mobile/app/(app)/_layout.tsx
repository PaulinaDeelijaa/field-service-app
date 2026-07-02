import { Redirect, Stack } from "expo-router";
import { useAuth } from "../../src/contexts/AuthContext";
import { View, ActivityIndicator } from "react-native";

export default function AppLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    );
  }

  if (!user) return <Redirect href="/login" />;

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: "#2563eb" },
        headerTintColor: "#fff",
        headerTitleStyle: { fontWeight: "700" },
      }}
    />
  );
}
