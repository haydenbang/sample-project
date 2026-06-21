// API 클라이언트. docs/api-spec.md 의 엔드포인트 계약을 따른다.
// 엔드포인트/응답 필드가 바뀌면 이 파일과 hooks, types 가 함께 영향받는다.

import type { OrderListResponse } from "../types/order";
import type { ProductListResponse } from "../types/product";
import type { UserListResponse } from "../types/user";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `요청 실패 (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
}

export const api = {
  login: (email: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  getProducts: (params: { category?: string; page?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.category) q.set("category", params.category);
    if (params.page) q.set("page", String(params.page));
    const qs = q.toString();
    return request<ProductListResponse>(`/products${qs ? `?${qs}` : ""}`);
  },

  getOrders: (params: { status?: string; page?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.status) q.set("status", params.status);
    if (params.page) q.set("page", String(params.page));
    const qs = q.toString();
    return request<OrderListResponse>(`/orders${qs ? `?${qs}` : ""}`);
  },

  getUsers: (params: { page?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    const qs = q.toString();
    return request<UserListResponse>(`/users${qs ? `?${qs}` : ""}`);
  },
};
