import { api } from "./api";
import { saveTokens, saveUser, clearSession, getUser } from "./storage";
import type { TokenResponse, ApiUser } from "../types";

export async function login(email: string, password: string): Promise<ApiUser> {
  const { data: tokens } = await api.post<TokenResponse>("/auth/login", {
    email,
    password,
  });
  await saveTokens(tokens.access_token, tokens.refresh_token);

  const { data: user } = await api.get<ApiUser>("/auth/me");
  await saveUser(user);
  return user;
}

export async function logout(): Promise<void> {
  await clearSession();
}

export async function restoreSession(): Promise<ApiUser | null> {
  return getUser<ApiUser>();
}
