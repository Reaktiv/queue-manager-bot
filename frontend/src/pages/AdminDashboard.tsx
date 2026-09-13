import { useState } from "react";
import { api } from "../api/client";
import { AppMain } from "../components/AppScreen";
import { DataList, ListRow } from "../components/DataList";
import { Icon, IconTile, type IconName } from "../components/Icon";
import { QueueList } from "../components/QueueList";
import { ListSkeleton, StatRailSkeleton } from "../components/Skeletons";
import { StatRail } from "../components/StatRail";
import { Tabs } from "../components/Tabs";
import {
  Avatar,
  Badge,
  Btn,
  ConfirmDialog,
  Empty,
  ErrorState,
  Field,
  SectionHead,
  Sheet,
  Switch,
  TextArea,
  toast,
} from "../components/ui";
import { useAsyncData } from "../hooks/useAsyncData";
import { formatDay, hasAssignee } from "../lib/format";
import type { AuthUser, GroupSummary, MemberSummary, QueueEntry, TaskSummary } from "../types";
import { CreateTaskSheet } from "./CreateTaskSheet";
import { ProfileSheet } from "../components/ProfileSheet";

interface Props {
  user: AuthUser;
  group: GroupSummary;
}

type Pane = "tasks" | "members" | "broadcast";

export function AdminDashboard({ user, group }: Props) {
  const [pane, setPane] = useState<Pane>("tasks");

  const tasks = useAsyncData<TaskSummary[]>("group-tasks", () => api.listTasks(group.id), [
    group.id,
  ]);
  const members = useAsyncData<MemberSummary[]>(
    "group-members",
    () => api.listMembers(group.id),
    [group.id]
  );

  const [createOpen, setCreateOpen] = useState(false);
  const [openTask, setOpenTask] = useState<TaskSummary | null>(null);
  const [openMember, setOpenMember] = useState<MemberSummary | null>(null);
  const [profileMember, setProfileMember] = useState<MemberSummary | null>(null);

  const [confirmDelete, setConfirmDelete] = useState<TaskSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [confirmDemote, setConfirmDemote] = useState<MemberSummary | null>(null);
  const [demoting, setDemoting] = useState(false);
  /*
   * Bir vaqtda bitta mutatsiya. Ilgari "Skip" tugmasi va a'zo kalitlari
   * hech qanday kutish holatiga ega emas edi: tez ikki marta bosilsa
   * navbat IKKI marta surilardi (ya'ni bir a'zo sababsiz o'tkazib
   * yuborilardi), kalitlar esa server javobi bilan poyga qilardi.
   */
  const [skipping, setSkipping] = useState(false);
  const [memberBusy, setMemberBusy] = useState<"vacation" | "role" | null>(null);

  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);

  /* Navbat ham boshqa so'rovlar kabi yuklanish/xato/qayta urinish holatiga ega.
     Ilgari u oddiy useEffect + setState edi va xato holati umuman yo'q edi. */
  const queue = useAsyncData<QueueEntry[]>(
    "queue-preview",
    openTask ? () => api.getQueuePreview(openTask.id) : null,
    [openTask?.id]
  );

  const taskList = tasks.data ?? [];
  const memberList = members.data ?? [];
  /*
   * XATOLIK: `openTask` sheet ochilgan paytdagi ESKI obyekt havolasini
   * saqlaydi. "Skip" bosilganda `tasks.reload()` ro'yxatni yangilaydi,
   * lekin `openTask`'ning o'zi hech qachon yangilanmasdi - natijada
   * navbat ("Navbat" bo'limi, mustaqil `queue.reload()` orqali) yangi
   * holatni ko'rsatsa ham, pastdagi "Sozlamalar" bo'limidagi "Keyingi
   * navbat" sanasi eskirgan qiymatda qolib ketardi.
   * Yechim: sheet ichida har doim `taskList`dagi ENG YANGI nusxani
   * ko'rsatamiz; topilmasa (masalan o'chirilgan bo'lsa) eski qiymatga
   * tushamiz - shu payt sheet allaqachon yopilish jarayonida bo'ladi.
   */
  const activeTask = openTask ? taskList.find((t) => t.id === openTask.id) ?? openTask : null;

  /* ---------------------------- amallar ---------------------------- */

  async function removeTask() {
    if (!confirmDelete) return;
    setDeleting(true);
    const res = await api.deleteTask(confirmDelete.id, user.telegram_id);
    setDeleting(false);
    setConfirmDelete(null);
    if (!res.success) return toast.err(res.message || "O'chirib bo'lmadi");
    toast.ok("Vazifa o'chirildi");
    setOpenTask(null);
    tasks.reload();
  }

  async function skip(taskId: number) {
    if (skipping) return;
    setSkipping(true);
    const res = await api.skipQueue(taskId, user.telegram_id);
    setSkipping(false);
    if (!res.success) return toast.err(res.message || "Skip bajarilmadi");
    toast.ok("Navbat keyingi a'zoga o'tdi");
    queue.reload();
    tasks.reload();
  }

  async function toggleVacation(m: MemberSummary) {
    if (memberBusy) return;
    setMemberBusy("vacation");
    const res = await api.setVacation(user.telegram_id, m.member_id, !m.is_on_vacation);
    setMemberBusy(null);
    if (!res.success) return toast.err(res.message || "O'zgartirib bo'lmadi");
    toast.ok(
      m.is_on_vacation ? `${m.full_name} navbatga qaytdi` : `${m.full_name} dam olishga chiqdi`
    );
    setOpenMember((prev) =>
      prev && prev.member_id === m.member_id ? { ...prev, is_on_vacation: !m.is_on_vacation } : prev
    );
    members.reload();
  }

  async function applyRole(m: MemberSummary, next: "admin" | "member") {
    setMemberBusy("role");
    const res = await api.setMemberRole(group.id, m.member_id, user.telegram_id, next);
    setMemberBusy(null);
    if (!res.success) return toast.err(res.message || "Rolni o'zgartirib bo'lmadi");
    toast.ok(next === "admin" ? `${m.full_name} admin bo'ldi` : `${m.full_name} oddiy a'zo bo'ldi`);
    setOpenMember((prev) =>
      prev && prev.member_id === m.member_id ? { ...prev, role: next } : prev
    );
    members.reload();
  }

  /*
   * Admin huquqini BERISH qaytariladigan, past xavfli amal - darhol bajariladi.
   * Admin huquqini OLIB QO'YISH esa oqibatli: o'z huquqini olib qo'ygan admin
   * uni o'ziga qaytara olmaydi. Shuning uchun faqat shu yo'nalish tasdiqlanadi.
   * (Backend oxirgi adminni tushirishni allaqachon bloklaydi - biz uni
   * takrorlamaymiz, xabari toast orqali ko'rsatiladi.)
   */
  function toggleAdmin(m: MemberSummary) {
    if (memberBusy) return;
    if (m.role === "admin") setConfirmDemote(m);
    else void applyRole(m, "admin");
  }

  async function confirmDemoteNow() {
    if (!confirmDemote) return;
    setDemoting(true);
    await applyRole(confirmDemote, "member");
    setDemoting(false);
    setConfirmDemote(null);
  }

  async function broadcast() {
    if (!msg.trim()) return;
    setSending(true);
    const res = await api.broadcastGroupMessage(group.id, {
      telegram_id: user.telegram_id,
      message: msg.trim(),
    });
    setSending(false);
    if (!res.success) return toast.err(res.message || "Xabar yuborilmadi");
    toast.ok("Xabar guruhga yuborildi");
    setMsg("");
  }

  /* ---------------------------- ko'rinish ---------------------------- */

  const activeCount = taskList.filter((t) => t.is_active).length;
  const onVacation = memberList.filter((m) => m.is_on_vacation).length;
  const firstLoad = tasks.loading && members.loading;

  return (
    <AppMain>
      <div className="space-y-4">
        {firstLoad ? (
          <StatRailSkeleton />
        ) : (
          <StatRail
            items={[
              { label: "Faol vazifa", value: activeCount, icon: "tasks", tone: "accent" },
              { label: "A'zolar", value: memberList.length, icon: "users" },
              { label: "Dam olishda", value: onVacation, icon: "umbrella", tone: "warning" },
            ]}
          />
        )}

        <Tabs
          value={pane}
          onChange={setPane}
          label="Admin bo'limlari"
          items={[
            { value: "tasks", label: "Vazifalar", icon: "tasks" },
            { value: "members", label: "A'zolar", icon: "users" },
            { value: "broadcast", label: "Xabar", icon: "megaphone" },
          ]}
        />

        {/* ------------------------- VAZIFALAR ------------------------- */}
        {pane === "tasks" && (
          <section className="animate-fadeIn">
            <SectionHead
              title="Vazifalar"
              sub="Navbat va sozlamalarni ko'rish uchun bosing"
              action={
                <Btn size="sm" icon="plus" onClick={() => setCreateOpen(true)}>
                  Yangi
                </Btn>
              }
            />

            {tasks.loading ? (
              <ListSkeleton rows={3} />
            ) : tasks.error ? (
              <ErrorState message={tasks.error} onRetry={tasks.reload} />
            ) : taskList.length === 0 ? (
              <Empty
                iconName="calendar"
                title="Hali vazifa yo'q"
                hint="Birinchi navbat vazifasini yarating - guruhning barcha faol a'zolari avtomatik navbatga qo'yiladi."
                action={
                  <Btn size="sm" icon="plus" onClick={() => setCreateOpen(true)}>
                    Vazifa yaratish
                  </Btn>
                }
              />
            ) : (
              <DataList>
                {taskList.map((t, i) => (
                  <ListRow
                    key={t.id}
                    index={i}
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
                        ? `Navbatda: ${t.current_assignee}`
                        : "Hech kim biriktirilmagan"
                    }
                    meta={formatDay(t.current_turn_date)}
                    trailing={!t.is_active ? <Badge tone="neutral">O'chiq</Badge> : undefined}
                    onClick={() => setOpenTask(t)}
                    ariaLabel={`${t.name} vazifasini ochish`}
                  />
                ))}
              </DataList>
            )}
          </section>
        )}

        {/* ------------------------- A'ZOLAR ------------------------- */}
        {pane === "members" && (
          <section className="animate-fadeIn">
            <SectionHead title="A'zolar" sub="Rol va dam olish holatini boshqarish" />

            {members.loading ? (
              <ListSkeleton rows={3} />
            ) : members.error ? (
              <ErrorState message={members.error} onRetry={members.reload} />
            ) : memberList.length === 0 ? (
              <Empty
                iconName="users"
                title="A'zolar yo'q"
                hint="Botdagi /mygroups buyrug'i taklif kodini ko'rsatadi - uni a'zolarga yuboring."
              />
            ) : (
              <DataList>
                {memberList.map((m, i) => (
                  <ListRow
                    key={m.member_id}
                    index={i}
                    leading={<Avatar name={m.full_name} crown={m.role === "admin"} />}
                    title={m.full_name}
                    subtitle={
                      <>
                        {m.role === "admin" ? "Admin" : "A'zo"}
                        {m.is_on_vacation && <span className="text-warning"> · Dam olishda</span>}
                      </>
                    }
                    trailing={
                      m.is_on_vacation ? (
                        <Icon
                          name="umbrella"
                          size={18}
                          label="Dam olishda"
                          className="text-warning"
                        />
                      ) : undefined
                    }
                    onClick={() => setOpenMember(m)}
                    ariaLabel={`${m.full_name} sozlamalari`}
                  />
                ))}
              </DataList>
            )}
          </section>
        )}

        {/* ------------------------- XABAR ------------------------- */}
        {pane === "broadcast" && (
          <section className="animate-fadeIn space-y-3">
            <SectionHead title="Guruhga xabar" sub="Bot orqali yetkaziladi" />

            {/* Kim oladi - aniq aytiladi. Backend xabarni HAR BIR a'zoga
                shaxsiy chatga yuboradi va guruh chati bog'langan bo'lsa
                unga ham yuboradi. Frontend guruh chati bog'langanini
                bilmaydi, shuning uchun faqat bilgan narsasini aytamiz. */}
            <div className="flex items-start gap-2.5 rounded-control bg-surface-2 px-3 py-2.5">
              <Icon name="info" size={16} className="mt-px shrink-0 text-accent" />
              <p className="text-caption leading-relaxed text-ink-2">
                Xabar <b className="font-semibold text-ink">{memberList.length} a'zoning</b> har
                biriga bot orqali shaxsiy xabar sifatida boradi. Guruh chati bog'langan bo'lsa,
                u yerga ham yuboriladi.
              </p>
            </div>

            <Field label="Xabar matni" hint={`${msg.length} / 1000 belgi`}>
              <TextArea
                rows={6}
                maxLength={1000}
                placeholder="Masalan: Ertaga soat 10:00 da umumiy yig'ilish bo'ladi."
                value={msg}
                onChange={(e) => setMsg(e.target.value)}
              />
            </Field>

            {/*
              Yuborish tugmasi ATAYLAB matn maydonining bevosita tagida.
              Ekranning pastiga mahkamlangan panel Android'da klaviatura
              ochilganda uning ostida qolib ketishi mumkin; bu yerda esa
              tugma matn maydoni bilan birga suriladi.
            */}
            <Btn
              full
              size="lg"
              icon="megaphone"
              onClick={broadcast}
              loading={sending}
              disabled={!msg.trim()}
            >
              {sending ? "Yuborilmoqda…" : `${memberList.length} a'zoga yuborish`}
            </Btn>
          </section>
        )}
      </div>

      {/* ------------------------- SHEET: yangi vazifa ------------------------- */}
      <CreateTaskSheet
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        user={user}
        group={group}
        onCreated={tasks.reload}
      />

      {/* ------------------------- SHEET: vazifa ------------------------- */}
      <Sheet open={!!openTask} onClose={() => setOpenTask(null)} title={activeTask?.name ?? ""}>
        {activeTask && (
          <div className="space-y-5">
            <section>
              <SheetLabel>Navbat</SheetLabel>
              {queue.loading ? (
                <ListSkeleton rows={3} />
              ) : queue.error ? (
                <ErrorState message={queue.error} onRetry={queue.reload} />
              ) : (
                <QueueList entries={queue.data ?? []} members={memberList} />
              )}
            </section>

            {/*
              Sozlamalar `GET /tasks/group/{id}` javobida allaqachon bor edi,
              lekin hech qachon ko'rsatilmagan - admin vazifa qanday
              sozlanganini bilish uchun uni o'chirib qayta yaratishi kerak edi.
              Yangi so'rov yo'q, mavjud ma'lumot ishlatiladi.
            */}
            <section>
              <SheetLabel>Sozlamalar</SheetLabel>
              <div className="overflow-hidden rounded-card bg-surface-2">
                <InfoRow
                  icon="bell"
                  label="Eslatma oralig'i"
                  value={formatInterval(activeTask)}
                />
                <InfoRow icon="clock" label="Eslatma vaqti" value={formatWindow(activeTask)} />
                <InfoRow
                  icon="calendar"
                  label="Keyingi navbat"
                  value={formatDay(activeTask.current_turn_date)}
                />
                <InfoRow
                  icon={activeTask.is_active ? "check" : "x"}
                  label="Holati"
                  value={activeTask.is_active ? "Faol" : "O'chirilgan"}
                  tone={activeTask.is_active ? "success" : "muted"}
                />
              </div>
            </section>

            {/* Ish oqimini tushuntirish: bu qoidalar backendda amal qiladi,
                lekin interfeysda hech qayerda aytilmagan edi. */}
            <section>
              <SheetLabel>Qanday ishlaydi</SheetLabel>
              <ul className="space-y-2 rounded-card bg-surface-2 p-3.5">
                <Rule icon="lock">
                  Navbat qulflangan: boshidagi a'zo bajarmaguncha keyingisiga o'tmaydi. Kun o'tsa
                  ham vazifa o'sha a'zoda qoladi va jarima ball qo'shiladi.
                </Rule>
                <Rule icon="camera">
                  A'zo vazifani <b className="font-semibold text-ink">bot orqali</b>, rasm yuborib
                  yakunlaydi. Guruh a'zolari ovoz beradi - ko'pchilik tasdiqlasa navbat suriladi.
                </Rule>
                <Rule icon="umbrella">
                  Dam olishdagi a'zolar navbatdan avtomatik o'tkazib yuboriladi.
                </Rule>
              </ul>
            </section>

            <div className="flex gap-2.5 border-t border-line pt-4">
              <Btn
                variant="outline"
                full
                icon="skip"
                loading={skipping}
                onClick={() => skip(activeTask.id)}
              >
                Skip
              </Btn>
              <Btn
                variant="destructive"
                full
                icon="trash"
                onClick={() => setConfirmDelete(activeTask)}
              >
                O'chirish
              </Btn>
            </div>
          </div>
        )}
      </Sheet>

      {/* ------------------------- SHEET: a'zo ------------------------- */}
      <Sheet
        open={!!openMember}
        onClose={() => setOpenMember(null)}
        title={openMember?.full_name ?? ""}
      >
        {openMember && (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => {
                setProfileMember(openMember);
                setOpenMember(null);
              }}
              className="flex w-full items-center gap-3 rounded-control bg-surface-2 p-3.5 text-left transition-colors duration-fast ease-out active:bg-interactive"
            >
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-control bg-surface text-warning">
                <Icon name="star" size={18} fill="currentColor" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-body font-semibold text-ink">Profilni ko'rish</p>
                <p className="mt-0.5 text-caption text-muted">Yulduzli daraja va statistikasi</p>
              </div>
              <Icon name="chevron-right" size={18} className="text-muted" />
            </button>

            <ToggleRow
              icon="umbrella"
              title="Dam olishda"
              hint="Yoqilsa, a'zo navbatdan avtomatik o'tkazib yuboriladi va unga eslatma kelmaydi"
              on={openMember.is_on_vacation}
              busy={memberBusy === "vacation"}
              disabled={memberBusy !== null}
              onToggle={() => toggleVacation(openMember)}
            />
            <ToggleRow
              icon="crown"
              title="Admin huquqi"
              hint="Vazifa yaratish va o'chirish, navbatni boshqarish, a'zolarni sozlash va xabar yuborish"
              on={openMember.role === "admin"}
              busy={memberBusy === "role"}
              disabled={memberBusy !== null}
              onToggle={() => toggleAdmin(openMember)}
            />
          </div>
        )}
      </Sheet>

      {/* ------------------------- SHEET: a'zo profili ------------------------- */}
      <ProfileSheet
        open={!!profileMember}
        onClose={() => setProfileMember(null)}
        memberId={profileMember?.member_id ?? null}
        fullName={profileMember?.full_name ?? ""}
        role={profileMember?.role ?? "member"}
      />

      {/* ------------------------- Tasdiqlashlar ------------------------- */}
      <ConfirmDialog
        open={!!confirmDelete}
        onCancel={() => setConfirmDelete(null)}
        onConfirm={removeTask}
        destructive
        busy={deleting}
        title="Vazifa o'chirilsinmi?"
        message={`"${confirmDelete?.name ?? ""}" vazifasi va uning navbati o'chiriladi. Buni qaytarib bo'lmaydi.`}
        confirmLabel="O'chirish"
      />

      <ConfirmDialog
        open={!!confirmDemote}
        onCancel={() => setConfirmDemote(null)}
        onConfirm={confirmDemoteNow}
        destructive
        busy={demoting}
        title="Admin huquqi olinsinmi?"
        message={`${confirmDemote?.full_name ?? ""} endi vazifa yarata olmaydi, navbatni boshqara olmaydi va xabar yubora olmaydi.`}
        confirmLabel="Huquqni olish"
      />
    </AppMain>
  );
}

/* ------------------------------------------------------------------ *
 * Kichik yordamchilar - faqat shu sahifada ishlatiladi
 * ------------------------------------------------------------------ */

function SheetLabel({ children }: { children: React.ReactNode }) {
  return <p className="mb-2 text-micro uppercase text-muted">{children}</p>;
}

function InfoRow({
  icon,
  label,
  value,
  tone = "ink",
}: {
  icon: IconName;
  label: string;
  value: string;
  tone?: "ink" | "success" | "muted";
}) {
  const tones = { ink: "text-ink", success: "text-success", muted: "text-muted" };
  return (
    <div className="flex items-center gap-3 px-3.5 py-2.5 [&+&]:border-t [&+&]:border-line">
      <Icon name={icon} size={16} className="shrink-0 text-muted" />
      <span className="min-w-0 flex-1 truncate text-caption text-muted">{label}</span>
      <span className={`shrink-0 text-caption font-semibold ${tones[tone]}`}>{value}</span>
    </div>
  );
}

function Rule({ icon, children }: { icon: IconName; children: React.ReactNode }) {
  return (
    <li className="flex gap-2.5">
      <Icon name={icon} size={16} className="mt-px shrink-0 text-accent" />
      <span className="text-caption leading-relaxed text-ink-2">{children}</span>
    </li>
  );
}

function ToggleRow({
  icon,
  title,
  hint,
  on,
  onToggle,
  busy = false,
  disabled = false,
}: {
  icon: IconName;
  title: string;
  hint: string;
  on: boolean;
  onToggle: () => void;
  busy?: boolean;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center gap-3 rounded-control bg-surface-2 p-3.5">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-control bg-surface text-muted">
        <Icon name={icon} size={18} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-body font-semibold text-ink">{title}</p>
        <p className="mt-0.5 text-caption leading-snug text-muted">{hint}</p>
      </div>
      <Switch on={on} onToggle={onToggle} label={title} busy={busy} disabled={disabled} />
    </div>
  );
}

/** "Har 60 daq" yoki "60-120 daq". Ma'lumot bo'lmasa - em tire. */
function formatInterval(t: TaskSummary): string {
  const min = t.reminder_interval_min_minutes;
  const max = t.reminder_interval_max_minutes;
  if (min === undefined || max === undefined) return "—";
  return min === max ? `Har ${min} daq` : `${min}-${max} daq`;
}

/** "08:00 - 22:00" */
function formatWindow(t: TaskSummary): string {
  const from = t.reminder_start_hour;
  const to = t.reminder_end_hour;
  if (from === undefined || to === undefined) return "—";
  const pad = (h: number) => String(h).padStart(2, "0");
  return `${pad(from)}:00 - ${pad(to)}:00`;
}
