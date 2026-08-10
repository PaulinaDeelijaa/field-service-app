import Constants from "expo-constants";
import axios from "axios";
import { getAccessToken, clearSession } from "./storage";

const configuredUrl =
  process.env.EXPO_PUBLIC_API_URL ??
  Constants.expoConfig?.extra?.apiUrl ??
  "http://localhost:8000";

export const API_BASE_URL = configuredUrl.replace(/\/$/, "");

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use(async (config) => {
  const token = await getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    if (err.response?.status === 401) {
      await clearSession();
    }
    return Promise.reject(err);
  }
);
