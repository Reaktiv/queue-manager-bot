import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Badge, Button, Card, EmptyState, LoadingSpinner } from "../components/ui";
import type {
  ErrorLog,
  SuperAdminGroupSummary,
  SuperAdminUserSummary,
  SystemStats,
} from "../types";

type Tab = "overview" | "groups" | "users" | "logs" | "broadcast";

export function SuperAdminDashboard() {
  const [tab, setTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [groups, setGroups] = useState<SuperAdminGroupSummary[] | null>(null);
  const [users, setUsers] = useState<SuperAdminUserSummary[] | null>(null);
  const [logs, setLogs] = useState<ErrorLog[] | null>(null);
  const [broadcastText, setBroadcastText] = useState("");
  const [broadcastResult, setBroadcastResult] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const loadStats = () => api.getSystemStats().then((res) => setStats(res.data));

  useEffect(() => {
    loadStats();
  }, []);

  useEffect(() => {
    if (tab === "groups" && groups === null) {
      api.listAllGroups().then((res) => setGroups(res.data || []));
    }
    if (tab === "users" && users === null) {
      api.listAllUsers().then((res) => setUsers(res.data || []));
    }
    if (tab === "logs" && logs === null) {
      api.listErrorLogs().then((res) => setLogs(res.data || []));
    }
  }, [tab, groups, users, logs]);

  async function toggleMaintenance() {
    if (!stats) return;
    await api.setMaintenanceMode(!stats.maintenance_mode);
    loadStats();
  }

  async function handleBroadcast() {
    if (!broadcastText.trim()) return;
    setSending(true);
    const res = await api.broadcastMessage(broadcastText.trim());
    if (res.data) {
      setBroadcastResult(`✅ ${res.data.sent}/${res.data.total} foydalanuvchiga yuborildi`);
    }
    setBroadcastText("");
    setSending(false);
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "📊 Umumiy" },
    { key: "groups", label: "👥 Guruhlar" },
    { key: "users", label: "🙋 Userlar" },
    { key: "logs", label: "🔴 Xatolar" },
    { key: "broadcast", label: "📢 Broadcast" },
  ];

  return (
    <div className="min-h-screen bg-tg-bg text-tg-text">
      <div className="border-b border-tg-hint/20 px-4 py-2">
        <h1 className="text-lg font-semibold">👑 Super Admin</h1>
      </div>

      <div className="flex gap-1 overflow-x-auto border-b border-tg-hint/20 px-2 py-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm ${
              tab === t.key ? "bg-tg-button text-tg-buttonText" : "text-tg-hint"
            }`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="p-4">
        {tab === "overview" && (
          <>
            {!stats ? (
              <LoadingSpinner />
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <Card>
                    <p className="text-2xl font-bold">{stats.total_groups}</p>
                    <p className="text-xs text-tg-hint">Jami guruhlar</p>
                  </Card>
                  <Card>
                    <p className="text-2xl font-bold">{stats.total_users}</p>
                    <p className="text-xs text-tg-hint">Jami foydalanuvchilar</p>
                  </Card>
                  <Card>
                    <p className="text-2xl font-bold">{stats.total_active_tasks}</p>
                    <p className="text-xs text-tg-hint">Faol vazifalar</p>
                  </Card>
                  <Card>
                    <p className="text-2xl font-bold">{stats.total_completions}</p>
                    <p className="text-xs text-tg-hint">Jami bajarishlar</p>
                  </Card>
                </div>

                <Card>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">🛠 Maintenance Mode</p>
                      <p className="text-xs text-tg-hint">
                        Yoqilsa, oddiy foydalanuvchilar uchun tizim vaqtincha o'chiriladi
                      </p>
                    </div>
                    {stats.maintenance_mode ? (
                      <Badge tone="danger">Yoqilgan</Badge>
                    ) : (
                      <Badge tone="success">O'chirilgan</Badge>
                    )}
                  </div>
                  <div className="mt-3">
                    <Button
                      variant={stats.maintenance_mode ? "secondary" : "danger"}
                      onClick={toggleMaintenance}
                    >
                      {stats.maintenance_mode ? "O'chirish" : "Yoqish"}
                    </Button>
                  </div>
                </Card>
              </div>
            )}
          </>
        )}

        {tab === "groups" && (
          <>
            {groups === null ? (
              <LoadingSpinner />
            ) : groups.length === 0 ? (
              <EmptyState message="Hali guruhlar yo'q" />
            ) : (
              <div className="space-y-2">
                {groups.map((g) => (
                  <Card key={g.id}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{g.name}</p>
                        <p className="text-xs text-tg-hint">
                          {g.member_count} a'zo &middot; {g.timezone}
                        </p>
                      </div>
                      {!g.is_active && <Badge tone="danger">Faol emas</Badge>}
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

        {tab === "users" && (
          <>
            {users === null ? (
              <LoadingSpinner />
            ) : (
              <div className="space-y-2">
                {users.map((u) => (
                  <Card key={u.id}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">
                          {u.is_super_admin ? "👑 " : ""}
                          {u.full_name}
                        </p>
                        <p className="text-xs text-tg-hint">
                          @{u.username || "—"} &middot; id: {u.telegram_id}
                        </p>
                      </div>
                      {!u.is_active && <Badge tone="danger">Bloklangan</Badge>}
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

        {tab === "logs" && (
          <>
            {logs === null ? (
              <LoadingSpinner />
            ) : logs.length === 0 ? (
              <EmptyState message="Xatolar yo'q 🎉" />
            ) : (
              <div className="space-y-2">
                {logs.map((log) => (
                  <Card key={log.id}>
                    <div className="flex items-center justify-between">
                      <Badge tone="danger">{log.level}</Badge>
                      <span className="text-xs text-tg-hint">
                        {new Date(log.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="mt-1 text-sm">{log.message}</p>
                    {log.context && <p className="mt-1 text-xs text-tg-hint">{log.context}</p>}
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

        {tab === "broadcast" && (
          <Card className="space-y-2">
            <p className="font-medium">📢 Barcha foydalanuvchilarga xabar</p>
            <textarea
              className="w-full rounded-lg border border-tg-hint/30 bg-transparent px-3 py-2 text-sm"
              rows={4}
              placeholder="Xabar matnini kiriting..."
              value={broadcastText}
              onChange={(e) => setBroadcastText(e.target.value)}
            />
            <Button onClick={handleBroadcast} disabled={sending || !broadcastText.trim()}>
              {sending ? "Yuborilmoqda..." : "Yuborish"}
            </Button>
            {broadcastResult && <p className="text-sm text-tg-hint">{broadcastResult}</p>}
          </Card>
        )}
      </div>
    </div>
  );
}
