import { useState } from "react";
import { api } from "./api/client";
import { AppHeader, AppScreen } from "./components/AppScreen";
import { Avatar, Btn, IconButton, ToastHost } from "./components/ui";
import { BootSkeleton } from "./components/Skeletons";
import { Icon } from "./components/Icon";
import { useAsyncData } from "./hooks/useAsyncData";
import { useTelegramAuth } from "./hooks/useTelegramAuth";
import { useTelegramViewport } from "./hooks/useTelegramViewport";
import { AdminDashboard } from "./pages/AdminDashboard";
import { GroupSelector } from "./pages/GroupSelector";
import { MemberDashboard } from "./pages/MemberDashboard";
import { SuperAdminDashboard } from "./pages/SuperAdminDashboard";
import type { GroupSummary } from "./types";

/**
 * Ilova ochilmagan holat: Telegram tashqarisida yoki auth ishlamaganda.
 * Bu yagona "boshi berk" ekran - bu yerdan davom etib bo'lmaydi.
 */
function FatalScreen({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-8 text-center">
      <span className="grid h-16 w-16 place-items-center rounded-hero bg-danger/16 text-danger">
        <Icon name="alert" size={30} />
      </span>
      <div>
        <h1 className="text-title-2 text-ink">Ilova ochilmadi</h1>
        <p className="mx-auto mt-2 max-w-[32ch] text-callout leading-relaxed text-ink-2">
          {message}
        </p>
      </div>
      {onRetry && (
        <Btn variant="outline" icon="refresh" onClick={onRetry}>
          Qayta urinish
        </Btn>
      )}
    </div>
  );
}

export default function App() {
  // Viewport / mavzu / haptika integratsiyasi - ILDIZDA bir marta.
  useTelegramViewport();

  const { loading, error, user } = useTelegramAuth();
  const [activeGroup, setActiveGroup] = useState<GroupSummary | null>(null);
  const [superAdminView, setSuperAdminView] = useState(false);

  const groups = useAsyncData<GroupSummary[]>(
    user ? () => api.listMyGroups(user.telegram_id) : null,
    [user?.telegram_id]
  );

  /*
   * Qobiq DOIM bir xil: fon, aurora, xavfsiz zonalar, markazlangan ustun.
   * Faqat ichidagi kontent almashadi. Shu tufayli yuklanish -> kontent
   * o'tishida fon sakramaydi.
   */
  const shell = (content: React.ReactNode) => (
    <AppScreen>
      <ToastHost />
      {content}
    </AppScreen>
  );

  if (loading) return shell(<BootSkeleton />);
  if (error) return shell(<FatalScreen message={error} />);
  if (!user) return shell(<BootSkeleton />);

  if (superAdminView) {
    return shell(<SuperAdminDashboard onBack={() => setSuperAdminView(false)} />);
  }

  if (!activeGroup) {
    return shell(
      <GroupSelector
        user={user}
        groups={groups.data}
        loading={groups.loading}
        error={groups.error}
        onRetry={groups.reload}
        onSelect={setActiveGroup}
        onOpenSuperAdmin={user.is_super_admin ? () => setSuperAdminView(true) : undefined}
      />
    );
  }

  const isAdmin = activeGroup.role === "admin";

  return shell(
    <>
      {/*
        Guruh sarlavhasi: bitta qator, uchta ma'lumot darajasi.
          1-daraja  guruh nomi
          2-daraja  rol + vaqt zonasi (ikkalasi ham amaliy ahamiyatga ega)
        Foydalanuvchining O'Z ismi ataylab olib tashlandi - u eng kam
        foydali element edi va guruh nomi bilan raqobatlashardi
        (ism GroupSelector'dagi salomlashuvda ko'rinadi).
        Ilgari pastda "Asia/Tashkent" uchun alohida futer bor edi -
        u butun bir qator vertikal joyni faqat shu matn uchun sarflardi.
      */}
      <AppHeader>
        <div className="flex items-center gap-2.5 pt-1">
          <IconButton
            name="chevron-left"
            label="Guruhlarga qaytish"
            onClick={() => setActiveGroup(null)}
          />
          <Avatar name={activeGroup.name} size="sm" crown={isAdmin} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-headline leading-tight text-ink">{activeGroup.name}</p>
            <p className="truncate text-caption leading-tight text-muted">
              {isAdmin ? "Admin" : "A'zo"} · {activeGroup.timezone}
            </p>
          </div>
          {user.is_super_admin && (
            <IconButton
              name="crown"
              label="Super Admin panel"
              tone="accent"
              onClick={() => setSuperAdminView(true)}
            />
          )}
        </div>
      </AppHeader>

      {isAdmin ? (
        <AdminDashboard user={user} group={activeGroup} />
      ) : (
        <MemberDashboard user={user} group={activeGroup} />
      )}
    </>
  );
}
