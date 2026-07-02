import React, { useEffect } from "react";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AuthProvider } from "../src/contexts/AuthContext";
import { initDatabase } from "../src/db/database";
import { getDeviceId } from "../src/db/syncWatermark";

export default function RootLayout() {
  useEffect(() => {
    initDatabase();
    getDeviceId(); // ensures the watermark row is created
  }, []);

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <StatusBar style="auto" />
        <Stack screenOptions={{ headerShown: false }} />
      </AuthProvider>
    </SafeAreaProvider>
  );
}
