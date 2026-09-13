import { cx } from "./ui";

/*
 * Har bir ekran uchun ALOHIDA yuklanish shakli.
 *
 * Ilgari hamma joyda bitta `PageSkeleton` ishlatilardi: 24px blok +
 * ikkita 20px plitka + uchta 16px qator. Bu hech bir sahifaning haqiqiy
 * tuzilishiga mos kelmasdi, shuning uchun ma'lumot kelganda layout
 * sakrab ketardi. Endi skelet kelayotgan kontentning shaklini takrorlaydi.
 *
 * Barchasi `aria-hidden` - ekran o'quvchi uchun ota-elementdagi
 * `role="status"` yetarli; bo'sh to'rtburchaklarni o'qish foydasiz.
 */

function Block({ className }: { className?: string }) {
  return <div className={cx("shimmer animate-shimmer rounded-card", className)} aria-hidden />;
}

/** Ro'yxat qatorlari: avatar + ikki qator matn. */
export function ListSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-card bg-surface shadow-e1" aria-hidden>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className={cx("flex items-center gap-3 px-3.5 py-3", i > 0 && "border-t border-line")}
        >
          <Block className="h-10 w-10 shrink-0 rounded-pill" />
          <div className="min-w-0 flex-1 space-y-1.5">
            <Block className="h-3.5 w-2/5 rounded-control" />
            <Block className="h-3 w-3/5 rounded-control" />
          </div>
          <Block className="h-3 w-12 shrink-0 rounded-control" />
        </div>
      ))}
    </div>
  );
}

/** Ko'rsatkichlar tasmasi: 3 yoki 4 ustun. */
export function StatRailSkeleton({ columns = 3 }: { columns?: number }) {
  const grid = columns >= 4;
  return (
    <div
      className={cx(
        "overflow-hidden rounded-card bg-surface shadow-e1",
        grid ? "grid grid-cols-2 divide-x divide-y divide-line" : "flex divide-x divide-line"
      )}
      aria-hidden
    >
      {Array.from({ length: columns }).map((_, i) => (
        <div key={i} className={cx("px-3 py-3", grid ? "" : "flex-1")}>
          <Block className="h-7 w-10 rounded-control" />
          <Block className="mt-2 h-2.5 w-full rounded-control" />
        </div>
      ))}
    </div>
  );
}

/** A'zo paneli: hero + statistika + ro'yxat. */
export function MemberSkeleton() {
  return (
    <div className="space-y-section" role="status" aria-label="Yuklanmoqda">
      <Block className="h-28 w-full rounded-hero" />
      <div className="space-y-3">
        <Block className="h-5 w-36 rounded-control" />
        <div className="flex items-center gap-4 rounded-card bg-surface p-4 shadow-e1">
          <Block className="h-24 w-24 shrink-0 rounded-pill" />
          <div className="flex-1 space-y-2.5">
            <Block className="h-3 w-full rounded-control" />
            <Block className="h-3 w-4/5 rounded-control" />
            <Block className="h-3 w-3/5 rounded-control" />
          </div>
        </div>
      </div>
      <ListSkeleton rows={3} />
    </div>
  );
}

/** Guruh tanlash ekrani. */
export function GroupsSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Yuklanmoqda">
      <Block className="h-16 w-full" />
      <Block className="h-3 w-28 rounded-control" />
      <ListSkeleton rows={2} />
    </div>
  );
}

/** Ilova birinchi marta ochilayotgani: sarlavha + kontent. */
export function BootSkeleton() {
  return (
    <div className="px-gutter pt-4" role="status" aria-label="Yuklanmoqda">
      <div className="flex items-center gap-2.5 pb-4">
        <Block className="h-10 w-10 shrink-0 rounded-pill" />
        <div className="flex-1 space-y-1.5">
          <Block className="h-3.5 w-1/3 rounded-control" />
          <Block className="h-2.5 w-1/2 rounded-control" />
        </div>
      </div>
      <GroupsSkeleton />
    </div>
  );
}
