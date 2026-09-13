import type { ReactNode } from "react";
import { haptics } from "../hooks/useTelegramViewport";
import { Icon } from "./Icon";
import { cx } from "./ui";

/*
 * Mobil ma'lumot ro'yxati - `Table` ning o'rnini bosadi.
 *
 * MUAMMO (STEP 1 auditi, P0-2): `Table` `overflow-x-auto` ichida edi va
 * chaqiruvchilar ustunlarni `max-w-[9rem]`, `max-w-[6.5rem]` bilan
 * kesardi. 360px ekranda natija: ismlar ham kesilgan, ham yon tomonga
 * skroll qilish kerak. Vertikal skroll qiladigan Telegram WebView
 * ichidagi gorizontal skroll konteyneri esa "surib yopish" imo-ishorasi
 * bilan to'qnashadi.
 *
 * YECHIM: ustunlar emas, ikki qatorli qatorlar. Har bir qator:
 *
 *   [leading]  Sarlavha ................. [meta]
 *              Izoh                       [trailing]
 *
 * Ma'lumot ustuvorligi: sarlavha (birlamchi) > izoh (ikkilamchi) >
 * meta (uchlamchi). Uzun ismlar/username/ID layoutni buzmaydi, chunki
 * har bir matn bloki `min-w-0` + `truncate` ichida.
 *
 * Bu "karta uyumi" emas: butun ro'yxat BITTA yuza, qatorlar ingichka
 * chiziq bilan ajratiladi. Ma'lumotga boy ro'yxatlar shaffof emas
 * (opaque) - glass faqat suzuvchi xrom uchun.
 */

export function DataList({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cx(
        "overflow-hidden rounded-card bg-surface shadow-e1",
        "divide-y divide-line",
        className
      )}
    >
      {children}
    </div>
  );
}

export function ListRow({
  leading,
  title,
  subtitle,
  meta,
  trailing,
  onClick,
  ariaLabel,
  highlighted = false,
  index,
}: {
  /** Avatar yoki ikonka */
  leading?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  /** O'ng tomondagi uchlamchi ma'lumot (sana, son) */
  meta?: ReactNode;
  /** O'ng tomondagi belgi yoki boshqaruv */
  trailing?: ReactNode;
  onClick?: () => void;
  ariaLabel?: string;
  /** "Bu siz" kabi holat uchun - rang YAGONA signal emas, chap chekkada chiziq ham bor */
  highlighted?: boolean;
  /**
   * Ro'yxatdagi tartib raqami. Berilsa, qator juda kichik kechikish bilan
   * paydo bo'ladi (bosqichma-bosqich). Kechikish 6 ta qatordan keyin
   * to'xtaydi - uzun ro'yxatda oxirgi element kutib qolmasin.
   * `prefers-reduced-motion` yoqilganda global CSS qoidasi animatsiyani
   * o'chiradi, shuning uchun bu yerda qo'shimcha tekshiruv shart emas.
   */
  index?: number;
}) {
  const body = (
    <>
      {highlighted && (
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 w-[3px] rounded-r-pill bg-accent"
        />
      )}

      {leading && <span className="shrink-0">{leading}</span>}

      <span className="flex min-w-0 flex-1 flex-col gap-0.5 text-left">
        <span className="truncate text-body font-semibold text-ink">{title}</span>
        {subtitle && <span className="truncate text-caption text-muted">{subtitle}</span>}
      </span>

      {(meta || trailing) && (
        <span className="flex shrink-0 items-center gap-2">
          {meta && <span className="tnum whitespace-nowrap text-caption text-muted">{meta}</span>}
          {trailing}
          {onClick && <Icon name="chevron-right" size={18} className="text-muted" />}
        </span>
      )}
      {onClick && !meta && !trailing && (
        <Icon name="chevron-right" size={18} className="shrink-0 text-muted" />
      )}
    </>
  );

  const shared = cx(
    "relative flex w-full items-center gap-3 px-3.5 py-3",
    highlighted && "bg-accent/6",
    index !== undefined && "animate-riseIn"
  );

  const style =
    index !== undefined
      ? { animationDelay: `${Math.min(index, 6) * 40}ms` }
      : undefined;

  // Bosiladigan qator HAQIQIY <button> bo'ladi: klaviatura, fokus va
  // ekran o'quvchi qo'llab-quvvatlashi shu bilan avtomatik keladi.
  // Ilgari bu `<tr onClick>` edi - sichqoncha/barmoqdan boshqa hech
  // narsa bilan ishlatib bo'lmasdi.
  if (onClick) {
    return (
      <button
        type="button"
        style={style}
        aria-label={ariaLabel}
        onClick={() => {
          haptics.press("light");
          onClick();
        }}
        className={cx(
          shared,
          "text-left transition-colors duration-fast ease-out active:bg-interactive",
          "outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent"
        )}
      >
        {body}
      </button>
    );
  }

  return (
    <div className={shared} style={style}>
      {body}
    </div>
  );
}
