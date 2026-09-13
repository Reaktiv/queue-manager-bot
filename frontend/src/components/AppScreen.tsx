import type { ReactNode } from "react";

/*
 * Ilova qobig'i: viewport, xavfsiz zonalar, aurora foni va markazlash.
 *
 * Ilgari har bir sahifa `min-h-screen` (ya'ni 100vh) ishlatardi, bu
 * Telegram WebView'da noto'g'ri balandlik beradi. Bu yerda balandlik
 * Telegram'ning `viewportStableHeight` qiymatidan olinadi; u bo'lmasa
 * `100dvh` ga, u ham bo'lmasa `100vh` ga tushadi.
 *
 * STEP 3 da sahifalar shu qobiqqa ko'chiriladi.
 */

export function AppScreen({ children }: { children: ReactNode }) {
  /*
   * `useTelegramViewport()` ATAYLAB bu yerda chaqirilmaydi - u ilova
   * ildizida (App.tsx) bir marta chaqiriladi. Aks holda AppScreen har
   * safar qayta o'rnatilganda Telegram hodisalariga takroriy obuna
   * bo'lib ketardi.
   *
   * `className`/`padded` proplari ATAYLAB yo'q: ilova bo'ylab yagona
   * chaqiruv `<AppScreen>{children}</AppScreen>` (App.tsx) - ishlatilmaydigan
   * moslashuvchanlikni saqlash shart emas edi.
   */
  return (
    <div
      className="relative mx-auto flex w-full max-w-lg flex-col bg-ground"
      style={{
        minHeight: "var(--tg-stable-viewport, 100dvh)",
      }}
    >
      {/* Yagona qo'zg'almas yorug'lik qatlami - glass shunga sinadi.
          `fixed` + animatsiyasiz, shuning uchun skrollda qayta chizilmaydi. */}
      <div className="app-aurora" aria-hidden />

      {/* Kontent aurora ustida */}
      <div className="relative z-10 flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  );
}

/*
 * Yopishqoq sarlavha. Yagona "glass-medium" yuza - kontent uning
 * ostidan suzib o'tadi. Ilovada bir vaqtda faqat SHU blur ko'rinadi
 * (sheet ochilganda u glass-strong bilan almashadi).
 */
export function AppHeader({ children }: { children: ReactNode }) {
  return (
    <header
      className="app-chrome glass-medium sticky top-0 z-40 px-gutter pb-3 pt-safe"
      /* Bitta marta kompozitsiya qatlamiga ko'taramiz: blur qilingan
         yopishqoq element skrollda har kadrda qayta chizilmasin. */
      style={{ transform: "translateZ(0)" }}
    >
      {children}
    </header>
  );
}

/**
 * Skroll qilinadigan asosiy maydon. Pastdagi xavfsiz zona (Android
 * imo-ishora chizig'i) hisobga olinadi.
 */
export function AppMain({ children }: { children: ReactNode }) {
  return (
    <main className="flex-1 px-gutter pb-8 pt-4">
      {children}
      <div className="pb-safe" aria-hidden />
    </main>
  );
}
