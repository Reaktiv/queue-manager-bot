import type {
  ApiResponse,
  ErrorLog,
  GroupSummary,
  LoginData,
  MemberStatistics,
  MemberSummary,
  QueueEntry,
  SuperAdminGroupSummary,
  SuperAdminUserSummary,
  SystemStats,
  TaskSummary,
} from "../types";

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

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  } catch {
    return { success: false, data: null, message: "Serverga ulanib bo'lmadi" } as ApiResponse<T>;
  }

  if (response.status === 401 && retry && refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request<T>(path, options, false);
    }
  }

  // Javob JSON bo'lmasligi mumkin: tunnel/proxy o'z HTML sahifasini qaytarsa
  // (masalan ngrok'ning ogohlantirish sahifasi) yoki 502 bo'lsa. Bunda
  // `response.json()` istisno tashlaydi va butun ekran qotib qolardi.
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return {
      success: false,
      data: null,
      message: `Server noto'g'ri javob qaytardi (HTTP ${response.status})`,
    } as ApiResponse<T>;
  }

  return normalize<T>(body, response.status);
}

/*
 * Backend ikki xil shaklda javob qaytaradi:
 *
 *   1. Router'lar - {success, data, message}  (bizning konvert)
 *   2. FastAPI HTTPException - {detail: "..."}  (401/403)
 *      va validatsiya xatolari - {detail: [{msg, loc}, ...]}  (422)
 *
 * Ilgari bu yerda faqat `response.json()` qaytarilardi, ya'ni ikkinchi
 * shakl uchun `success` `undefined` bo'lib qolardi (noto'g'ri deb
 * qabul qilinardi - to'g'ri) LEKIN `message` ham `undefined` bo'lardi.
 * Natijada backend aniq aytgan sabab - masalan "Bu amalni faqat guruh
 * admini bajara oladi" - tashlab yuborilib, foydalanuvchiga umumiy
 * "O'chirib bo'lmadi" ko'rsatilardi.
 *
 * Endi `detail` xabarga ko'chiriladi. API shartnomasi o'zgarmaydi -
 * chaqiruvchilar avvalgidek {success, data, message} oladi.
 */
function normalize<T>(body: unknown, status: number): ApiResponse<T> {
  if (body && typeof body === "object" && "success" in body) {
    return body as ApiResponse<T>;
  }

  const detail = (body as { detail?: unknown } | null)?.detail;

  let message: string | null = null;
  if (typeof detail === "string") {
    message = detail;
  } else if (Array.isArray(detail)) {
    // 422: Pydantic validatsiya xatolari ro'yxati
    const first = detail[0] as { msg?: string } | undefined;
    message = first?.msg ?? null;
  }

  return {
    success: false,
    data: null,
    message: message ?? `So'rov bajarilmadi (HTTP ${status})`,
  } as ApiResponse<T>;
}

/*
 * Bir vaqtda bir nechta so'rov 401 olishi mumkin (masalan MemberDashboard
 * uchta so'rovni parallel yuboradi). Ilgari har biri alohida refresh
 * so'rovi yuborardi - ya'ni bitta token yangilash o'rniga uchta, va ular
 * bir-birining natijasini ustiga yozishi mumkin edi. Endi navbatdagi
 * chaqiruvlar ayni bitta so'rovni kutadi.
 */
let refreshInFlight: Promise<boolean> | null = null;

function refreshAccessToken(): Promise<boolean> {
  if (!refreshToken) return Promise.resolve(false);
  if (!refreshInFlight) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

async function doRefresh(): Promise<boolean> {
  try {
    const response = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    const body = (await response.json()) as ApiResponse<{ access_token: string }>;
    if (body.success && body.data?.access_token) {
      accessToken = body.data.access_token;
      return true;
    }
    // Refresh token ham yaroqsiz - qayta urinishning ma'nosi yo'q
    refreshToken = null;
  } catch {
    // jim tarzda muvaffaqiyatsiz - foydalanuvchi qayta login qilishi kerak bo'ladi
  }
  return false;
}

export const api = {
  loginWithTelegram: (initData: string) =>
    request<LoginData>(
      "/api/v1/auth/telegram",
      { method: "POST", body: JSON.stringify({ init_data: initData }) }
    ),

  listMyGroups: (telegramId: number) =>
    request<GroupSummary[]>(`/api/v1/groups/user/${telegramId}`),

  listMembers: (groupId: number) =>
    request<MemberSummary[]>(`/api/v1/groups/${groupId}/members`),

  listTasks: (groupId: number) =>
    request<TaskSummary[]>(`/api/v1/tasks/group/${groupId}`),

  getQueuePreview: (taskId: number) =>
    request<QueueEntry[]>(`/api/v1/tasks/${taskId}/queue/preview`),

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
    request<MemberStatistics>(`/api/v1/statistics/member/${memberId}`),

  getMyTasks: (telegramId: number, groupId: number) =>
    request<TaskSummary[]>(
      `/api/v1/tasks/member/${telegramId}?group_id=${groupId}`
    ),

  // --- Super Admin ---
  listAllGroups: () =>
    request<SuperAdminGroupSummary[]>("/api/v1/superadmin/groups"),

  listAllUsers: () =>
    request<SuperAdminUserSummary[]>("/api/v1/superadmin/users"),

  getSystemStats: () => request<SystemStats>("/api/v1/superadmin/stats"),

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

  listErrorLogs: () => request<ErrorLog[]>("/api/v1/superadmin/logs"),

  /*
   * Yulduz bahosi (rate) endpointi ATAYLAB shu yerda yo'q: baholash bot
   * ichida, guruh chatidagi inline tugmalar orqali sodir bo'ladi
   * (bot/handlers/ratings.py) - Mini App'da alohida baholash amali yo'q,
   * shuning uchun ishlatilmaydigan API klient metodini qo'shmaymiz.
   */
  clearErrorLogs: () =>
    request<{ deleted_count: number }>("/api/v1/superadmin/logs", { method: "DELETE" }),
};