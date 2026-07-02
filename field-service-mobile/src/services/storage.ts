/**
 * Thin wrapper around expo-secure-store.
 * Tokens are stored encrypted using the device keychain/keystore.
 */
import * as SecureStore from "expo-secure-store";

const KEYS = {
  ACCESS_TOKEN: "fs_access_token",
  REFRESH_TOKEN: "fs_refresh_token",
  USER_JSON: "fs_user",
} as const;

export async function saveTokens(access: string, refresh: string): Promise<void> {
  await SecureStore.setItemAsync(KEYS.ACCESS_TOKEN, access);
  await SecureStore.setItemAsync(KEYS.REFRESH_TOKEN, refresh);
}

export async function getAccessToken(): Promise<string | null> {
  return SecureStore.getItemAsync(KEYS.ACCESS_TOKEN);
}

export async function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(KEYS.REFRESH_TOKEN);
}

export async function saveUser(user: object): Promise<void> {
  await SecureStore.setItemAsync(KEYS.USER_JSON, JSON.stringify(user));
}

export async function getUser<T>(): Promise<T | null> {
  const raw = await SecureStore.getItemAsync(KEYS.USER_JSON);
  return raw ? (JSON.parse(raw) as T) : null;
}

export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(KEYS.ACCESS_TOKEN);
  await SecureStore.deleteItemAsync(KEYS.REFRESH_TOKEN);
  await SecureStore.deleteItemAsync(KEYS.USER_JSON);
}
