import { haptics } from "../hooks/useTelegramViewport";
import { Icon, type IconName } from "./Icon";
import { cx } from "./ui";

/*
 * Navigatsiya.
 *
 * Ilgari ilovada ikkita ALOQASIZ naqsh bor edi: AdminDashboard'da
 * `Segmented`, SuperAdminDashboard'da gorizontal skroll qiladigan
 * emoji-pill qatori. Ikkalasi ham boshqacha ko'rinar va boshqacha
 * his qilinardi.
 *
 * Endi bitta faol-holat tili (aksent rang + yassi indikator + bir xil
 * harakat), lekin IKKITA joylashuv - element soniga qarab tanlanadi:
 *
 *   <= 3 element  -> `Tabs`        (yuqorida, segmented, teng kenglik)
 *   4-5 element   -> `BottomTabs`  (pastda, barmoq yetadigan joyda)
 *
 * 5 ta bo'limni 360px kenglikdagi bitta segmented qatorga tiqish
 * o'qib bo'lmas yorliqlar beradi; gorizontal skroll esa Telegram'ning
 * "yon tomonga surib yopish" imo-ishorasi bilan to'qnashadi. Shuning
 * uchun 5 ta uchun pastki panel - u hammasini bir vaqtda ko'rsatadi,
 * skrollsiz.
 */

export interface TabItem<T extends string> {
  value: T;
  label: string;
  icon?: IconName;
}

/* ------------------------------------------------------------------ *
 * Segmented - 2-3 bo'lim uchun
 * ------------------------------------------------------------------ */
export function Tabs<T extends string>({
  value,
  onChange,
  items,
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  items: TabItem<T>[];
  label?: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={label ?? "Bo'limlar"}
      className="flex gap-1 rounded-card bg-surface-2 p-1"
    >
      {items.map((item) => {
        const selected = value === item.value;
        return (
          <button
            key={item.value}
            role="tab"
            aria-selected={selected}
            onClick={() => {
              if (selected) return;
              haptics.select();
              onChange(item.value);
            }}
            className={cx(
              "flex min-h-tap flex-1 items-center justify-center gap-1.5 rounded-control px-2",
              "text-callout font-semibold",
              "transition-[background-color,color] duration-base ease-standard",
              "outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface-2",
              selected ? "bg-raised text-ink shadow-e1" : "text-muted active:bg-ground/40"
            )}
          >
            {item.icon && <Icon name={item.icon} size={16} className="shrink-0" />}
            <span className="truncate">{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Pastki panel - 4-5 bo'lim uchun
 *
 * Panel `fixed`, shuning uchun oqimda joy egallamaydi. Kontent uning
 * ostida qolib ketmasligi uchun komponent o'zi bilan birga bo'sh
 * joy ajratuvchi (spacer) ham qaytaradi - uni sahifa oxiriga qo'ying.
 * ------------------------------------------------------------------ */
export function BottomTabs<T extends string>({
  value,
  onChange,
  items,
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  items: TabItem<T>[];
  label?: string;
}) {
  return (
    <>
      {/* Oqimdagi joy: fixed panel kontentning oxirini yopmasin */}
      <div
        aria-hidden
        style={{ height: "calc(3.75rem + env(safe-area-inset-bottom))" }}
      />

      <nav
        role="tablist"
        aria-label={label ?? "Bo'limlar"}
        /* `fixed` viewport'ga nisbatan joylashadi, shuning uchun ilova
           ustunining kengligi va markazi qo'lda takrorlanadi. */
        className="app-chrome glass-subtle fixed bottom-0 left-1/2 z-40 w-full max-w-lg -translate-x-1/2 px-1 pb-safe"
        style={{ transform: "translateX(-50%) translateZ(0)" }}
      >
        <div className="flex items-stretch">
          {items.map((item) => {
            const selected = value === item.value;
            return (
              <button
                key={item.value}
                role="tab"
                aria-selected={selected}
                onClick={() => {
                  if (selected) return;
                  haptics.select();
                  onChange(item.value);
                }}
                className={cx(
                  "relative flex min-h-tap flex-1 flex-col items-center justify-center gap-1 rounded-control px-1 py-2",
                  "transition-colors duration-base ease-standard",
                  "outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1 focus-visible:ring-offset-surface",
                  selected ? "text-accent" : "text-muted"
                )}
              >
                {/* Faol indikator: yuqorida qisqa yassi chiziq.
                    Rang yagona signal emas - yorliq ham qalinlashadi. */}
                <span
                  aria-hidden
                  className={cx(
                    "absolute inset-x-3 top-0 h-0.5 rounded-pill transition-opacity duration-base",
                    selected ? "bg-accent opacity-100" : "opacity-0"
                  )}
                />
                {item.icon && <Icon name={item.icon} size={20} />}
                <span
                  className={cx(
                    "max-w-full truncate text-micro normal-case tracking-normal",
                    selected ? "font-bold" : "font-medium"
                  )}
                >
                  {item.label}
                </span>
              </button>
            );
          })}
        </div>
      </nav>
    </>
  );
}
