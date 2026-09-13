/** @type {import('tailwindcss').Config} */

/*
 * Dizayn tizimi ko'prigi.
 *
 * Barcha ranglar src/index.css dagi CSS o'zgaruvchilaridan olinadi -
 * shunda light/dark rejim bitta joyda boshqariladi va `bg-surface/60`
 * kabi alfa variantlari ishlashda davom etadi.
 *
 * STEP 2/3 davrida eski nomlar (canvas, sunken, brand, jade, amber,
 * rose, midnight, shadow-lift/pop, rounded-xl2/xl3, text-2xs) vaqtincha
 * alias sifatida saqlangan edi. STEP 4 da barcha sahifalar yangi
 * semantik nomlarga ko'chib bo'lgani tekshirildi (0 ta qoldiq), shuning
 * uchun aliaslar olib tashlandi - endi bitta nom, bitta ma'no.
 */

const surface = {
  ground: "rgb(var(--c-ground) / <alpha-value>)",
  elevated: "rgb(var(--c-elevated) / <alpha-value>)",
  surface: "rgb(var(--c-surface) / <alpha-value>)",
  "surface-2": "rgb(var(--c-surface-2) / <alpha-value>)",
  interactive: "rgb(var(--c-interactive) / <alpha-value>)",
  active: "rgb(var(--c-active) / <alpha-value>)",
  raised: "rgb(var(--c-raised) / <alpha-value>)",
};

const content = {
  ink: "rgb(var(--c-ink) / <alpha-value>)",
  "ink-2": "rgb(var(--c-ink-2) / <alpha-value>)",
  muted: "rgb(var(--c-muted) / <alpha-value>)",
  disabled: "rgb(var(--c-disabled) / <alpha-value>)",
};

const lines = {
  line: "rgb(var(--c-line) / <alpha-value>)",
  "control-edge": "rgb(var(--c-control-edge) / <alpha-value>)",
};

const accents = {
  accent: "rgb(var(--c-accent) / <alpha-value>)",
  "accent-solid": "rgb(var(--c-accent-solid) / <alpha-value>)",
  "accent-ink": "rgb(var(--c-accent-ink) / <alpha-value>)",
  "accent-2": "rgb(var(--c-accent-2) / <alpha-value>)",
};

const semantic = {
  success: "rgb(var(--c-success) / <alpha-value>)",
  warning: "rgb(var(--c-warning) / <alpha-value>)",
  danger: "rgb(var(--c-danger) / <alpha-value>)",
  info: "rgb(var(--c-info) / <alpha-value>)",
  "semantic-ink": "rgb(var(--c-semantic-ink) / <alpha-value>)",
};

module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ...surface,
        ...content,
        ...lines,
        ...accents,
        ...semantic,
      },

      /*
       * Tipografika: semantik nomlar, Tailwind'ning standart
       * text-xs/sm/base shkalasi bilan to'qnashmaydi.
       * Kontent uchun eng kichik o'lcham - caption (13px).
       * micro (11px) faqat KATTA HARFLI yorliqlar uchun.
       */
      fontSize: {
        display: ["1.75rem", { lineHeight: "2rem", letterSpacing: "-0.02em", fontWeight: "800" }],
        "title-1": ["1.375rem", { lineHeight: "1.75rem", letterSpacing: "-0.01em", fontWeight: "700" }],
        "title-2": ["1.125rem", { lineHeight: "1.5rem", letterSpacing: "-0.01em", fontWeight: "700" }],
        headline: ["1rem", { lineHeight: "1.375rem", fontWeight: "600" }],
        body: ["0.9375rem", { lineHeight: "1.375rem" }],
        callout: ["0.875rem", { lineHeight: "1.25rem" }],
        caption: ["0.8125rem", { lineHeight: "1.125rem" }],
        micro: ["0.6875rem", { lineHeight: "0.875rem", letterSpacing: "0.08em", fontWeight: "600" }],
      },

      /*
       * Radius: semantik nomlar. Tailwind'ning rounded-lg/xl standart
       * qiymatlarini ATAYLAB o'zgartirmaymiz - aks holda mavjud
       * sahifalardagi kichik elementlar to'satdan juda dumaloq bo'lib qolardi.
       */
      borderRadius: {
        control: "0.75rem", // tugma, input, stepper
        card: "1rem", // karta, ro'yxat qatori
        hero: "1.25rem", // hero blok
        sheet: "1.75rem", // bottom sheet, modal
        pill: "9999px",
      },

      /*
       * Ko'tarilish: uchta daraja. Har bir yuza yo CHEGARA, yo SOYA
       * oladi - ikkalasi birga emas.
       */
      boxShadow: {
        e1: "0 1px 2px rgb(var(--c-shadow) / 0.16), 0 2px 8px -2px rgb(var(--c-shadow) / 0.20)",
        e2: "0 8px 24px -8px rgb(var(--c-shadow) / 0.34)",
        e3: "0 -8px 40px -12px rgb(var(--c-shadow) / 0.50)",
        "glass-edge": "inset 0 1px 0 rgb(var(--glass-edge) / var(--glass-edge-alpha))",
        focus: "0 0 0 3px rgb(var(--c-accent) / 0.34)",
      },

      /*
       * Alfa (shaffoflik) shkalasi.
       *
       * MAVJUD XATOLIK TUZATILDI: Tailwind'ning standart opacity shkalasi
       * faqat 0/5/10/20/25/... qadamlarni biladi. Loyihada esa `bg-brand/12`,
       * `bg-jade/14`, `bg-amber/16`, `bg-rose/14`, `bg-white/15`,
       * `border-amber/35` kabi qiymatlar ishlatilgan - ular Tailwind
       * tomonidan JIM-JITLIK bilan e'tiborsiz qoldirilgan, ya'ni hech qanday
       * CSS chiqarilmagan. Natijada barcha rangli Pill/Badge fonlari,
       * hero bloklaridagi yarim shaffof qatlamlar va chegaralar umuman
       * ko'rinmay kelgan (headless Chrome skrinshoti bilan tasdiqlangan).
       *
       * Kerakli qadamlarni qo'shamiz - bu ham yangi komponentlarni, ham
       * mavjud sahifalardagi eskidan buzuq bo'lib kelgan tonlarni tiklaydi.
       */
      opacity: {
        2: "0.02",
        4: "0.04",
        6: "0.06",
        8: "0.08",
        12: "0.12",
        14: "0.14",
        15: "0.15",
        16: "0.16",
        18: "0.18",
        22: "0.22",
        24: "0.24",
        34: "0.34",
        35: "0.35",
        45: "0.45",
        55: "0.55",
        65: "0.65",
        85: "0.85",
        88: "0.88",
      },

      spacing: {
        gutter: "1rem",
        section: "1.5rem",
        tap: "2.75rem", // 44px - minimal tegish maydoni
        /* 13 Tailwind standart shkalasida YO'Q edi, shuning uchun
           Btn size="lg" dagi `h-13` hech qanday CSS bermay kelgan. */
        13: "3.25rem",
      },

      // `minWidth.tap` yo'q: hech qanday joyda `min-w-tap` ishlatilmagan -
      // faqat balandlik (min-h-tap) kerak bo'lgan, chunki kenglik odatda
      // `flex-1` yoki `w-full` bilan allaqachon ta'minlanadi.
      minHeight: {
        tap: "2.75rem",
      },

      transitionDuration: {
        fast: "140ms",
        base: "200ms",
        slow: "280ms",
        sheet: "320ms",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(.22,1,.36,1)",
        standard: "cubic-bezier(.4,0,.2,1)",
      },

      keyframes: {
        riseIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        sheetUp: {
          "0%": { transform: "translateY(100%)" },
          "100%": { transform: "translateY(0)" },
        },
        fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        spin: { to: { transform: "rotate(360deg)" } },
      },
      animation: {
        riseIn: "riseIn var(--d-base) var(--e-out) both",
        sheetUp: "sheetUp var(--d-sheet) var(--e-out) both",
        fadeIn: "fadeIn var(--d-base) var(--e-standard) both",
        shimmer: "shimmer 1.4s linear infinite",
        spin: "spin .7s linear infinite",
      },
    },
  },
  plugins: [],
};
