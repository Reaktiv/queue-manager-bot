import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";
import { cx } from "./ui";

/*
 * Ko'rsatkichlar tasmasi.
 *
 * Ilgari: uchta alohida `Stat` kartasi, har birida ramka + soya + emoji.
 * 360x640 ekranda ular ekranning yuqori uchdan birini egallab, asosiy
 * kontentni pastga surib yuborardi - va ko'rsatilgan sonlar baribir
 * pastdagi ro'yxatdan qayta hisoblangan edi.
 *
 * Endi: BITTA yuza, ichida ustunlar. Chegaralar soni 3 tadan 1 taga
 * tushdi, balandlik ~40% qisqardi, sonlar esa vizual langar sifatida
 * kattaroq bo'lib qoldi.
 *
 * 4 ta ko'rsatkich 360px da bitta qatorga sig'maydi, shuning uchun
 * 2x2 panjaraga o'tadi.
 */

export interface StatItem {
  value: ReactNode;
  label: string;
  icon?: IconName;
  tone?: "ink" | "accent" | "success" | "warning" | "danger";
}

const TONES: Record<NonNullable<StatItem["tone"]>, string> = {
  ink: "text-ink",
  accent: "text-accent",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
};

export function StatRail({ items }: { items: StatItem[] }) {
  const grid = items.length >= 4;

  return (
    <div
      className={cx(
        "overflow-hidden rounded-card bg-surface shadow-e1",
        grid
          ? "grid grid-cols-2 divide-x divide-y divide-line"
          : "flex divide-x divide-line"
      )}
    >
      {items.map((item) => (
        <div
          key={item.label}
          className={cx("min-w-0 px-3 py-3", grid ? "" : "flex-1")}
        >
          {/*
            Son BIRINCHI - u vizual langar (5-bo'lim talabi). Yorliq
            tagida, va u KESILMAYDI: 360px da "Dam olishda" bitta qatorga
            sig'maydi, shuning uchun ikki qatorga o'tishiga ruxsat beramiz.
            Ilgari bu `truncate` edi va "DAM OLIS..." bo'lib ko'rinardi.
          */}
          <div
            className={cx("tnum text-display leading-none", TONES[item.tone ?? "ink"])}
          >
            {item.value}
          </div>
          <div className="mt-1.5 flex items-start gap-1 text-muted">
            {item.icon && <Icon name={item.icon} size={12} className="mt-px shrink-0" />}
            <span className="text-micro uppercase leading-tight">{item.label}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
