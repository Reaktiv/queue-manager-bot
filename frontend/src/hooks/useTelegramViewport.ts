import { useEffect, useRef } from "react";
import { getWebApp } from "../types/telegram";

/*
 * Telegram viewport / mavzu / BackButton / haptika integratsiyasi.
 *
 * Muammo: `100vh` Telegram WebView'da noto'g'ri. Balandlik skroll paytida
 * (header yig'ilganda) va klaviatura ochilganda o'zgaradi, lekin `100vh`
 * o'zgarmaydi - natijada sahifa ostidan kesiladi yoki ortiqcha bo'sh joy
 * qoladi. Telegram `viewportStableHeight` beradi: klaviatura
 * animatsiyasidan qat'i nazar barqaror qiymat - layout uchun aynan shu kerak.
 *
 * Bu hook qiymatlarni CSS o'zgaruvchilariga yozadi, shunda ularni
 * istalgan joyda `h-[var(--tg-stable-viewport)]` ko'rinishida ishlatish
 * mumkin (AppScreen shuni qiladi).
 */

function setVar(name: string, value: string) {
  document.documentElement.style.setProperty(name, value);
}

/**
 * Viewport balandligini va mavzuni Telegram bilan sinxron ushlab turadi.
 * Ilovada BIR MARTA, eng yuqori komponentda chaqiriladi.
 */
export function useTelegramViewport(): void {
  useEffect(() => {
    const webApp = getWebApp();
    if (!webApp) return;

    const syncViewport = () => {
      if (webApp.viewportStableHeight > 0) {
        setVar("--tg-stable-viewport", `${webApp.viewportStableHeight}px`);
      }
    };

    /*
     * Mavzu almashinuvi. Ilgari `colorScheme` faqat bir marta, ilova
     * ochilganda o'qilardi - foydalanuvchi Telegram'da mavzuni
     * almashtirsa, Mini App eski mavzuda qolib ketardi.
     */
    const syncTheme = () => {
      document.documentElement.dataset.theme =
        webApp.colorScheme === "dark" ? "dark" : "light";
    };

    syncViewport();
    syncTheme();

    webApp.onEvent("viewportChanged", syncViewport);
    webApp.onEvent("themeChanged", syncTheme);

    return () => {
      webApp.offEvent("viewportChanged", syncViewport);
      webApp.offEvent("themeChanged", syncTheme);
    };
  }, []);
}

/**
 * Telegram'ning tizim "orqaga" tugmasini boshqaradi.
 *
 * `active` true bo'lganda tugma ko'rinadi va bosilganda `onBack` ishlaydi.
 * Bu Android'dagi tizim orqaga imo-ishorasini ham ushlaydi - usiz
 * foydalanuvchi sheet'ni yopmoqchi bo'lganda butun Mini App yopilib ketadi.
 */
export function useTelegramBackButton(active: boolean, onBack: () => void): void {
  /*
   * `onBack` odatda chaqiruv joyida inline funksiya bo'ladi (masalan
   * `onClose={() => setOpenTask(null)}`), ya'ni har renderda yangi
   * identifikatorga ega bo'ladi. Uni to'g'ridan-to'g'ri deps'ga qo'ysak,
   * effekt har renderda qayta ishga tushib, BackButton'ni qayta
   * ro'yxatdan o'tkazaverardi. Eng so'nggi qiymatni ref'da saqlaymiz -
   * effekt esa faqat `active` o'zgarganda ishlaydi.
   */
  const onBackRef = useRef(onBack);
  useEffect(() => {
    onBackRef.current = onBack;
  });

  useEffect(() => {
    const webApp = getWebApp();
    if (!webApp?.BackButton || !active) return;

    const handler = () => onBackRef.current();
    webApp.BackButton.onClick(handler);
    webApp.BackButton.show();

    return () => {
      webApp.BackButton.offClick(handler);
      webApp.BackButton.hide();
    };
  }, [active]);
}

/*
 * Haptika. Telegram tashqarisida jim-jit hech narsa qilmaydi, shuning
 * uchun chaqiruvchi tomonda tekshiruv yozish shart emas.
 */
export const haptics = {
  /** Tugma bosilganda / amal bajarilganda */
  press(style: "light" | "medium" | "heavy" = "light") {
    getWebApp()?.HapticFeedback?.impactOccurred(style);
  },
  /** Amal natijasi bildirilganda (toast bilan birga) */
  notify(type: "success" | "error" | "warning") {
    getWebApp()?.HapticFeedback?.notificationOccurred(type);
  },
  /** Tab / segment almashganda */
  select() {
    getWebApp()?.HapticFeedback?.selectionChanged();
  },
};
