import type { ReactNode, SVGProps } from "react";

/*
 * Ikonka tizimi.
 *
 * NEGA kutubxona emas: loyihada ikonka kutubxonasi yo'q edi (butun
 * interfeys emoji ustiga qurilgan edi). Bizga 28 ta belgi kerak.
 * Qo'lda yozilgan inline SVG ~2kB gzip beradi, `lucide-react` esa shuncha
 * ikonka uchun ~8-10kB. Yangi bog'liqlik ham qo'shilmaydi.
 *
 * Barcha belgilar bitta tizimda:
 *   - 24x24 viewBox
 *   - chiziqli (stroke), to'ldirilmagan
 *   - stroke-width 1.75, yumaloq uchlar va burchaklar
 *   - `currentColor` - matn rangini meros qilib oladi, mavzuga moslashadi
 *
 * KIRISH IMKONIYATI:
 *   - Standart holatda ikonka BEZAK hisoblanadi -> aria-hidden.
 *   - Agar ikonka yagona ma'no tashuvchi bo'lsa (faqat-ikonkali tugma),
 *     `label` bering -> role="img" + aria-label qo'shiladi.
 *   Eslatma: faqat-ikonkali tugmada `label` ni ikonkaga emas, tugmaning
 *   o'ziga (aria-label) berish afzal - IconButton shuni qiladi.
 */

const P = (d: string, key?: string) => <path key={key} d={d} />;

/*
 * ATAYLAB `Record<string, ReactNode>` bilan izohlanmagan: shunday
 * qilinsa `keyof typeof GLYPHS` `string` ga aylanib, `IconName` hech
 * qanday himoya bermay qolardi - `<Icon name="yoq-ikonka" />` muammosiz
 * kompilyatsiya bo'lib, ekranda jimgina hech narsa chizmasdi.
 * Endi kalitlar literal sifatida chiqariladi va noto'g'ri nom
 * kompilyatsiya vaqtida xato beradi.
 */
const GLYPHS = {
  /* --- Harakatlar --- */
  check: P("M20 6 9 17l-5-5"),
  x: (
    <>
      {P("M18 6 6 18", "a")}
      {P("m6 6 12 12", "b")}
    </>
  ),
  plus: (
    <>
      {P("M12 5v14", "a")}
      {P("M5 12h14", "b")}
    </>
  ),
  minus: P("M5 12h14"),
  trash: (
    <>
      {P("M4 7h16", "a")}
      {P("M10 11v6M14 11v6", "b")}
      {P("m5 7 1 13a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-13", "c")}
      {P("M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2", "d")}
    </>
  ),
  skip: (
    <>
      {P("M5 4v16l11-8z", "a")}
      {P("M19 5v14", "b")}
    </>
  ),
  refresh: (
    <>
      {P("M21 4v6h-6", "a")}
      {P("M19.3 14.5A8 8 0 1 1 18 6.3L21 9", "b")}
    </>
  ),
  search: (
    <>
      <circle key="a" cx="11" cy="11" r="7" />
      {P("m20 20-3.6-3.6", "b")}
    </>
  ),

  /* --- Yo'nalish --- */
  "chevron-left": P("m15 18-6-6 6-6"),
  "chevron-right": P("m9 18 6-6-6-6"),
  "chevron-down": P("m6 9 6 6 6-6"),
  "arrow-left": (
    <>
      {P("M19 12H5", "a")}
      {P("m12 19-7-7 7-7", "b")}
    </>
  ),

  /* --- Mavzuviy --- */
  tasks: (
    <>
      <rect key="a" x="8" y="2" width="8" height="4" rx="1" />
      {P("M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2", "b")}
      {P("M9 12h6M9 16h6", "c")}
    </>
  ),
  users: (
    <>
      {P("M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2", "a")}
      <circle key="b" cx="9" cy="7" r="4" />
      {P("M22 21v-2a4 4 0 0 0-3-3.87", "c")}
      {P("M16 3.13a4 4 0 0 1 0 7.75", "d")}
    </>
  ),
  user: (
    <>
      {P("M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2", "a")}
      <circle key="b" cx="12" cy="7" r="4" />
    </>
  ),
  groups: (
    <>
      {P("M3 21h18", "a")}
      {P("M5 21V8l7-4 7 4v13", "b")}
      {P("M9.5 12h.01M14.5 12h.01M9.5 16h.01M14.5 16h.01", "c")}
    </>
  ),
  megaphone: (
    <>
      {P("M3 11v2a1 1 0 0 0 1 1h2l5 4V6L6 10H4a1 1 0 0 0-1 1z", "a")}
      {P("M15.5 8.5a5 5 0 0 1 0 7", "b")}
      {P("M18.5 5.5a9 9 0 0 1 0 13", "c")}
    </>
  ),
  chart: (
    <>
      {P("M3 21h18", "a")}
      {P("M6 21v-6M12 21V5M18 21v-10", "b")}
    </>
  ),
  calendar: (
    <>
      <rect key="a" x="3" y="5" width="18" height="16" rx="2" />
      {P("M16 3v4M8 3v4M3 11h18", "b")}
    </>
  ),
  clock: (
    <>
      <circle key="a" cx="12" cy="12" r="9" />
      {P("M12 7v5l3 2", "b")}
    </>
  ),
  bell: (
    <>
      {P("M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9", "a")}
      {P("M13.7 21a2 2 0 0 1-3.4 0", "b")}
    </>
  ),
  camera: (
    <>
      {P("M21 19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h3l1.5-3h5L16 7h3a2 2 0 0 1 2 2z", "a")}
      <circle key="b" cx="12" cy="13" r="3.5" />
    </>
  ),
  image: (
    <>
      <rect key="a" x="3" y="3" width="18" height="18" rx="2" />
      <circle key="b" cx="8.5" cy="8.5" r="1.5" />
      {P("m21 15-5-5L5 21", "c")}
    </>
  ),
  lock: (
    <>
      <rect key="a" x="4" y="11" width="16" height="10" rx="2" />
      {P("M8 11V7a4 4 0 0 1 8 0v4", "b")}
    </>
  ),
  crown: (
    <>
      {P("M5 18h14", "a")}
      {P("M4 7l4.5 4L12 4l3.5 7L20 7l-1.6 8H5.6z", "b")}
    </>
  ),
  umbrella: (
    <>
      {P("M12 13v6a2 2 0 0 1-4 0", "a")}
      {P("M2 13a10 10 0 0 1 20 0z", "b")}
    </>
  ),
  sparkle: P("m12 3 1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"),
  inbox: (
    <>
      {P("M21 12h-5l-2 3h-4l-2-3H3", "a")}
      {P("M5.5 5.6 3 12v6a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-6l-2.5-6.4A2 2 0 0 0 16.6 4H7.4a2 2 0 0 0-1.9 1.6z", "b")}
    </>
  ),
  compass: (
    <>
      <circle key="a" cx="12" cy="12" r="9" />
      {P("m16 8-2.2 5.8L8 16l2.2-5.8z", "b")}
    </>
  ),
  bug: (
    <>
      {P("M9 8h6a4 4 0 0 1 4 4v2a7 7 0 0 1-14 0v-2a4 4 0 0 1 4-4z", "a")}
      {P("M9 8V6.5a3 3 0 0 1 6 0V8", "b")}
      {P("M3 13h2M19 13h2M4.5 18 7 16.5M19.5 18 17 16.5M4.5 8.5 7 10M19.5 8.5 17 10", "c")}
    </>
  ),
  wrench: P(
    "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.3-3.3a6 6 0 0 1-7.9 7.9l-6.3 6.3a2.1 2.1 0 0 1-3-3l6.3-6.3a6 6 0 0 1 7.9-7.9z"
  ),
  alert: (
    <>
      {P("M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z", "a")}
      {P("M12 9v4M12 17h.01", "b")}
    </>
  ),
  info: (
    <>
      <circle key="a" cx="12" cy="12" r="9" />
      {P("M12 16v-4M12 8h.01", "b")}
    </>
  ),
  settings: (
    <>
      {P("M5 21v-6M5 11V3M12 21v-9M12 8V3M19 21v-4M19 13V3", "a")}
      {P("M2 15h6M9 8h6M16 17h6", "b")}
    </>
  ),
  /*
   * Profil reytingi uchun (5 yulduzli daraja). To'la yulduz ko'rsatish
   * uchun `<Icon name="star" fill="currentColor" />` chaqiring - `Icon`
   * `rest` proplarini standart `fill="none"` dan KEYIN yozadi, shuning
   * uchun bitta glif ikkala holatni (bo'sh/to'la) ham beradi.
   */
  star: P(
    "M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.77 5.82 21 7 14.14 2 9.27l6.91-1.01L12 2z"
  ),
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof GLYPHS;

export interface IconProps extends Omit<SVGProps<SVGSVGElement>, "name"> {
  name: IconName;
  /** Piksel o'lchami. Standart 20 - matn yonida optik jihatdan mos keladi. */
  size?: number;
  /** Berilsa, ikonka ma'noli deb hisoblanadi va ekran o'quvchiga o'qiladi. */
  label?: string;
  strokeWidth?: number;
}

export function Icon({
  name,
  size = 20,
  label,
  strokeWidth = 1.75,
  ...rest
}: IconProps) {
  const glyph = GLYPHS[name];
  if (!glyph) return null;

  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
      shapeRendering="geometricPrecision"
      {...(label ? { role: "img", "aria-label": label } : { "aria-hidden": true })}
      {...rest}
    >
      {glyph}
    </svg>
  );
}

/*
 * `Avatar size="sm"` bilan bir xil o'lchamdagi doira - a'zo biriktirilmagan
 * holatlarni ko'rsatish uchun (Avatar o'rnini bosadi). Ilgari
 * AdminDashboard va MemberDashboard'da bir xil sinf satri bilan mustaqil
 * ikki marta yozilgan edi.
 */
export function IconTile({ name }: { name: IconName }) {
  return (
    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-pill bg-surface-2 text-muted">
      <Icon name={name} size={16} />
    </span>
  );
}

/*
 * 5 yulduzli profil darajasini ko'rsatadi (RatingService'ning
 * `rating_stars` qiymati). Yaqin butun songa yaxlitlanadi - yarim
 * yulduz aniqligi so'ralmagan va aniq son (`value.toFixed(2)`)
 * baribir yonida ko'rsatiladi, shuning uchun aniqlik yo'qolmaydi.
 */
export function StarRating({ value, size = 18 }: { value: number; size?: number }) {
  const filled = Math.round(Math.max(0, Math.min(5, value)));
  return (
    <div
      className="flex items-center gap-0.5"
      role="img"
      aria-label={`Reyting: 5 dan ${value.toFixed(2)}`}
    >
      {Array.from({ length: 5 }).map((_, i) =>
        i < filled ? (
          <Icon key={i} name="star" size={size} fill="currentColor" className="text-warning" />
        ) : (
          <Icon key={i} name="star" size={size} className="text-muted" />
        )
      )}
    </div>
  );
}
