import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Btn, Field, Input, Sheet, Stepper, Switch, TextArea, toast } from "../components/ui";
import { todayInZone } from "../lib/format";
import type { AuthUser, GroupSummary, TaskSummary } from "../types";

/*
 * Mavjud vazifani tahrirlash formasi - `CreateTaskSheet` bilan bir xil
 * maydonlar, lekin POST o'rniga PATCH yuboradi va faqat FAKTIK
 * o'zgargan qiymatlarni jo'natadi (backend `UpdateTaskRequest`da har bir
 * maydon ixtiyoriy - `None` bo'lsa tegilmaydi).
 *
 * "Boshlanish sanasi" o'rniga bu yerda "Keyingi tsikl sanasi" (xom
 * `next_execution_date`) tahrirlanadi - vazifa allaqachon yaratilgan,
 * `start_date` endi tarixiy nuqta. DIQQAT: bu `TaskSummary.current_turn_date`
 * BILAN BIR XIL EMAS - o'sha maydon interval bo'yicha hisoblab chiqarilgan
 * (bir interval orqaga surilgan), uni to'g'ridan-to'g'ri qaytarib yozish
 * jadvalni har saqlashda bitta intervalga siljitib qo'yardi.
 */

interface Props {
  open: boolean;
  onClose: () => void;
  user: AuthUser;
  group: GroupSummary;
  task: TaskSummary | null;
  onUpdated: () => void;
}

export function EditTaskSheet({ open, onClose, user, group, task, onUpdated }: Props) {
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [everyDays, setEveryDays] = useState(1);
  const [nextDate, setNextDate] = useState(() => todayInZone(group.timezone));
  const [requirePhoto, setRequirePhoto] = useState(true);
  const [isActive, setIsActive] = useState(true);

  // Sheet har safar YANGI vazifa uchun ochilganda maydonlarni o'sha
  // vazifaning joriy qiymatlari bilan to'ldiramiz - forma har doim
  // ochilgan paytdagi haqiqiy holatni aks ettirishi kerak.
  useEffect(() => {
    if (!open || !task) return;
    setName(task.name);
    setDescription(task.description ?? "");
    setEveryDays(task.schedule_interval_days || 1);
    setNextDate(task.next_cycle_date || todayInZone(group.timezone));
    setRequirePhoto(task.require_photo ?? true);
    setIsActive(task.is_active);
  }, [open, task, group.timezone]);

  async function save() {
    if (!task) return;
    if (!name.trim()) return;
    setSaving(true);
    const res = await api.updateTask(task.id, {
      telegram_id: user.telegram_id,
      name: name.trim(),
      description: description.trim() || null,
      schedule_interval_days: everyDays || 1,
      next_execution_date: nextDate,
      require_photo: requirePhoto,
      is_active: isActive,
    });
    setSaving(false);
    if (!res.success) return toast.err(res.message || "Vazifa yangilanmadi");
    toast.ok("Vazifa yangilandi");
    onClose();
    onUpdated();
  }

  return (
    <Sheet open={open} onClose={onClose} title="Vazifani tahrirlash">
      <div className="space-y-4">
        <Field label="Vazifa nomi">
          <Input
            placeholder="Masalan: Oshxonani tozalash"
            value={name}
            maxLength={80}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>

        <Field label="Tavsif" hint="Ixtiyoriy">
          <TextArea
            placeholder="Qo'shimcha izoh..."
            value={description}
            maxLength={500}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Takrorlanish" hint="1 = har kuni">
            <Stepper
              value={everyDays}
              onChange={setEveryDays}
              min={1}
              max={365}
              suffix="kun"
              label="Takrorlanish"
            />
          </Field>
          <Field
            label="Keyingi tsikl sanasi"
            hint="Joriy navbat allaqachon tayinlangan - bu sana KEYINGI davra qachon boshlanishini belgilaydi"
          >
            <Input type="date" value={nextDate} onChange={(e) => setNextDate(e.target.value)} />
          </Field>
        </div>

        <div className="flex items-center justify-between gap-3 rounded-control bg-surface-2 px-3.5 py-3">
          <div className="min-w-0">
            <p className="text-body font-semibold text-ink">Rasm talab qilinsin</p>
            <p className="mt-0.5 text-caption text-muted">
              A'zo bajarganini rasm bilan tasdiqlaydi
            </p>
          </div>
          <Switch
            on={requirePhoto}
            onToggle={() => setRequirePhoto((v) => !v)}
            label="Rasm talab qilinsin"
          />
        </div>

        <p className="text-caption text-muted">
          🔔 Eslatmalar har kuni qat'iy 08:00, 13:00 va 19:00 da yuboriladi.
        </p>

        <div className="flex items-center justify-between gap-3 rounded-control bg-surface-2 px-3.5 py-3">
          <div className="min-w-0">
            <p className="text-body font-semibold text-ink">Vazifa faol</p>
            <p className="mt-0.5 text-caption text-muted">
              O'chirilsa - eslatma va navbat yangilanishi to'xtaydi (o'chirilmaydi)
            </p>
          </div>
          <Switch on={isActive} onToggle={() => setIsActive((v) => !v)} label="Vazifa faol" />
        </div>

        <Btn full size="lg" onClick={save} loading={saving} disabled={!name.trim()}>
          {saving ? "Saqlanmoqda…" : "Saqlash"}
        </Btn>
      </div>
    </Sheet>
  );
}
