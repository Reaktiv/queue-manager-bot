import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Card, EmptyState, LoadingSpinner } from "../components/ui";
import type { AuthUser, GroupSummary, MemberStatistics, TaskSummary } from "../types";

interface Props {
  user: AuthUser;
  group: GroupSummary;
}

function formatTaskDate(value?: string | null) {
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

export function MemberDashboard({ user, group }: Props) {
  const [myTasks, setMyTasks] = useState<TaskSummary[] | null>(null);
  const [allTasks, setAllTasks] = useState<TaskSummary[]>([]);
  const [stats, setStats] = useState<MemberStatistics | null>(null);

  useEffect(() => {
    api.getMyTasks(user.telegram_id, group.id).then((res) => setMyTasks(res.data || []));
    api.listTasks(group.id).then((res) => setAllTasks(res.data || []));
    api.getMemberStatistics(group.member_id).then((res) => setStats(res.data));
  }, [user.telegram_id, group.id, group.member_id]);

  if (myTasks === null) return <LoadingSpinner />;

  return (
    <div className="space-y-4 p-4">
      <div>
        <h2 className="text-lg font-semibold">👋 {user.full_name}</h2>
        <p className="text-sm text-tg-hint">{group.name}</p>
      </div>

      <section>
        <h3 className="mb-2 font-medium">🙋 Mening vazifalarim</h3>
        {myTasks.length === 0 ? (
          <EmptyState message="Hozircha navbat sizda emas 🎉" />
        ) : (
          <div className="space-y-2">
            {myTasks.map((task) => {
              let hintText = "Siz hozir navbatdasiz - botga o'ting va rasm yuboring";
              if (!task.is_active_now && task.days_left !== undefined && task.days_left > 0) {
                const days = task.days_left;
                if (days === 1) {
                  hintText = "Navbatingizga 1 kun qoldi (Ertaga)";
                } else if (days % 7 === 0) {
                  const weeks = days / 7;
                  hintText = `Navbatingizga ${weeks} hafta bor`;
                } else {
                  hintText = `Navbatingizga hali ${days} kun bor`;
                }
              }
              return (
                <Card key={task.id}>
                  <p className="font-medium">📋 {task.name}</p>
                  <p className="text-xs text-tg-hint">{hintText}</p>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      <section>
        <h3 className="mb-2 font-medium">👥 Guruhdagi barcha navbatlar</h3>
        {allTasks.length === 0 ? (
          <EmptyState message="Guruhda hali vazifalar yo'q" />
        ) : (
          <div className="space-y-2">
            {allTasks.filter(t => t.is_active).map((task) => (
              <Card key={task.id}>
                <div className="flex items-center justify-between">
                  <span className="font-medium">📋 {task.name}</span>
                  <span className="text-sm font-semibold text-tg-button">
                    {formatTaskDate(task.current_turn_date)}: {task.current_assignee || "Hech kim"}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      {stats && (
        <section>
          <h3 className="mb-2 font-medium">📊 Statistikam</h3>
          <Card>
            <div className="grid grid-cols-2 gap-3 text-center">
              <div>
                <p className="text-2xl font-bold text-tg-button">{stats.completion_rate}%</p>
                <p className="text-xs text-tg-hint">Bajarish foizi</p>
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {stats.completed}/{stats.total}
                </p>
                <p className="text-xs text-tg-hint">Bajarilgan</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-yellow-600">{stats.current_penalty}</p>
                <p className="text-xs text-tg-hint">Joriy jarima</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-red-500">{stats.total_missed}</p>
                <p className="text-xs text-tg-hint">O'tkazib yuborilgan</p>
              </div>
            </div>
          </Card>
        </section>
      )}
    </div>
  );
}
