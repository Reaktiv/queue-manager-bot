import { useEffect, useState } from "react";
import { api } from "../api/client";
import { QueueList } from "../components/QueueList";
import { Badge, Button, Card, EmptyState, LoadingSpinner } from "../components/ui";
import type { AuthUser, GroupSummary, MemberSummary, QueueEntry, TaskSummary } from "../types";

function formatDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatTodayForTimezone() {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tashkent",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  const parts = formatter.formatToParts(new Date());
  const year = parts.find((part) => part.type === "year")?.value ?? "1970";
  const month = parts.find((part) => part.type === "month")?.value ?? "01";
  const day = parts.find((part) => part.type === "day")?.value ?? "01";
  return `${year}-${month}-${day}`;
}

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

export function AdminDashboard({ user, group }: Props) {
  const [tasks, setTasks] = useState<TaskSummary[] | null>(null);
  const [members, setMembers] = useState<MemberSummary[]>([]);
  const [selectedTask, setSelectedTask] = useState<TaskSummary | null>(null);
  const [queue, setQueue] = useState<QueueEntry[]>([]);
  const [newTaskName, setNewTaskName] = useState("");
  const [creating, setCreating] = useState(false);
  const [scheduleIntervalDays, setScheduleIntervalDays] = useState(1);
  const [startDate, setStartDate] = useState(() => formatTodayForTimezone());
  const [reminderInterval, setReminderInterval] = useState(60);
  const [reminderStartHour, setReminderStartHour] = useState(8);
  const [reminderEndHour, setReminderEndHour] = useState(22);
  const [broadcastMsg, setBroadcastMsg] = useState("");
  const [broadcasting, setBroadcasting] = useState(false);

  const loadTasks = () => api.listTasks(group.id).then((res) => setTasks(res.data || []));
  const loadMembers = () => api.listMembers(group.id).then((res) => setMembers(res.data || []));

  useEffect(() => {
    loadTasks();
    loadMembers();
    setStartDate(formatTodayForTimezone());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [group.id]);

  useEffect(() => {
    if (selectedTask) {
      api.getQueuePreview(selectedTask.id).then((res) => setQueue(res.data || []));
    }
  }, [selectedTask]);

  async function handleCreateTask() {
    if (!newTaskName.trim()) return;
    setCreating(true);
    await api.createTask({
      telegram_id: user.telegram_id,
      group_id: group.id,
      name: newTaskName.trim(),
      require_photo: true,
      schedule_interval_days: Number(scheduleIntervalDays) || 1,
      start_date: startDate,
      reminder_interval_minutes: Number(reminderInterval) || 60,
      reminder_start_hour: Number(reminderStartHour) ?? 8,
      reminder_end_hour: Number(reminderEndHour) ?? 22,
    });
    setNewTaskName("");
    setScheduleIntervalDays(1);
    setReminderInterval(60);
    setReminderStartHour(8);
    setReminderEndHour(22);
    setCreating(false);
    loadTasks();
  }

  async function handleBroadcast() {
    if (!broadcastMsg.trim()) return;
    setBroadcasting(true);
    try {
      const res = await api.broadcastGroupMessage(group.id, {
        telegram_id: user.telegram_id,
        message: broadcastMsg.trim(),
      });
      if (res.success) {
        alert("Xabar muvaffaqiyatli yuborildi!");
        setBroadcastMsg("");
      } else {
        alert(`Xatolik: ${res.message}`);
      }
    } catch (e: any) {
      alert(`Xatolik yuz berdi: ${e.message || e}`);
    } finally {
      setBroadcasting(false);
    }
  }

  async function handleDeleteTask(taskId: number) {
    await api.deleteTask(taskId, user.telegram_id);
    setSelectedTask(null);
    loadTasks();
  }

  async function handleSkip(taskId: number) {
    await api.skipQueue(taskId, user.telegram_id);
    api.getQueuePreview(taskId).then((res) => setQueue(res.data || []));
  }

  async function toggleVacation(member: MemberSummary) {
    await api.setVacation(user.telegram_id, member.member_id, !member.is_on_vacation);
    loadMembers();
  }

  if (tasks === null) return <LoadingSpinner />;

  return (
    <div className="space-y-4 p-4">
      <div>
        <h2 className="text-lg font-semibold">👑 Admin panel</h2>
        <p className="text-sm text-tg-hint">{group.name}</p>
      </div>

      <section>
        <h3 className="mb-2 font-medium">➕ Yangi vazifa</h3>
        <Card className="space-y-3">
          <div>
            <label className="text-xs text-tg-hint block mb-1">Vazifa nomi</label>
            <input
              className="w-full rounded-lg border border-tg-hint/30 bg-transparent px-3 py-2 text-sm"
              placeholder="Masalan: Oshxona tozalash"
              value={newTaskName}
              onChange={(e) => setNewTaskName(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-tg-hint block mb-1">Har necha kunda?</label>
              <input
                type="number"
                min="1"
                className="w-full rounded-lg border border-tg-hint/30 bg-transparent px-3 py-2 text-sm text-tg-text"
                placeholder="1 = har kuni, 7 = har hafta"
                value={scheduleIntervalDays}
                onChange={(e) => setScheduleIntervalDays(Number(e.target.value) || 1)}
              />
            </div>

            <div>
              <label className="text-xs text-tg-hint block mb-1">Boshlanish sanasi</label>
              <input
                type="date"
                className="w-full rounded-lg border border-tg-hint/30 bg-transparent px-3 py-2 text-sm text-tg-text"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                style={{ colorScheme: "dark" }}
              />
            </div>
          </div>



          <div className="border-t border-tg-hint/15 pt-2 space-y-2">
            <h4 className="text-xs font-semibold text-tg-hint">🔔 Eslatma sozlamalari</h4>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-xs text-tg-hint block mb-1">Daqiqada (interval)</label>
                <input
                  type="number"
                  min="1"
                  className="w-full rounded-lg border border-tg-hint/30 bg-transparent px-3 py-2 text-sm text-tg-text"
                  value={reminderInterval}
                  onChange={(e) => setReminderInterval(Number(e.target.value) || 60)}
                />
              </div>
              <div>
                <label className="text-xs text-tg-hint block mb-1">Boshlash (soat)</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  className="w-full rounded-lg border border-tg-hint/30 bg-transparent px-3 py-2 text-sm text-tg-text"
                  value={reminderStartHour}
                  onChange={(e) => setReminderStartHour(Number(e.target.value) ?? 8)}
                />
              </div>
              <div>
                <label className="text-xs text-tg-hint block mb-1">Tugash (soat)</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  className="w-full rounded-lg border border-tg-hint/30 bg-transparent px-3 py-2 text-sm text-tg-text"
                  value={reminderEndHour}
                  onChange={(e) => setReminderEndHour(Number(e.target.value) ?? 22)}
                />
              </div>
            </div>
          </div>

          <Button onClick={handleCreateTask} disabled={creating || !newTaskName.trim() || scheduleIntervalDays < 1}>
            {creating ? "Yaratilmoqda..." : "Yaratish"}
          </Button>
        </Card>
      </section>

      <section>
        <h3 className="mb-2 font-medium">📢 Guruhga xabar yuborish (Broadcast)</h3>
        <Card className="space-y-3">
          <textarea
            className="w-full rounded-lg border border-tg-hint/30 bg-transparent px-3 py-2 text-sm text-tg-text focus:outline-none focus:border-tg-link"
            placeholder="Guruh a'zolariga yuboriladigan xabar matni..."
            rows={3}
            value={broadcastMsg}
            onChange={(e) => setBroadcastMsg(e.target.value)}
          />
          <Button
            onClick={handleBroadcast}
            disabled={broadcasting || !broadcastMsg.trim()}
          >
            {broadcasting ? "Yuborilmoqda..." : "📢 Barchaga yuborish"}
          </Button>
        </Card>
      </section>

      <section>
        <h3 className="mb-2 font-medium">📋 Vazifalar</h3>
        {tasks.length === 0 ? (
          <EmptyState message="Hali vazifalar yo'q" />
        ) : (
          <div className="space-y-2">
            {tasks.map((task) => (
              <Card key={task.id} onClick={() => setSelectedTask(task)}>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium">{task.name}</span>
                    {task.is_active && (
                      <p className="text-xs text-tg-hint mt-0.5">
                        {formatTaskDate(task.current_turn_date)}: {task.current_assignee || "Hech kim"}
                      </p>
                    )}
                  </div>
                  {!task.is_active && <Badge tone="danger">Faol emas</Badge>}
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      {selectedTask && (
        <section>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-medium">👀 "{selectedTask.name}" navbati</h3>
            <button className="text-xs text-tg-hint underline" onClick={() => setSelectedTask(null)}>
              yopish
            </button>
          </div>
          <QueueList entries={queue} members={members} />
          <div className="mt-2 flex gap-2">
            <Button variant="secondary" onClick={() => handleSkip(selectedTask.id)}>
              ⏭ Skip
            </Button>
            <Button variant="danger" onClick={() => handleDeleteTask(selectedTask.id)}>
              🗑 O'chirish
            </Button>
          </div>
        </section>
      )}

      <section>
        <h3 className="mb-2 font-medium">👥 A'zolar</h3>
        <div className="space-y-2">
          {members.map((member) => (
            <Card key={member.member_id} className="flex items-center justify-between">
              <div>
                <p className="font-medium">
                  {member.role === "admin" ? "👑 " : "👤 "}
                  {member.full_name}
                </p>
                {member.is_on_vacation && <Badge tone="warning">🏖 Dam olishda</Badge>}
              </div>
              <button
                className="text-xs text-tg-link underline"
                onClick={() => toggleVacation(member)}
              >
                {member.is_on_vacation ? "Qaytarish" : "Dam olish"}
              </button>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
