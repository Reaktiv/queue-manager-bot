import { formatDay } from "../lib/format";
import type { MemberSummary, QueueEntry } from "../types";
import { Icon } from "./Icon";
import { Avatar, Badge, Empty } from "./ui";

interface Props {
  entries: QueueEntry[];
  members: MemberSummary[];
}

/**
 * Navbat - vertikal vaqt chizig'i: kim, qachon va hozir kimda ekani
 * bir qarashda ko'rinadi.
 *
 * Ilgarigidek faqat birinchi 5 ta ko'rsatiladi, lekin endi qolganlari
 * borligi ham aytiladi (ilgari ular jim-jitlik bilan yashirilardi).
 */
export function QueueList({ entries, members }: Props) {
  const memberById = new Map(members.map((m) => [m.member_id, m]));
  const LIMIT = 5;
  const visible = entries.slice(0, LIMIT);
  const hidden = Math.max(0, entries.length - LIMIT);

  if (visible.length === 0) {
    return (
      <Empty
        iconName="users"
        title="Navbat bo'sh"
        hint="Bu vazifaga hali hech kim biriktirilmagan."
      />
    );
  }

  return (
    <div>
      <ol className="relative space-y-1">
        {/* chap tomondagi ulovchi chiziq */}
        <span className="absolute bottom-6 left-[19px] top-6 w-px bg-line" aria-hidden />

        {visible.map((entry, i) => {
          const member = memberById.get(entry.member_id);
          const name = member?.full_name || `A'zo #${entry.member_id}`;
          const isNow = i === 0;

          return (
            <li key={entry.id} className="relative flex items-center gap-3 py-1.5">
              <span
                className={`relative z-10 grid h-10 w-10 shrink-0 place-items-center rounded-pill text-caption font-bold ring-4 ring-ground ${
                  isNow ? "bg-accent-solid text-accent-ink" : "bg-surface-2 text-muted"
                }`}
                aria-hidden
              >
                {i + 1}
              </span>

              <div className="flex min-w-0 flex-1 items-center gap-2.5 rounded-control bg-surface px-3 py-2.5 shadow-e1">
                <Avatar name={name} size="sm" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-body font-semibold text-ink">{name}</p>
                  <p className="tnum text-caption text-muted">{formatDay(entry.scheduled_date)}</p>
                </div>
                {isNow && (
                  <Badge tone="accent" dot>
                    Navbatda
                  </Badge>
                )}
                {entry.is_locked && !isNow && (
                  <span className="shrink-0 text-muted" title="Qulflangan">
                    <Icon name="lock" size={16} label="Qulflangan" />
                  </span>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      {hidden > 0 && (
        <p className="mt-2.5 pl-[52px] text-caption text-muted">
          va yana {hidden} ta a'zo navbatda
        </p>
      )}
    </div>
  );
}
