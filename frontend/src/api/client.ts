import type { ApiResponse } from "../types";

// Bo'sh qiymat = joriy origin (frontend qaysi tunnel/domenda ochilgan bo'lsa,
// so'rovlar ham o'sha yerga, /api orqali ketadi - dev serverdagi proxy yoki
// productiondagi nginx uni backend'ga yo'naltiradi).
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
}

export function getAccessToken() {
  return accessToken;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  retry = true
): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401 && retry && refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request<T>(path, options, false);
    }
  }

  return (await response.json()) as ApiResponse<T>;
}

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshToken) return false;
  try {
    const response = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    const body = await response.json();
    if (body.success) {
      accessToken = body.data.access_token;
      return true;
    }
  } catch {
    // jim tarzda muvaffaqiyatsiz - foydalanuvchi qayta login qilishi kerak bo'ladi
  }
  return false;
}

export const api = {
  loginWithTelegram: (initData: string) =>
    request<{ access_token: string; refresh_token: string; user: import("../types").AuthUser }>(
      "/api/v1/auth/telegram",
      { method: "POST", body: JSON.stringify({ init_data: initData }) }
    ),

  listMyGroups: (telegramId: number) =>
    request<import("../types").GroupSummary[]>(`/api/v1/groups/user/${telegramId}`),

  listMembers: (groupId: number) =>
    request<import("../types").MemberSummary[]>(`/api/v1/groups/${groupId}/members`),

  listTasks: (groupId: number) =>
    request<import("../types").TaskSummary[]>(`/api/v1/tasks/group/${groupId}`),

  getQueuePreview: (taskId: number) =>
    request<import("../types").QueueEntry[]>(`/api/v1/tasks/${taskId}/queue/preview`),

  createTask: (payload: {
    telegram_id: number;
    group_id: number;
    name: string;
    require_photo: boolean;
    schedule_type?: string;
    schedule_interval_days?: number | null;
    start_date?: string | null;
    reminder_interval_min_minutes?: number;
    reminder_interval_max_minutes?: number;
    reminder_start_hour?: number;
    reminder_end_hour?: number;
  }) =>
    request<{ task_id: number; name: string }>("/api/v1/tasks/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deleteTask: (taskId: number, telegramId: number) =>
    request<null>(`/api/v1/tasks/${taskId}`, {
      method: "DELETE",
      body: JSON.stringify({ telegram_id: telegramId }),
    }),

  skipQueue: (taskId: number, telegramId: number) =>
    request<null>(`/api/v1/tasks/${taskId}/queue/skip`, {
      method: "POST",
      body: JSON.stringify({ telegram_id: telegramId }),
    }),

  setVacation: (telegramId: number, memberId: number, isOnVacation: boolean) =>
    request<null>("/api/v1/groups/vacation", {
      method: "POST",
      body: JSON.stringify({
        telegram_id: telegramId,
        member_id: memberId,
        is_on_vacation: isOnVacation,
      }),
    }),

  setMemberRole: (groupId: number, memberId: number, telegramId: number, role: "admin" | "member") =>
    request<{ member_id: number; role: string }>(
      `/api/v1/groups/${groupId}/members/${memberId}/role`,
      {
        method: "PATCH",
        body: JSON.stringify({ telegram_id: telegramId, role }),
      }
    ),

  getMemberStatistics: (memberId: number) =>
    request<import("../types").MemberStatistics>(`/api/v1/statistics/member/${memberId}`),

  getMyTasks: (telegramId: number, groupId: number) =>
    request<import("../types").TaskSummary[]>(
      `/api/v1/tasks/member/${telegramId}?group_id=${groupId}`
    ),

  // --- Super Admin ---
  listAllGroups: () =>
    request<import("../types").SuperAdminGroupSummary[]>("/api/v1/superadmin/groups"),

  listAllUsers: () =>
    request<import("../types").SuperAdminUserSummary[]>("/api/v1/superadmin/users"),

  getSystemStats: () => request<import("../types").SystemStats>("/api/v1/superadmin/stats"),

  setMaintenanceMode: (enabled: boolean) =>
    request<null>("/api/v1/superadmin/maintenance-mode", {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),

  broadcastMessage: (text: string) =>
    request<{ sent: number; failed: number; total: number }>("/api/v1/superadmin/broadcast", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  broadcastGroupMessage: (groupId: number, payload: { telegram_id: number; message: string }) =>
    request<null>(`/api/v1/groups/${groupId}/broadcast`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listErrorLogs: () => request<import("../types").ErrorLog[]>("/api/v1/superadmin/logs"),
};
