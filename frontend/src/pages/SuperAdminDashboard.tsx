import { useEffect, useState } from "react";
import { api } from "../api/client";
import { AppHeader, AppMain } from "../components/AppScreen";
import { DataList, ListRow } from "../components/DataList";
import { Icon } from "../components/Icon";
import { StatRail } from "../components/StatRail";
import { BottomTabs } from "../components/Tabs";
import {
  Avatar,
  Badge,
  Btn,
  ConfirmDialog,
  Empty,
  ErrorState,
  Field,
  IconButton,
  SectionHead,
  Surface,
  Switch,
  TextArea,
  toast,
} from "../components/ui";
import { ListSkeleton, StatRailSkeleton } from "../components/Skeletons";
import { SuperAdminUserProfileSheet } from "../components/SuperAdminUserProfileSheet";
import { useAsyncData } from "../hooks/useAsyncData";
import { formatStamp } from "../lib/format";
import type {
  ErrorLog,
  GroupSummary,
  SuperAdminGroupSummary,
  SuperAdminUserSummary,
  SystemStats,
} from "../types";

type Tab = "overview" | "groups" | "users" | "logs" | "broadcast";

interface Props {
  onBack: () => void;
  /**
   * Guruh qatoriga bosilganda chaqiriladi - App.tsx shu guruhni "faol
   * guruh" qilib, Super Admin panelidan chiqib, o'sha guruhning admin
   * ko'rinishini ochadi. Backend guruhga oid endpointlarda Super
   * Admin'ni har doim admin sifatida qabul qiladi (`ensure_admin_for_group`
   * uni chetlab o'tadi), shuning uchun bu yerda haqiqiy a'zolik shart
   * emas - shunchaki "admin" rolini qo'lda belgilaymiz.
   */
  onOpenGroup: (group: GroupSummary) => void;
}

export function SuperAdminDashboard({ onBack, onOpenGroup }: Props) {
  const [tab, setTab] = useState<Tab>("overview");
  const [profileUserId, setProfileUserId] = useState<number | null>(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  /* Ikkala amal ham oqibatli: biri butun tizimni yopadi, ikkinchisi
     qaytarib bo'lmaydigan ommaviy xabar yuboradi. */
  const [confirmMaintenance, setConfirmMaintenance] = useState(false);
  const [confirmSend, setConfirmSend] = useState(false);
  /* Texnik rejim kaliti ham server javobini kutadi - spam bosishni bloklaydi. */
  const [maintenanceBusy, setMaintenanceBusy] = useState(false);
  /* Jurnalni tozalash - qaytarib bo'lmaydigan amal, shuning uchun tasdiqlanadi. */
  const [confirmClearLogs, setConfirmClearLogs] = useState(false);
  const [clearingLogs, setClearingLogs] = useState(false);

  const stats = useAsyncData<SystemStats>("system-stats", () => api.getSystemStats(), []);

  /*
   * Bo'lim faqat BIRINCHI MARTA ochilganda yuklanadi va keyin keshda qoladi.
   *
   * REGRESSIYA TUZATILDI: ilgari bu yerda deps sifatida `[tab === "groups"]`
   * turardi. Bo'limdan chiqilganda bu qiymat true->false ga o'zgarardi,
   * ya'ni effekt QAYTA ishga tushib, keshdagi ma'lumotni `null` qilib
   * tozalardi; qaytib kirilganda esa hammasi qaytadan so'ralardi.
   * 212 foydalanuvchi ro'yxatini har safar qayta yuklash keraksiz.
   *
   * `visited` bir tomonlama qulf: bo'lim bir marta ochilgach true bo'lib
   * qoladi, shuning uchun effekt aynan bir marta ishlaydi (STEP 1
   * shartnomasidagi "lazy-fetch once then cached" xatti-harakati).
   */
  const [visited, setVisited] = useState<Partial<Record<Tab, boolean>>>({ overview: true });
  useEffect(() => {
    setVisited((v) => (v[tab] ? v : { ...v, [tab]: true }));
  }, [tab]);
  const groups = useAsyncData<SuperAdminGroupSummary[]>(
    "all-groups",
    visited.groups ? () => api.listAllGroups() : null,
    [!!visited.groups]
  );
  const users = useAsyncData<SuperAdminUserSummary[]>(
    "all-users",
    visited.users ? () => api.listAllUsers() : null,
    [!!visited.users]
  );
  const logs = useAsyncData<ErrorLog[]>(
    "error-logs",
    visited.logs ? () => api.listErrorLogs() : null,
    [!!visited.logs]
  );

  function requestMaintenanceToggle() {
    if (!stats.data || maintenanceBusy) return;
    // Yoqish - butun tizimni yopadi, shuning uchun tasdiqlanadi.
    // O'chirish - xizmatni tiklaydi, darhol bajariladi.
    if (!stats.data.maintenance_mode) setConfirmMaintenance(true);
    else void applyMaintenance(false);
  }

  async function applyMaintenance(next: boolean) {
    setMaintenanceBusy(true);
    const res = await api.setMaintenanceMode(next);
    setMaintenanceBusy(false);
    if (!res.success) return toast.err(res.message || "O'zgartirib bo'lmadi");
    toast.ok(next ? "Texnik rejim yoqildi" : "Texnik rejim o'chirildi");
    stats.reload();
  }

  async function send() {
    if (!text.trim() || sending) return;
    setSending(true);
    const res = await api.broadcastMessage(text.trim());
    setSending(false);
    if (!res.success || !res.data) return toast.err(res.message || "Yuborilmadi");
    toast.ok(`${res.data.sent}/${res.data.total} foydalanuvchiga yetkazildi`);
    setText("");
  }

  async function clearLogs() {
    setClearingLogs(true);
    const res = await api.clearErrorLogs();
    setClearingLogs(false);
    setConfirmClearLogs(false);
    if (!res.success) return toast.err(res.message || "Tozalab bo'lmadi");
    toast.ok(res.message || "Jurnal tozalandi");
    logs.reload();
  }

  return (
    <>
      <AppHeader>
        <div className="flex items-center gap-2.5 pt-1">
          <IconButton name="chevron-left" label="Orqaga" onClick={onBack} />
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-control bg-warning/18 text-warning">
            <Icon name="crown" size={18} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-headline leading-tight text-ink">Super Admin</p>
            <p className="truncate text-caption leading-tight text-muted">Tizim boshqaruvi</p>
          </div>
          {stats.data?.maintenance_mode && (
            <Badge tone="danger" dot>
              Texnik rejim
            </Badge>
          )}
        </div>
      </AppHeader>

      <AppMain>
        <div className="space-y-4">
          {/* ------------------------- UMUMIY ------------------------- */}
          {tab === "overview" &&
            (stats.loading ? (
              <StatRailSkeleton columns={4} />
            ) : stats.error ? (
              <ErrorState message={stats.error} onRetry={stats.reload} />
            ) : (
              stats.data && (
                <div className="animate-fadeIn space-y-4">
                  <StatRail
                    items={[
                      {
                        label: "Guruhlar",
                        value: stats.data.total_groups,
                        icon: "groups",
                        tone: "accent",
                      },
                      { label: "Userlar", value: stats.data.total_users, icon: "users" },
                      {
                        label: "Faol vazifa",
                        value: stats.data.total_active_tasks,
                        icon: "tasks",
                        tone: "success",
                      },
                      {
                        label: "Bajarishlar",
                        value: stats.data.total_completions,
                        icon: "check",
                        tone: "warning",
                      },
                    ]}
                  />

                  <section>
                    <SectionHead
                      title="Texnik rejim"
                      sub="Yoqilsa oddiy foydalanuvchilar uchun tizim yopiladi"
                    />
                    <Surface
                      className={stats.data.maintenance_mode ? "bg-danger/8" : undefined}
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex min-w-0 items-center gap-3">
                          <span
                            className={`grid h-11 w-11 shrink-0 place-items-center rounded-control ${
                              stats.data.maintenance_mode
                                ? "bg-danger/16 text-danger"
                                : "bg-success/16 text-success"
                            }`}
                          >
                            <Icon
                              name={stats.data.maintenance_mode ? "wrench" : "check"}
                              size={20}
                            />
                          </span>
                          <div className="min-w-0">
                            <p className="text-headline text-ink">
                              {stats.data.maintenance_mode ? "Yoqilgan" : "O'chirilgan"}
                            </p>
                            <p className="mt-0.5 text-caption leading-snug text-muted">
                              {stats.data.maintenance_mode
                                ? "Bot va Mini App 503 qaytarmoqda"
                                : "Hamma narsa odatdagidek ishlayapti"}
                            </p>
                          </div>
                        </div>
                        <Switch
                          on={stats.data.maintenance_mode}
                          onToggle={requestMaintenanceToggle}
                          label="Texnik rejim"
                          busy={maintenanceBusy}
                        />
                      </div>
                    </Surface>
                  </section>
                </div>
              )
            ))}

          {/* ------------------------- GURUHLAR ------------------------- */}
          {tab === "groups" && (
            <div className="animate-fadeIn">
              <SectionHead
                title="Barcha guruhlar"
                sub={groups.data ? `${groups.data.length} ta` : undefined}
              />
              {groups.loading ? (
                <ListSkeleton rows={3} />
              ) : groups.error ? (
                <ErrorState message={groups.error} onRetry={groups.reload} />
              ) : !groups.data || groups.data.length === 0 ? (
                <Empty
                  iconName="groups"
                  title="Guruhlar yo'q"
                  hint="Hali hech kim bot orqali guruh yaratmagan."
                />
              ) : (
                <DataList>
                  {groups.data.map((g, i) => (
                    <ListRow
                      key={g.id}
                      index={i}
                      leading={<Avatar name={g.name} size="sm" />}
                      title={g.name}
                      subtitle={`${g.member_count} a'zo · ${g.timezone}`}
                      trailing={
                        g.is_active ? (
                          <Badge tone="success">Faol</Badge>
                        ) : (
                          <Badge tone="danger">Yopiq</Badge>
                        )
                      }
                      onClick={() =>
                        onOpenGroup({
                          id: g.id,
                          name: g.name,
                          role: "admin",
                          member_id: -1,
                          timezone: g.timezone,
                        })
                      }
                      ariaLabel={`${g.name} guruhini ochish`}
                    />
                  ))}
                </DataList>
              )}
            </div>
          )}

          {/* ------------------------- USERLAR -------------------------
              Ilgari bu uch ustunli, yon tomonga skroll qiladigan jadval
              edi (FOYDALANUVCHI / TELEGRAM ID / HOLAT) va ismlar
              `max-w-[8rem]` bilan kesilardi. Endi ustuvorlikka qarab
              ikki qatorli qator: ism (birlamchi), @username va Telegram ID
              (ikkilamchi), holat belgisi (o'ngda). Uzun ism ham, uzun
              username ham layoutni buzmaydi.
             ----------------------------------------------------------- */}
          {tab === "users" && (
            <div className="animate-fadeIn">
              <SectionHead
                title="Foydalanuvchilar"
                sub={users.data ? `${users.data.length} ta` : undefined}
              />
              {users.loading ? (
                <ListSkeleton rows={4} />
              ) : users.error ? (
                <ErrorState message={users.error} onRetry={users.reload} />
              ) : !users.data || users.data.length === 0 ? (
                <Empty
                  iconName="users"
                  title="Foydalanuvchilar yo'q"
                  hint="Hali hech kim botda /start bosmagan."
                />
              ) : (
                <DataList>
                  {users.data.map((u, i) => (
                    <ListRow
                      key={u.id}
                      index={i}
                      leading={<Avatar name={u.full_name} size="sm" crown={u.is_super_admin} />}
                      title={u.full_name}
                      subtitle={
                        <>
                          {u.username ? `@${u.username}` : "username yo'q"}
                          <span className="text-muted/70"> · </span>
                          <span className="tnum">{u.telegram_id}</span>
                        </>
                      }
                      trailing={
                        u.is_active ? (
                          <Badge tone="success">Faol</Badge>
                        ) : (
                          <Badge tone="danger">Blok</Badge>
                        )
                      }
                      onClick={() => setProfileUserId(u.id)}
                      ariaLabel={`${u.full_name} profilini ochish`}
                    />
                  ))}
                </DataList>
              )}
            </div>
          )}

          {/* ------------------------- XATOLAR ------------------------- */}
          {tab === "logs" && (
            <div className="animate-fadeIn">
              <SectionHead
                title="Xatoliklar jurnali"
                sub={logs.data ? `oxirgi ${logs.data.length} ta yozuv` : undefined}
                action={
                  logs.data && logs.data.length > 0 ? (
                    <Btn
                      variant="destructive"
                      size="sm"
                      icon="trash"
                      onClick={() => setConfirmClearLogs(true)}
                    >
                      Tozalash
                    </Btn>
                  ) : undefined
                }
              />
              {logs.loading ? (
                <ListSkeleton rows={2} />
              ) : logs.error ? (
                <ErrorState message={logs.error} onRetry={logs.reload} />
              ) : !logs.data || logs.data.length === 0 ? (
                <Empty
                  iconName="sparkle"
                  title="Xatolar yo'q"
                  hint="Tizim jurnalida hech qanday xatolik qayd etilmagan."
                />
              ) : (
                <div className="space-y-2.5">
                  {logs.data.map((log) => (
                    <Surface key={log.id} padded={false} className="overflow-hidden">
                      <div className="flex items-center justify-between gap-2 border-b border-line px-3.5 py-2">
                        <Badge tone="danger" dot>
                          {log.level}
                        </Badge>
                        <span className="tnum text-caption text-muted">
                          {formatStamp(log.created_at)}
                        </span>
                      </div>
                      <div className="px-3.5 py-3">
                        <p className="whitespace-pre-wrap break-words font-mono text-caption leading-relaxed text-ink">
                          {log.message}
                        </p>
                        {log.context && (
                          <p className="mt-2 break-words rounded-control bg-surface-2 px-2.5 py-2 font-mono text-micro normal-case tracking-normal leading-relaxed text-muted">
                            {log.context}
                          </p>
                        )}
                      </div>
                    </Surface>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ------------------------- BROADCAST ------------------------- */}
          {tab === "broadcast" && (
            <div className="animate-fadeIn space-y-3">
              <SectionHead title="Ommaviy xabar" sub="Botdagi barcha foydalanuvchilarga" />

              <div className="flex items-start gap-2.5 rounded-control bg-warning/12 px-3 py-2.5">
                <Icon name="alert" size={16} className="mt-px shrink-0 text-warning" />
                <p className="text-caption leading-relaxed text-ink-2">
                  Bu xabar {stats.data?.total_users ?? "barcha"} foydalanuvchiga yetib boradi.
                  Yuborilgandan keyin bekor qilib bo'lmaydi.
                </p>
              </div>

              <Field label="Xabar matni" hint={`${text.length} / 2000 belgi`}>
                <TextArea
                  rows={7}
                  maxLength={2000}
                  placeholder="Xabar matnini kiriting…"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
              </Field>

              <Btn
                full
                size="lg"
                icon="megaphone"
                onClick={() => setConfirmSend(true)}
                loading={sending}
                disabled={!text.trim()}
              >
                {sending ? "Yuborilmoqda…" : "Hammaga yuborish"}
              </Btn>
            </div>
          )}
        </div>

        <SuperAdminUserProfileSheet
          open={profileUserId !== null}
          onClose={() => setProfileUserId(null)}
          userId={profileUserId}
        />

        <ConfirmDialog
          open={confirmMaintenance}
          onCancel={() => setConfirmMaintenance(false)}
          onConfirm={() => {
            setConfirmMaintenance(false);
            void applyMaintenance(true);
          }}
          destructive
          title="Texnik rejim yoqilsinmi?"
          message="Yoqilgach bot va Mini App barcha oddiy foydalanuvchilar uchun 503 qaytaradi. Faqat Super Admin bo'limlari ochiq qoladi."
          confirmLabel="Yoqish"
        />

        <ConfirmDialog
          open={confirmSend}
          onCancel={() => setConfirmSend(false)}
          onConfirm={async () => {
            await send();
            setConfirmSend(false);
          }}
          destructive
          busy={sending}
          title="Hammaga yuborilsinmi?"
          message={`Xabar botdagi ${stats.data?.total_users ?? "barcha"} foydalanuvchiga boradi. Yuborilgandan keyin bekor qilib bo'lmaydi.`}
          confirmLabel="Yuborish"
        />

        <ConfirmDialog
          open={confirmClearLogs}
          onCancel={() => setConfirmClearLogs(false)}
          onConfirm={clearLogs}
          destructive
          busy={clearingLogs}
          title="Jurnal tozalansinmi?"
          message={`${logs.data?.length ?? 0} ta xato yozuvi butunlay o'chiriladi. Buni qaytarib bo'lmaydi.`}
          confirmLabel="Tozalash"
        />

        {/*
          5 ta bo'lim uchun pastki panel: hammasi bir vaqtda ko'rinadi,
          gorizontal skrollsiz (u Telegram'ning yon-surish imo-ishorasi
          bilan to'qnashardi) va barmoq yetadigan joyda.
        */}
        <BottomTabs
          value={tab}
          onChange={setTab}
          label="Super Admin bo'limlari"
          items={[
            { value: "overview", label: "Umumiy", icon: "chart" },
            { value: "groups", label: "Guruhlar", icon: "groups" },
            { value: "users", label: "Userlar", icon: "users" },
            { value: "logs", label: "Xatolar", icon: "bug" },
            { value: "broadcast", label: "Xabar", icon: "megaphone" },
          ]}
        />
      </AppMain>
    </>
  );
}
