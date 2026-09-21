import { useState } from "react";
import { api } from "../api/client";
import { Btn, Field, Input, Sheet, Stepper, Switch, toast } from "../components/ui";
import { todayInZone } from "../lib/format";
import type { AuthUser, GroupSummary } from "../types";

/*
 * Vazifa yaratish formasi.
 *
 * Ilgari bu AdminDashboard.tsx ichida edi va o'sha faylni 369 qatorga
 * cho'zib yuborgan edi (uchta panel + ikkita sheet + 8 maydonli forma +
 * oltita async ishlov beruvchi bitta komponentda). Endi alohida fayl -
 * mantiq o'zgarmagan, faqat ko'chirildi.
 *
 * MUHIM: ikkala mijoz tomonidagi tekshiruv ham (backend'dagi
 * `model_validator` ning aksi) va toast matnlari AYNAN saqlangan.
 */

interface Props {
  open: boolean;
  onClose: () => void;
  user: AuthUser;
  group: GroupSummary;
  onCreated: () => void;
}

export function CreateTaskSheet({ open, onClose, user, group, onCreated }: Props) {
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [everyDays, setEveryDays] = useState(1);
  const [startDate, setStartDate] = useState(() => todayInZone(group.timezone));
  const [requirePhoto, setRequirePhoto] = useState(true);

  function resetForm() {
    setName("");
    setEveryDays(1);
    setRequirePhoto(true);
    setStartDate(todayInZone(group.timezone));
  }

  async function createTask() {
    if (!name.trim()) return;
    setCreating(true);
    const res = await api.createTask({
      telegram_id: user.telegram_id,
      group_id: group.id,
      name: name.trim(),
      require_photo: requirePhoto,
      schedule_interval_days: everyDays || 1,
      start_date: startDate,
    });
    setCreating(false);
    if (!res.success) return toast.err(res.message || "Vazifa yaratilmadi");
    toast.ok("Vazifa yaratildi");
    onClose();
    resetForm();
    onCreated();
  }

  return (
    <Sheet open={open} onClose={onClose} title="Yangi vazifa">
      <div className="space-y-4">
        <Field label="Vazifa nomi">
          <Input
            placeholder="Masalan: Oshxonani tozalash"
            value={name}
            maxLength={80}
            onChange={(e) => setName(e.target.value)}
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
          <Field label="Boshlanish sanasi">
            <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
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

        <Btn full size="lg" onClick={createTask} loading={creating} disabled={!name.trim()}>
          {creating ? "Yaratilmoqda…" : "Vazifani yaratish"}
        </Btn>
      </div>
    </Sheet>
  );
}
