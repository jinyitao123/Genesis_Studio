import { storeToRefs } from 'pinia';
import { useAuthStore } from '@/stores/useAuthStore';

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:18080";

export async function apiGet<T>(path: string, token?: string): Promise<T> {
  // Auto-fetch token from authStore if not provided
  const authStore = useAuthStore();
  const { token: authToken } = storeToRefs(authStore);
  const effectiveToken = token || authToken.value;

  const headers: Record<string, string> = {};
  if (effectiveToken) {
    headers.Authorization = `Bearer ${effectiveToken}`;
  }
  const response = await fetch(`${API_BASE}${path}`, { headers });
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function apiPost<T>(
  path: string,
  body: Record<string, unknown>,
  token?: string,
): Promise<T> {
  // Auto-fetch token from authStore if not provided
  const authStore = useAuthStore();
  const { token: authToken } = storeToRefs(authStore);
  const effectiveToken = token || authToken.value;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (effectiveToken) {
    headers.Authorization = `Bearer ${effectiveToken}`;
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(err?.detail ?? `POST ${path} failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function apiDelete<T = { deleted: boolean }>(path: string, token?: string): Promise<T> {
  const authStore = useAuthStore();
  const { token: authToken } = storeToRefs(authStore);
  const effectiveToken = token || authToken.value;
  const headers: Record<string, string> = {};
  if (effectiveToken) {
    headers.Authorization = `Bearer ${effectiveToken}`;
  }
  const response = await fetch(`${API_BASE}${path}`, { method: "DELETE", headers });
  if (!response.ok) {
    const err = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(err?.detail ?? `DELETE ${path} failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function apiPatch<T>(
  path: string,
  body: Record<string, unknown>,
  token?: string,
): Promise<T> {
  const authStore = useAuthStore();
  const { token: authToken } = storeToRefs(authStore);
  const effectiveToken = token || authToken.value;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (effectiveToken) {
    headers.Authorization = `Bearer ${effectiveToken}`;
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(err?.detail ?? `PATCH ${path} failed: ${response.status}`);
  }
  return (await response.json()) as T;
}
