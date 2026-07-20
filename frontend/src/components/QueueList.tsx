import type { MemberSummary, QueueEntry } from "../types";
import { Badge, Card } from "./ui";

interface Props {
  entries: QueueEntry[];
  members: MemberSummary[];
}

function formatQueueDate(value?: string | null) {
  if (!value) return "Sana yo'q";
  const [year, month, day] = value.split("-");
  if (!year || !month || !day) return value;

  const monthName = new Intl.DateTimeFormat("en", {
    month: "long",
    timeZone: "Asia/Tashkent",
  })
    .format(new Date(`${year}-${month}-${day}T00:00:00Z`))
    .toLowerCase();

  return `${Number(day)}-${monthName}`;
}

export function QueueList({ entries, members }: Props) {
  const memberById = new Map(members.map((m) => [m.member_id, m]));

  if (entries.length === 0) {
    return <p className="text-tg-hint text-sm">Navbat bo'sh</p>;
  }

  return (
    <div className="space-y-2">
      {entries.slice(0, 3).map((entry, index) => {
        const member = memberById.get(entry.member_id);
        return (
          <Card key={entry.id} className="flex items-center justify-between">
            <div>
              <p className="text-xs text-tg-hint">{index + 1}. {formatQueueDate(entry.scheduled_date)}</p>
              <p className="font-medium">{member?.full_name || `A'zo #${entry.member_id}`}</p>
            </div>
            {entry.is_locked && <Badge tone="warning">🔒 Qulflangan</Badge>}
          </Card>
        );
      })}
    </div>
  );
}
