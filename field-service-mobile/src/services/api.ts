import axios from "axios";
import { getAccessToken, clearSession } from "./storage";

// Point to the backend — update for production deploy.
export const API_BASE_URL = "http://192.168.178.143:8000";

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
      // Navigation reset is handled by the AuthContext listener
    }
    return Promise.reject(err);
  }
);
