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
  current_penalty: number;
  total_missed: number;
  total: number;
  completed: number;
  completion_rate: number;

  /*
   * 5 yulduzli profil darajasi (aralash model - backend `RatingService`):
   *   rating_stars = guruhdoshlar bergan o'rtacha ball (hali baho
   *   bo'lmasa 5.0) - jami jarima balli, 1.0 va 5.0 oralig'ida.
   */
  rating_stars: number;
  /** Guruhdoshlar bergan o'rtacha sifat bahosi, hali hech kim baho bermagan bo'lsa `null`. */
  peer_rating_avg: number | null;
  /** Nechta guruhdosh baho berganini bildiradi. */
  rating_count: number;
  /** Jami jarima balli (o'tkazib yuborilgan kunlar soni) - rating_stars shundan ayiriladi. */
  penalty_points: number;
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
