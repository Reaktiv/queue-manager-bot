/*
 * Sana formatlash. Ilgari aynan shu funksiya AdminDashboard, MemberDashboard
 * va QueueList ichida uch marta nusxalangan edi.
 */
const MONTHS_UZ = [
  "yanvar", "fevral", "mart", "aprel", "may", "iyun",
  "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr",
];

/** "2026-09-11" -> "11-sentyabr" */
export function formatDay(value?: string | null): string {
  if (!value) return "—";
  const [y, m, d] = value.split("-");
  if (!y || !m || !d) return value;
  const month = MONTHS_UZ[Number(m) - 1];
  if (!month) return value;
  return `${Number(d)}-${month}`;
}

/** Guruh vaqt zonasidagi bugungi sana, <input type="date"> uchun */
export function todayInZone(timeZone = "Asia/Tashkent"): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const get = (t: string) => parts.find((p) => p.type === t)?.value;
  return `${get("year") ?? "1970"}-${get("month") ?? "01"}-${get("day") ?? "01"}`;
}

/** "Ertaga", "3 kundan keyin", "2 haftadan keyin" */
export function humanizeDaysLeft(days: number): string {
  if (days <= 0) return "Bugun";
  if (days === 1) return "Ertaga";
  if (days % 7 === 0) return `${days / 7} haftadan keyin`;
  return `${days} kundan keyin`;
}

/*
 * Backend "hech kim biriktirilmagan" holatini `current_assignee: "Hech kim"`
 * satri bilan bildiradi (bo'sh/null emas) - `tasks.py` router shu literalni
 * qattiq yozadi. Bu tekshiruv ilgari AdminDashboard va MemberDashboard'da
 * mustaqil ikki marta yozilgan edi.
 */
export function hasAssignee(name: string | undefined): name is string {
  return !!name && name !== "Hech kim";
}

/** Log vaqti uchun qisqa ko'rinish */
export function formatStamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("uz-UZ", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}
