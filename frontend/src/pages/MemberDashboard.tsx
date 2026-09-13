import { useState } from "react";
import { api } from "../api/client";
import { AppMain } from "../components/AppScreen";
import { ProfileSheet } from "../components/ProfileSheet";
import { DataList, ListRow } from "../components/DataList";
import { Icon, IconTile } from "../components/Icon";
import {
  Avatar,
  Empty,
  ErrorState,
  LabelValueRow,
  Ring,
  SectionHead,
  Surface,
} from "../components/ui";
import { ListSkeleton, MemberSkeleton } from "../components/Skeletons";
import { useAsyncData } from "../hooks/useAsyncData";
import { formatDay, hasAssignee, humanizeDaysLeft } from "../lib/format";
import type { AuthUser, GroupSummary, MemberStatistics, TaskSummary } from "../types";

interface Props {
  user: AuthUser;
  group: GroupSummary;
}

export function MemberDashboard({ user, group }: Props) {
  const [profileOpen, setProfileOpen] = useState(false);
  const myTasks = useAsyncData<TaskSummary[]>(
    () => api.getMyTasks(user.telegram_id, group.id),
    [user.telegram_id, group.id]
  );
  const allTasks = useAsyncData<TaskSummary[]>(() => api.listTasks(group.id), [group.id]);
  const stats = useAsyncData<MemberStatistics>(
    () => api.getMemberStatistics(group.member_id),
    [group.member_id]
  );

  const mine = myTasks.data ?? [];
  const activeNow = mine.filter((t) => t.is_active_now);
  const upcoming = mine.filter((t) => !t.is_active_now);
  const activeTasks = (allTasks.data ?? []).filter((t) => t.is_active);

  return (
    <AppMain>
      <div className="space-y-section">
        {/* ----------------------------------------------------------------
            Bugungi holat. Ilgari bu to'liq gradient blok + to'xtovsiz
            `animate-ping` nuqta edi (u ota-element `relative` bo'lmagani
            uchun noto'g'ri joyda chizilardi). Endi: tonal yuza, aniq
            chekka rangi va statik nuqta. Rang yagona signal emas -
            ikonka va matn ham holatni aytadi.
           ---------------------------------------------------------------- */}
        {myTasks.loading ? (
          <MemberSkeleton />
        ) : myTasks.error ? (
          <ErrorState message={myTasks.error} onRetry={myTasks.reload} />
        ) : activeNow.length > 0 ? (
          <section className="animate-riseIn overflow-hidden rounded-hero border border-accent/24 bg-accent/12">
            <div className="flex items-center gap-2 px-4 pt-4">
              <span className="h-2 w-2 shrink-0 rounded-pill bg-accent" aria-hidden />
              <p className="text-micro uppercase text-accent">Navbat sizda</p>
            </div>

            <ul className="mt-2 space-y-1 px-4">
              {activeNow.map((t) => (
                <li key={t.id} className="text-title-1 leading-tight text-ink">
                  {t.name}
                </li>
              ))}
            </ul>

            <p className="mt-3 flex items-start gap-2 border-t border-accent/20 px-4 py-3 text-caption leading-relaxed text-ink-2">
              <Icon name="camera" size={16} className="mt-px shrink-0 text-accent" />
              Botga o'ting va bajarganingizni tasdiqlash uchun rasm yuboring.
            </p>
          </section>
        ) : (
          <section className="animate-riseIn flex items-center gap-3 rounded-hero bg-surface p-4 shadow-e1">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-control bg-success/16 text-success">
              <Icon name="check" size={22} />
            </span>
            <div className="min-w-0">
              <p className="text-headline text-ink">Navbat sizda emas</p>
              <p className="mt-0.5 text-caption text-muted">
                Hozircha bemalol dam olishingiz mumkin.
              </p>
            </div>
          </section>
        )}

        {/* --- Statistika: halqa + qatorlar ---
            Yuklanish paytida bu bo'lim umuman ko'rsatilmaydi: yuqoridagi
            `MemberSkeleton` allaqachon shu shaklni egallab turadi, ikkita
            skelet birga chiqsa ekran shovqinli bo'lardi. */}
        {stats.loading ? null : stats.error ? (
          <ErrorState message={stats.error} onRetry={stats.reload} />
        ) : (
          stats.data && (
            <section>
              <SectionHead title="Statistikangiz" sub="Shu guruhdagi ko'rsatkichlar" />
              <Surface
                interactive
                onClick={() => setProfileOpen(true)}
                className="flex items-center gap-4"
              >
                <Ring value={stats.data.completion_rate} label="bajarildi" />
                <div className="grid min-w-0 flex-1 gap-2.5">
                  <LabelValueRow label="Bajarilgan" value={`${stats.data.completed} / ${stats.data.total}`} />
                  <div className="h-px bg-line" />
                  <LabelValueRow label="Joriy jarima" value={stats.data.current_penalty} tone="warning" />
                  <div className="h-px bg-line" />
                  <LabelValueRow label="O'tkazib yuborilgan" value={stats.data.total_missed} tone="danger" />
                </div>
              </Surface>
              <p className="mt-2 flex items-center gap-1 px-1 text-caption text-accent">
                <Icon name="chevron-right" size={14} />
                To'liq profilni (yulduzli daraja) ko'rish
              </p>
            </section>
          )
        )}

        {/* --- Kelgusi navbatlarim --- */}
        {upcoming.length > 0 && (
          <section>
            <SectionHead title="Kelgusi navbatlaringiz" sub="Sizga biriktirilgan vazifalar" />
            <DataList>
              {upcoming.map((t, i) => (
                <ListRow
                  key={t.id}
                  index={i}
                  leading={
                    <span className="grid h-10 w-10 place-items-center rounded-control bg-surface-2 text-muted">
                      <Icon name="tasks" size={18} />
                    </span>
                  }
                  title={t.name}
                  subtitle={
                    t.days_left !== undefined
                      ? humanizeDaysLeft(t.days_left)
                      : "Sana aniqlanmagan"
                  }
                  trailing={
                    t.days_left !== undefined ? (
                      <span className="text-right">
                        <span className="tnum block text-title-2 leading-none text-accent">
                          {t.days_left}
                        </span>
                        <span className="block text-micro normal-case tracking-normal text-muted">
                          kun
                        </span>
                      </span>
                    ) : undefined
                  }
                />
              ))}
            </DataList>
          </section>
        )}

        {/* --- Guruhdagi barcha navbatlar --- */}
        <section>
          <SectionHead
            title="Guruh navbatlari"
            sub={allTasks.loading ? undefined : `${activeTasks.length} ta faol vazifa`}
          />
          {allTasks.loading ? (
            <ListSkeleton rows={3} />
          ) : allTasks.error ? (
            <ErrorState message={allTasks.error} onRetry={allTasks.reload} />
          ) : activeTasks.length === 0 ? (
            <Empty
              iconName="inbox"
              title="Vazifalar yo'q"
              hint="Guruh admini hali vazifa yaratmagan."
            />
          ) : (
            <DataList>
              {activeTasks.map((t, i) => {
                const isMine = t.current_assignee === user.full_name;
                return (
                  <ListRow
                    key={t.id}
                    index={i}
                    highlighted={isMine}
                    leading={
                      hasAssignee(t.current_assignee) ? (
                        <Avatar name={t.current_assignee} size="sm" />
                      ) : (
                        <IconTile name="user" />
                      )
                    }
                    title={t.name}
                    subtitle={
                      hasAssignee(t.current_assignee)
                        ? isMine
                          ? "Navbat sizda"
                          : t.current_assignee
                        : "Hech kim biriktirilmagan"
                    }
                    meta={formatDay(t.current_turn_date)}
                  />
                );
              })}
            </DataList>
          )}
        </section>
      </div>

      <ProfileSheet
        open={profileOpen}
        onClose={() => setProfileOpen(false)}
        memberId={group.member_id}
        fullName={user.full_name}
        role={group.role}
      />
    </AppMain>
  );
}
