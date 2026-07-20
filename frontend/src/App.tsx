import { useEffect, useState } from "react";
import { api } from "./api/client";
import { LoadingSpinner } from "./components/ui";
import { useTelegramAuth } from "./hooks/useTelegramAuth";
import { AdminDashboard } from "./pages/AdminDashboard";
import { GroupSelector } from "./pages/GroupSelector";
import { MemberDashboard } from "./pages/MemberDashboard";
import { SuperAdminDashboard } from "./pages/SuperAdminDashboard";
import type { GroupSummary } from "./types";

export default function App() {
  const { loading, error, user } = useTelegramAuth();
  const [groups, setGroups] = useState<GroupSummary[] | null>(null);
  const [activeGroup, setActiveGroup] = useState<GroupSummary | null>(null);
  const [showSuperAdmin, setShowSuperAdmin] = useState(false);

  useEffect(() => {
    if (user) {
      api.listMyGroups(user.telegram_id).then((res) => setGroups(res.data || []));
    }
  }, [user]);

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 text-center">
        <p className="text-tg-hint">{error}</p>
      </div>
    );
  }

  if (!user || groups === null) return <LoadingSpinner />;

  // Super Admin (Bot Owner) - guruhlardan mustaqil global panel.
  // Guruh a'zosi ham bo'lsa, u istalgan vaqt oddiy panelga qaytishi mumkin.
  if (user.is_super_admin && showSuperAdmin) {
    return (
      <div>
        <button
          className="w-full bg-tg-secondaryBg px-4 py-2 text-left text-xs text-tg-link underline"
          onClick={() => setShowSuperAdmin(false)}
        >
          ← Oddiy panelga qaytish
        </button>
        <SuperAdminDashboard />
      </div>
    );
  }

  if (!activeGroup) {
    return (
      <div>
        {user.is_super_admin && (
          <div className="p-4">
            <button
              className="w-full rounded-xl bg-tg-button px-4 py-2.5 font-medium text-tg-buttonText"
              onClick={() => setShowSuperAdmin(true)}
            >
              👑 Super Admin panelga o'tish
            </button>
          </div>
        )}
        <GroupSelector groups={groups} onSelect={setActiveGroup} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-tg-bg text-tg-text">
      <div className="flex items-center justify-between border-b border-tg-hint/20 px-4 py-2">
        <button className="text-xs text-tg-link underline" onClick={() => setActiveGroup(null)}>
          ← Guruhlar
        </button>
        <span className="text-xs text-tg-hint">{activeGroup.name}</span>
      </div>

      {activeGroup.role === "admin" ? (
        <AdminDashboard user={user} group={activeGroup} />
      ) : (
        <MemberDashboard user={user} group={activeGroup} />
      )}
    </div>
  );
}

