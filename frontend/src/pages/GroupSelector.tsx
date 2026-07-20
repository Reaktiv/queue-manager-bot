import { Card, EmptyState } from "../components/ui";
import type { GroupSummary } from "../types";

interface Props {
  groups: GroupSummary[];
  onSelect: (group: GroupSummary) => void;
}

export function GroupSelector({ groups, onSelect }: Props) {
  if (groups.length === 0) {
    return (
      <div className="p-4">
        <EmptyState message="Siz hali hech qanday guruhga a'zo emassiz. Botda /join yoki /creategroup buyrug'ini ishlating." />
      </div>
    );
  }

  return (
    <div className="space-y-2 p-4">
      <h2 className="mb-2 text-lg font-semibold">Guruhni tanlang</h2>
      {groups.map((group) => (
        <Card key={group.id} onClick={() => onSelect(group)}>
          <div className="flex items-center justify-between">
            <span className="font-medium">{group.name}</span>
            <span className="text-xs text-tg-hint">
              {group.role === "admin" ? "👑 Admin" : "👤 A'zo"}
            </span>
          </div>
        </Card>
      ))}
    </div>
  );
}
