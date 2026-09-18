export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  message: string | null;
}

export interface AuthUser {
  id: number;
  telegram_id: number;
  full_name: string;
  language: string;
  is_super_admin: boolean;
}

export interface LoginData {
  access_token: string;
  refresh_token: string;
  user: AuthUser;
}

export interface GroupSummary {
  id: number;
  name: string;
  role: "admin" | "member";
  member_id: number;
  timezone: string;
}

export interface MemberSummary {
  member_id: number;
  user_id: number;
  full_name: string;
  role: "admin" | "member";
  is_on_vacation: boolean;
}

export interface TaskSummary {
  id: number;
  name: string;
  priority: number;
  is_active: boolean;
  current_assignee?: string;
  current_turn_date?: string | null;
  days_left?: number;
  is_active_now?: boolean;
  next_execution_date?: string;

  /*
   * Eslatma sozlamalari. Backend `GET /tasks/group/{id}` da bu to'rt
   * maydonni ALLAQACHON qaytaradi, lekin frontend ularni hech qachon
   * ko'rsatmagan - admin vazifa qanday sozlanganini bilish uchun uni
   * o'chirib qayta yaratishi kerak edi. Yangi API chaqiruvi qo'shilmaydi,
   * mavjud javobdagi ma'lumot ishlatiladi.
   * `GET /tasks/member/{tg}` bu maydonlarni qaytarmaydi - shuning uchun
   * ixtiyoriy.
   */
  reminder_interval_min_minutes?: number;
  reminder_interval_max_minutes?: number;
  reminder_start_hour?: number;
  reminder_end_hour?: number;

  /** Vazifani tahrirlash formasini oldindan to'ldirish uchun. */
  description?: string | null;
  require_photo?: boolean;
  schedule_interval_days?: number;
  /**
   * Xom `next_execution_date` (lokal sana) - `current_turn_date`dan farqli
   * o'laroq, tahrirlash formasi buni to'g'ridan-to'g'ri o'qib-yozadi,
   * chunki `current_turn_date` interval bo'yicha SURILGAN (hisoblangan)
   * qiymat - uni orqaga yozish jadvalni bitta intervalga siljitib qo'yardi.
   */
  next_cycle_date?: string | null;
}

export interface QueueEntry {
  id: number;
  member_id: number;
  position: number;
  is_locked: boolean;
  full_name?: string;
  scheduled_date?: string | null;
}

export interface MemberStatistics {
  total: number;
  completed: number;
  completion_rate: number;
}

export interface SuperAdminGroupSummary {
  id: number;
  name: string;
  member_count: number;
  timezone: string;
  is_active: boolean;
  created_at: string;
}

export interface SuperAdminUserSummary {
  id: number;
  telegram_id: number;
  full_name: string;
  username: string | null;
  is_super_admin: boolean;
  is_active: boolean;
  joined_at: string;
}

export interface SuperAdminUserGroupMembership {
  group_id: number;
  group_name: string;
  role: "admin" | "member";
}

export interface SuperAdminUserProfile {
  id: number;
  telegram_id: number;
  full_name: string;
  username: string | null;
  phone_number: string | null;
  is_active: boolean;
  is_super_admin: boolean;
  joined_at: string;
  groups: SuperAdminUserGroupMembership[];
}

export interface SystemStats {
  total_groups: number;
  total_users: number;
  total_active_tasks: number;
  total_completions: number;
  maintenance_mode: boolean;
}

export interface ErrorLog {
  id: number;
  level: string;
  message: string;
  context: string | null;
  created_at: string;
}
