import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Icon, type IconName } from "./Icon";
import { haptics, useTelegramBackButton } from "../hooks/useTelegramViewport";

/*
 * Dizayn tizimi primitivlari.
 *
 * MUHIM: barcha mavjud eksportlar va prop shakllari saqlangan, shuning
 * uchun sahifalar (AdminDashboard, MemberDashboard, GroupSelector,
 * SuperAdminDashboard) o'zgarishsiz kompilyatsiya bo'ladi va yangi
 * palitrani/o'lchamlarni avtomatik oladi. Eski variant nomlari
 * ("solid", "soft", "danger", "brand", "jade", ...) yangi semantik
 * nomlarga alias qilingan - STEP 3 da sahifalar ko'chiriladi.
 */

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ *
 * Fokus: bitta joyda belgilanadi, hamma interaktiv element ishlatadi.
 * Ilgari loyihada birorta ham ko'rinadigan fokus holati yo'q edi.
 * ------------------------------------------------------------------ */
const FOCUS =
  "outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-ground";

/* ------------------------------------------------------------------ *
 * Spinner - tugma va yuklanish holatlari uchun
 * ------------------------------------------------------------------ */
function Spinner({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="animate-spin"
      aria-hidden
      focusable="false"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.25" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

/* ------------------------------------------------------------------ *
 * Toast - modulga bog'langan oddiy pub/sub: istalgan fayldan
 * `toast("matn")` chaqirsa kifoya, prop uzatish shart emas.
 * `alert()` ni almashtiradi - u Telegram WebView'ni bloklab qo'yadi.
 * ------------------------------------------------------------------ */
type ToastTone = "ok" | "err" | "info";
type ToastItem = { id: number; text: string; tone: ToastTone };

let toastSeq = 0;
const toastSubs = new Set<(items: ToastItem[]) => void>();
let toastItems: ToastItem[] = [];

function pushToast(text: string, tone: ToastTone) {
  const item = { id: ++toastSeq, text, tone };
  toastItems = [...toastItems, item];
  toastSubs.forEach((fn) => fn(toastItems));
  // Telegram-native his: natija haptika bilan ham bildiriladi.
  haptics.notify(tone === "ok" ? "success" : tone === "err" ? "error" : "warning");
  setTimeout(() => {
    toastItems = toastItems.filter((t) => t.id !== item.id);
    toastSubs.forEach((fn) => fn(toastItems));
  }, 3600);
}

export const toast = {
  ok: (text: string) => pushToast(text, "ok"),
  err: (text: string) => pushToast(text, "err"),
  info: (text: string) => pushToast(text, "info"),
};

const TOAST_ICON: Record<ToastTone, IconName> = {
  ok: "check",
  err: "alert",
  info: "info",
};

export function ToastHost() {
  const [items, setItems] = useState<ToastItem[]>([]);
  useEffect(() => {
    toastSubs.add(setItems);
    return () => {
      toastSubs.delete(setItems);
    };
  }, []);

  return (
    <div
      className="pointer-events-none fixed inset-x-0 top-0 z-[60] flex flex-col items-center gap-2 px-gutter pt-safe"
      // Ekran o'quvchi toast matnini eshitsin - ilgari u faqat vizual edi.
      role="status"
      aria-live="polite"
      aria-atomic="false"
    >
      {items.map((t) => (
        <div
          key={t.id}
          className={cx(
            "glass-strong animate-riseIn pointer-events-auto flex w-full max-w-sm items-start gap-2.5 rounded-card px-3.5 py-3 text-callout shadow-e2",
            t.tone === "ok" && "text-success",
            t.tone === "err" && "text-danger",
            t.tone === "info" && "text-ink"
          )}
        >
          <Icon name={TOAST_ICON[t.tone]} size={18} className="mt-px shrink-0" />
          <span className="leading-snug text-ink">{t.text}</span>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Avatar - ismning bosh harflari.
 * Ilgari 5 ta gradient halqa ishlatilardi; har bir ro'yxat qatorida
 * ma'no tashimaydigan rang shovqini hosil bo'lardi. Endi tekis,
 * bosiq tonal fon.
 * ------------------------------------------------------------------ */
const AVATAR_TONES = [
  "bg-accent/16 text-accent",
  "bg-success/16 text-success",
  "bg-warning/18 text-warning",
  "bg-danger/16 text-danger",
  "bg-info/16 text-info",
];

export function Avatar({
  name,
  size = "md",
  crown = false,
}: {
  name: string;
  size?: "sm" | "md" | "lg";
  crown?: boolean;
}) {
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  const tone = AVATAR_TONES[hash % AVATAR_TONES.length];
  const dims = {
    sm: "h-8 w-8 text-micro",
    md: "h-10 w-10 text-caption",
    lg: "h-14 w-14 text-headline",
  }[size];

  return (
    <span className="relative inline-flex shrink-0">
      <span
        className={cx(
          "inline-flex items-center justify-center rounded-pill font-bold tracking-wide",
          tone,
          dims
        )}
        aria-hidden
      >
        {initials || "?"}
      </span>
      {crown && (
        <span className="absolute -right-1 -top-1 grid h-4 w-4 place-items-center rounded-pill bg-warning text-semantic-ink">
          <Icon name="crown" size={10} strokeWidth={2.25} />
        </span>
      )}
    </span>
  );
}

/* ------------------------------------------------------------------ *
 * Pill / Badge - holat belgisi
 * ------------------------------------------------------------------ */
type PillTone =
  | "neutral"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "info"
  /* eski nomlar */
  | "brand"
  | "jade"
  | "amber"
  | "rose";

const PILL_TONES: Record<PillTone, string> = {
  neutral: "bg-surface-2 text-muted",
  accent: "bg-accent/14 text-accent",
  success: "bg-success/16 text-success",
  warning: "bg-warning/18 text-warning",
  danger: "bg-danger/16 text-danger",
  info: "bg-info/16 text-info",
  brand: "bg-accent/14 text-accent",
  jade: "bg-success/16 text-success",
  amber: "bg-warning/18 text-warning",
  rose: "bg-danger/16 text-danger",
};

const PILL_DOTS: Record<PillTone, string> = {
  neutral: "bg-muted",
  accent: "bg-accent",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info",
  brand: "bg-accent",
  jade: "bg-success",
  amber: "bg-warning",
  rose: "bg-danger",
};

function Pill({
  children,
  tone = "neutral",
  dot = false,
}: {
  children: ReactNode;
  tone?: PillTone;
  dot?: boolean;
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-pill px-2.5 py-1 text-caption font-semibold",
        PILL_TONES[tone]
      )}
    >
      {dot && <span className={cx("h-1.5 w-1.5 shrink-0 rounded-pill", PILL_DOTS[tone])} aria-hidden />}
      {children}
    </span>
  );
}

/* Yagona eksport `Badge`: ilova bo'ylab faqat shu nom ishlatiladi.
   `Pill` ichki amalga oshirish sifatida qoladi. */
export const Badge = Pill;

/* ------------------------------------------------------------------ *
 * Tugmalar
 * ------------------------------------------------------------------ */
type BtnVariant =
  | "primary"
  | "secondary"
  | "ghost"
  | "destructive"
  | "outline"
  /* eski nomlar */
  | "solid"
  | "soft"
  | "danger";

const BTN_VARIANTS: Record<BtnVariant, string> = {
  primary: "bg-accent-solid text-accent-ink shadow-e1 active:bg-accent-solid/88",
  secondary: "bg-accent/14 text-accent active:bg-accent/24",
  outline: "border border-control-edge bg-surface text-ink active:bg-interactive",
  ghost: "text-ink-2 active:bg-surface-2",
  destructive: "bg-danger/14 text-danger active:bg-danger/24",
  solid: "bg-accent-solid text-accent-ink shadow-e1 active:bg-accent-solid/88",
  soft: "bg-accent/14 text-accent active:bg-accent/24",
  danger: "bg-danger/14 text-danger active:bg-danger/24",
};

const BTN_SIZES = {
  /* sm vizual jihatdan 36px, lekin `tap-44` tegish maydonini 44px qiladi */
  sm: "h-9 px-3 text-caption rounded-control gap-1.5 tap-44",
  md: "h-11 px-4 text-callout rounded-control gap-2",
  lg: "h-13 px-5 text-headline rounded-control gap-2",
};

export function Btn({
  children,
  onClick,
  variant = "primary",
  size = "md",
  disabled,
  loading = false,
  full,
  type = "button",
  icon,
  iconRight,
  ariaLabel,
  className,
}: {
  children?: ReactNode;
  onClick?: () => void;
  variant?: BtnVariant;
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  loading?: boolean;
  full?: boolean;
  type?: "button" | "submit";
  icon?: IconName;
  iconRight?: IconName;
  ariaLabel?: string;
  className?: string;
}) {
  const isDisabled = disabled || loading;
  return (
    <button
      type={type}
      onClick={
        onClick
          ? () => {
              haptics.press("light");
              onClick();
            }
          : undefined
      }
      disabled={isDisabled}
      aria-label={ariaLabel}
      aria-busy={loading || undefined}
      className={cx(
        "inline-flex select-none items-center justify-center font-semibold",
        "transition-[transform,background-color,opacity] duration-fast ease-out",
        "active:scale-[.97] disabled:pointer-events-none disabled:opacity-45",
        FOCUS,
        BTN_SIZES[size],
        BTN_VARIANTS[variant],
        full && "w-full",
        className
      )}
    >
      {loading ? (
        <Spinner size={size === "lg" ? 18 : 16} />
      ) : (
        icon && <Icon name={icon} size={size === "sm" ? 16 : 18} className="shrink-0" />
      )}
      {children}
      {iconRight && !loading && (
        <Icon name={iconRight} size={size === "sm" ? 16 : 18} className="shrink-0" />
      )}
    </button>
  );
}

/**
 * Faqat ikonkali tugma. `label` MAJBURIY - u aria-label bo'ladi,
 * aks holda ekran o'quvchi uchun tugma nomsiz qolardi.
 */
export function IconButton({
  name,
  label,
  onClick,
  tone = "neutral",
  size = "md",
  disabled,
  className,
}: {
  name: IconName;
  label: string;
  onClick?: () => void;
  tone?: "neutral" | "accent" | "danger" | "onGlass";
  size?: "sm" | "md";
  disabled?: boolean;
  className?: string;
}) {
  const tones = {
    neutral: "bg-surface-2 text-ink-2 active:bg-interactive",
    accent: "bg-accent/14 text-accent active:bg-accent/24",
    danger: "bg-danger/14 text-danger active:bg-danger/24",
    onGlass: "bg-ink/10 text-ink active:bg-ink/16",
  };
  const dims = size === "sm" ? "h-8 w-8" : "h-10 w-10";

  return (
    <button
      type="button"
      onClick={
        onClick
          ? () => {
              haptics.press("light");
              onClick();
            }
          : undefined
      }
      disabled={disabled}
      aria-label={label}
      className={cx(
        "tap-44 grid shrink-0 place-items-center rounded-pill",
        "transition-[transform,background-color] duration-fast ease-out active:scale-90",
        "disabled:pointer-events-none disabled:opacity-45",
        FOCUS,
        dims,
        tones[tone],
        className
      )}
    >
      <Icon name={name} size={size === "sm" ? 16 : 20} />
    </button>
  );
}

/* ------------------------------------------------------------------ *
 * Yuzalar
 *
 * Ma'lumot ko'rsatadigan yuzalar HAMISHA shaffof emas (opaque).
 * Glass faqat suzuvchi xrom uchun - Sheet va AppHeader.
 * Har bir yuza yo CHEGARA, yo SOYA oladi - ikkalasi birga emas.
 * ------------------------------------------------------------------ */
export function Surface({
  children,
  className,
  onClick,
  padded = true,
  interactive = false,
  material = "raised",
}: {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  padded?: boolean;
  interactive?: boolean;
  /** raised = soya bilan, flat = chegara bilan.
      "glass" varianti ATAYLAB yo'q: glass faqat suzuvchi xrom uchun
      (AppHeader, BottomTabs, Sheet) - ma'lumot ko'rsatadigan yuza
      hech qachon shaffof bo'lmaydi. */
  material?: "raised" | "flat";
}) {
  const materials = {
    raised: "bg-surface shadow-e1",
    flat: "bg-surface border border-line",
  };

  const shared = cx(
    "rounded-card",
    materials[material],
    padded && "p-4",
    interactive &&
      "cursor-pointer transition-transform duration-fast ease-out active:scale-[.985] active:bg-interactive",
    className
  );

  /*
   * `onClick` berilganda HAQIQIY <button> qaytariladi - xuddi shu
   * sabab bilan `ListRow` ham shunday qiladi: oddiy `<div onClick>`
   * klaviatura, fokus va ekran o'quvchi bilan umuman ishlamaydi.
   */
  if (onClick) {
    return (
      <button
        type="button"
        onClick={() => {
          haptics.press("light");
          onClick();
        }}
        className={cx("block w-full text-left", FOCUS, shared)}
      >
        {children}
      </button>
    );
  }

  return <div className={shared}>{children}</div>;
}

export function SectionHead({
  title,
  sub,
  action,
}: {
  title: string;
  sub?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-3 flex items-end justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-title-2 text-ink">{title}</h2>
        {sub && <p className="mt-0.5 text-caption text-muted">{sub}</p>}
      </div>
      {action}
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Formalar
 * ------------------------------------------------------------------ */
export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-micro uppercase text-muted">{label}</span>
      {children}
      {/*
        Xato va maslahat bitta joyda ko'rsatiladi. Xato paydo bo'lganda
        layout sakramasligi uchun ikkalasi ham bir xil qatorda turadi.
      */}
      {error ? (
        <span className="mt-1 block text-caption text-danger">{error}</span>
      ) : (
        hint && <span className="mt-1 block text-caption text-muted">{hint}</span>
      )}
    </label>
  );
}

/*
 * Input: 16px shrift - iOS Safari 16px dan kichik maydonga fokuslanganda
 * sahifani avtomatik kattalashtiradi (zoom), bu Mini App'da juda yomon
 * ko'rinadi. Chegara `control-edge` - u >=3:1 kontrastga ega (WCAG 1.4.11),
 * eski `line` esa 1.24:1 edi, ya'ni input chegarasi amalda ko'rinmasdi.
 */
const inputBase = cx(
  "w-full min-h-tap rounded-control border border-control-edge bg-surface-2",
  "px-3.5 py-2.5 text-[16px] leading-snug text-ink placeholder:text-muted",
  "transition-[border-color,background-color,box-shadow] duration-fast ease-out",
  "outline-none focus-visible:border-accent focus-visible:shadow-focus",
  "disabled:opacity-50 disabled:cursor-not-allowed",
  "aria-[invalid=true]:border-danger"
);

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx(inputBase, props.className)} />;
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cx(inputBase, "resize-none leading-relaxed", props.className)}
    />
  );
}

/* Raqamli maydon uchun -/+ tugmalari: telefonda klaviatura ochmasdan sozlash.
   Tugmalar 44px - ilgari 32px edi. */
export function Stepper({
  value,
  onChange,
  min = 0,
  max = 999,
  suffix,
  label,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  suffix?: string;
  /** Ekran o'quvchi uchun: "Takrorlanish" kabi. */
  label?: string;
}) {
  const clamp = (v: number) => Math.min(max, Math.max(min, v));
  const step = (delta: number) => {
    haptics.select();
    onChange(clamp(value + delta));
  };
  const btn = cx(
    "grid h-11 w-11 shrink-0 place-items-center rounded-control text-ink-2",
    "transition-transform duration-fast ease-out active:scale-90 active:bg-surface",
    "disabled:opacity-35 disabled:pointer-events-none",
    FOCUS
  );

  /*
   * XATOLIK: `Stepper` odatda `Field` ichida ishlatiladi, u o'zining
   * yorlig'ini `<label>` bilan o'raydi (Input/TextArea kabi yagona
   * nazoratli maydonlarga aniq nom berish uchun). Brauzer qoidasiga
   * ko'ra, `<label>` matniga bosilganda klik DOM tartibidagi BIRINCHI
   * "labelable" elementga (input/button/select/...) yo'naltiriladi.
   * Kamaytirish tugmasi inputdan OLDIN turgani uchun "Takrorlanish"
   * kabi yorliq matniga bosish qiymatni jim-jitlik bilan 1 ga
   * KAMAYTIRARDI - amaliy sinovda tasdiqlandi.
   *
   * Yechim: `<input>` ni DOM tartibida BIRINCHI qilamiz (shunda label
   * kliki uni fokuslaydi - xavfsiz standart xatti-harakat), vizual
   * joylashuvni esa `order-*` bilan avvalgidek saqlaymiz.
   */
  return (
    <div className="flex items-center gap-1 rounded-control border border-control-edge bg-surface-2 p-1">
      <input
        type="number"
        inputMode="numeric"
        value={value}
        min={min}
        max={max}
        aria-label={label}
        onChange={(e) => onChange(clamp(Number(e.target.value) || min))}
        className="tnum order-2 w-full min-w-0 bg-transparent text-center text-[16px] font-semibold text-ink outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
      />
      <button
        type="button"
        onClick={() => step(-1)}
        disabled={value <= min}
        aria-label={label ? `${label}: kamaytirish` : "Kamaytirish"}
        className={cx(btn, "order-1")}
      >
        <Icon name="minus" size={18} />
      </button>
      {suffix && <span className="order-3 shrink-0 text-caption text-muted">{suffix}</span>}
      <button
        type="button"
        onClick={() => step(1)}
        disabled={value >= max}
        aria-label={label ? `${label}: oshirish` : "Oshirish"}
        className={cx(btn, "order-4")}
      >
        <Icon name="plus" size={18} />
      </button>
    </div>
  );
}

export function Switch({
  on,
  onToggle,
  label,
  disabled,
  busy = false,
}: {
  on: boolean;
  onToggle: () => void;
  /** Ekran o'quvchi uchun nom. Bermaslik tavsiya etilmaydi. */
  label?: string;
  disabled?: boolean;
  /** Server javobi kutilmoqda - qayta bosishni bloklaydi va buni ko'rsatadi. */
  busy?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      aria-busy={busy || undefined}
      disabled={disabled || busy}
      onClick={() => {
        haptics.press("light");
        onToggle();
      }}
      className={cx(
        "tap-44 relative h-7 w-12 shrink-0 rounded-pill",
        "transition-colors duration-base ease-standard",
        "disabled:opacity-45 disabled:pointer-events-none",
        FOCUS,
        on ? "bg-success" : "bg-interactive",
        busy && "opacity-60"
      )}
    >
      {/*
        `left` ni aniq beramiz. Usiz absolute element o'zining "static"
        o'rnidan hisoblanib, doira pill'dan tashqarida qolib ketardi.
        Yurish masofasi: 48 - 4 - 20 - 4 = 20px.
      */}
      <span
        className={cx(
          "absolute left-1 top-1 h-5 w-5 rounded-pill bg-white shadow-e1",
          "transition-transform duration-base ease-out",
          on ? "translate-x-5" : "translate-x-0"
        )}
        aria-hidden
      />
    </button>
  );
}

/* ------------------------------------------------------------------ *
 * Ma'lumot ko'rsatkichlari
 * ------------------------------------------------------------------ */
export function Ring({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value));
  const R = 34;
  const C = 2 * Math.PI * R;
  return (
    <div
      className="relative grid h-24 w-24 shrink-0 place-items-center"
      role="img"
      aria-label={`${label}: ${pct}%`}
    >
      <svg viewBox="0 0 80 80" className="h-24 w-24 -rotate-90" aria-hidden focusable="false">
        <circle cx="40" cy="40" r={R} fill="none" strokeWidth="8" className="stroke-surface-2" />
        <circle
          cx="40"
          cy="40"
          r={R}
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          className="stroke-accent transition-[stroke-dashoffset] duration-700 ease-out"
          strokeDasharray={C}
          strokeDashoffset={C - (pct / 100) * C}
        />
      </svg>
      <div className="absolute text-center" aria-hidden>
        <div className="tnum text-title-1 text-ink">{pct}%</div>
        <div className="mt-0.5 text-caption text-muted">{label}</div>
      </div>
    </div>
  );
}

/**
 * Yorliq (chapda) + qalin qiymat (o'ngda) qatori - statistika ro'yxatlari
 * uchun. Ilgari MemberDashboard ichida xususiy `Row` sifatida yozilgan
 * edi; Profil sheet ham aynan shu naqshga muhtoj bo'lgani uchun bu yerga
 * ko'chirildi.
 */
export function LabelValueRow({
  label,
  value,
  tone = "ink",
}: {
  label: string;
  value: ReactNode;
  tone?: "ink" | "warning" | "danger";
}) {
  const tones = { ink: "text-ink", warning: "text-warning", danger: "text-danger" };
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="truncate text-caption text-muted">{label}</span>
      <span className={cx("tnum shrink-0 text-callout font-bold", tones[tone])}>{value}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Bottom sheet
 *
 * STEP 1 da aniqlangan kamchiliklar tuzatildi:
 *   - role="dialog" + aria-modal + aria-labelledby
 *   - Escape bilan yopish
 *   - fokus tuzog'i (Tab sheet ichida qoladi)
 *   - yopilgach fokus avvalgi elementga qaytadi
 *   - Telegram BackButton bilan bog'landi: Android tizim "orqaga"
 *     imo-ishorasi endi sheet'ni yopadi, butun Mini App'ni emas
 *   - skroll qulfi modul darajasidagi hisoblagich bilan (ichma-ich
 *     sheet'larda ham to'g'ri tiklanadi)
 * ------------------------------------------------------------------ */
let scrollLocks = 0;
let savedOverflow = "";

function lockScroll() {
  if (scrollLocks === 0) {
    savedOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    /*
     * Modal ochilganda sarlavha va pastki panel `scrim` ostida qoladi -
     * ularning `backdrop-filter` qatlami ko'rinmaydi, lekin brauzer uni
     * baribir hisoblaydi. Super Admin ekranida bu uchta bir vaqtdagi
     * blur qatlami degani (sarlavha + pastki panel + sheet). Shu klass
     * ularni vaqtincha shaffof bo'lmagan holatga o'tkazadi: vizual farq
     * yo'q, bitta blur qatlami kamayadi.
     */
    document.body.classList.add("modal-open");
  }
  scrollLocks++;
}

function unlockScroll() {
  scrollLocks = Math.max(0, scrollLocks - 1);
  if (scrollLocks === 0) {
    document.body.style.overflow = savedOverflow;
    document.body.classList.remove("modal-open");
  }
}

const FOCUSABLE =
  'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])';

/*
 * Modal xatti-harakati: skroll qulfi, fokus tuzog'i, Escape, fokusni
 * qaytarish va Telegram BackButton. `Sheet` ham, `ConfirmDialog` ham
 * shu bitta amalga oshirishdan foydalanadi - ikki nusxa bo'lmasin.
 */
function useModalBehavior(
  open: boolean,
  close: () => void,
  panelRef: React.RefObject<HTMLElement>
) {
  const restoreRef = useRef<HTMLElement | null>(null);
  /*
   * XATOLIK TUZATILDI: `close` chaqiruv joyida inline funksiya
   * (`onClose={() => setOpenTask(null)}`), ya'ni ota-komponent har
   * qayta renderlanganda yangi identifikator oladi. U effekt deps'ida
   * turgani uchun effekt HAR RENDERDA qayta ishga tushardi va:
   *   1. `panel.focus()` qayta chaqirilib, foydalanuvchi fokusini
   *      o'g'irlardi (masalan navbat yuklanib bo'lgach);
   *   2. `restoreRef` panelning o'zi bilan qayta yozilib, oyna
   *      yopilganda fokus chaqirgan tugmaga emas, panelga qaytardi.
   * Eng so'nggi `close` ni ref'da saqlaymiz; effekt faqat `open`
   * o'zgarganda ishlaydi.
   */
  const closeRef = useRef(close);
  useEffect(() => {
    closeRef.current = close;
  });

  // Android tizim orqaga imo-ishorasi / Telegram BackButton
  useTelegramBackButton(open, close);

  useEffect(() => {
    if (!open) return;

    restoreRef.current = document.activeElement as HTMLElement | null;
    lockScroll();

    const panel = panelRef.current;
    /*
     * Fokusni panelning O'ZIGA beramiz, birinchi tugmaga emas. Aks holda
     * oyna ochilishi bilan "Yopish" (✕) tugmasi yoritilgan holda turadi -
     * bu foydalanuvchiga "yopish" ni taklif qilayotgandek ko'rinadi.
     * Panel `tabIndex={-1}` - dasturiy fokus oladi, lekin Tab tartibiga
     * qo'shilmaydi.
     */
    panel?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        closeRef.current();
        return;
      }
      if (e.key !== "Tab" || !panel) return;

      const nodes = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null
      );
      if (nodes.length === 0) return;

      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      unlockScroll();
      restoreRef.current?.focus?.();
    };
  }, [open, panelRef]);
}

export function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  // `useModalBehavior` eng so'nggi callback'ni ref'da saqlaydi, shuning
  // uchun bu yerda `useCallback` bilan identifikatorni barqarorlashtirish
  // shart emas edi - u hech narsa bermayotgan memoizatsiya edi.
  useModalBehavior(open, onClose, panelRef);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      {/* Qoplama: faqat qorayish, blur YO'Q - sheet'ning o'zi allaqachon
          blur qilyapti, ikkita backdrop o'tishi behuda xarajat bo'lardi. */}
      <div className="scrim absolute inset-0 animate-fadeIn" onClick={onClose} aria-hidden />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="glass-strong relative flex max-h-[88svh] w-full max-w-lg animate-sheetUp flex-col rounded-t-sheet shadow-e3 focus:outline-none"
      >
        <div className="relative flex shrink-0 items-center justify-between gap-3 border-b border-line px-gutter py-3">
          <span
            className="absolute inset-x-0 top-1.5 mx-auto h-1 w-10 rounded-pill bg-muted/40"
            aria-hidden
          />
          <h3 id={titleId} className="mt-1 min-w-0 truncate text-title-2 text-ink">
            {title}
          </h3>
          <IconButton name="x" label="Yopish" onClick={onClose} size="sm" className="mt-1" />
        </div>

        <div className="overflow-y-auto px-gutter py-4 pb-safe">{children}</div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Tasdiqlash oynasi
 *
 * Sheet emas, MARKAZIY dialog: qaytarib bo'lmaydigan amal uchun diqqatni
 * bir joyga to'plash kerak, pastdan chiqadigan panel esa "yana bir
 * varaq" kabi his qilinadi va tasodifan bosilishi osonroq.
 * ------------------------------------------------------------------ */
export function ConfirmDialog({
  open,
  onCancel,
  onConfirm,
  title,
  message,
  confirmLabel = "Tasdiqlash",
  cancelLabel = "Bekor qilish",
  destructive = false,
  busy = false,
}: {
  open: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  busy?: boolean;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descId = useId();

  // Ish bajarilayotganda (busy) oynani yopib bo'lmaydi - yarim yo'lda
  // to'xtatilgan amal foydalanuvchini chalg'itadi.
  const close = () => {
    if (!busy) onCancel();
  };
  useModalBehavior(open, close, panelRef);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[55] flex items-center justify-center px-gutter">
      <div className="scrim absolute inset-0 animate-fadeIn" onClick={close} aria-hidden />

      <div
        ref={panelRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        tabIndex={-1}
        className="glass-strong relative w-full max-w-sm animate-riseIn rounded-card p-5 shadow-e3 focus:outline-none"
      >
        <div
          className={cx(
            "mb-3 grid h-11 w-11 place-items-center rounded-control",
            destructive ? "bg-danger/16 text-danger" : "bg-accent/14 text-accent"
          )}
        >
          <Icon name={destructive ? "alert" : "info"} size={22} />
        </div>

        <h2 id={titleId} className="text-title-2 text-ink">
          {title}
        </h2>
        <p id={descId} className="mt-1.5 text-callout leading-relaxed text-ink-2">
          {message}
        </p>

        <div className="mt-5 flex gap-2.5">
          <Btn variant="outline" full onClick={close} disabled={busy}>
            {cancelLabel}
          </Btn>
          <Btn
            variant={destructive ? "destructive" : "primary"}
            full
            onClick={onConfirm}
            loading={busy}
          >
            {confirmLabel}
          </Btn>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Bo'sh / xato / yuklanish holatlari
 * ------------------------------------------------------------------ */

/**
 * API xatosi. Ilgari bunday holat UMUMAN yo'q edi: muvaffaqiyatsiz
 * so'rov "ma'lumot yo'q" bo'sh holati sifatida ko'rsatilardi.
 * Rang yagona signal emas - ikonka, sarlavha va matn ham bor.
 */
export function ErrorState({
  message,
  onRetry,
  title = "Yuklab bo'lmadi",
}: {
  message?: string | null;
  onRetry?: () => void;
  title?: string;
}) {
  return (
    <div className="rounded-card border border-danger/24 bg-danger/6 px-5 py-8 text-center">
      <div className="mb-3 flex justify-center text-danger">
        <Icon name="alert" size={28} />
      </div>
      <p className="text-headline text-ink">{title}</p>
      <p className="mx-auto mt-1.5 max-w-[34ch] text-caption leading-relaxed text-ink-2">
        {message || "Server bilan bog'lanishda muammo bo'ldi."}
      </p>
      {onRetry && (
        <div className="mt-4 flex justify-center">
          <Btn variant="outline" size="sm" icon="refresh" onClick={onRetry}>
            Qayta urinish
          </Btn>
        </div>
      )}
    </div>
  );
}

export function Empty({
  icon,
  iconName = "inbox",
  title,
  hint,
  action,
}: {
  /** Eski chaqiruvlar emoji satri berishi mumkin. */
  icon?: ReactNode;
  iconName?: IconName;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-card border border-dashed border-line bg-surface/50 px-6 py-10 text-center">
      <div className="mb-3 flex justify-center text-muted">
        {icon ?? <Icon name={iconName} size={28} />}
      </div>
      <p className="text-headline text-ink">{title}</p>
      {hint && <p className="mx-auto mt-1.5 max-w-[34ch] text-caption leading-relaxed text-muted">{hint}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
