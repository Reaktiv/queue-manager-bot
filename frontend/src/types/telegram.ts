/*
 * Telegram WebApp API tiplari.
 *
 * NEGA `@twa-dev/sdk` dan import qilmaymiz (u package.json da bor):
 *   `@twa-dev/sdk/dist/sdk.js` ichida `require("./telegram-web-apps")` bor -
 *   bu 88 kB lik Telegram runtime polifilini bundle'ga qo'shadi. Lekin
 *   `index.html` allaqachon rasmiy skriptni yuklaydi
 *   (https://telegram.org/js/telegram-web-app.js), ya'ni runtime ikki
 *   marta kelardi va bundle ~88 kB ga shishardi.
 *
 *   `@twa-dev/types` esa faqat tiplar beradi, lekin u package.json da
 *   e'lon qilinmagan (tranzitiv bog'liqlik) va `main: index.js` mavjud
 *   bo'lmagan faylga ishora qiladi - npm hoisting o'zgarsa sinadi.
 *
 * Shuning uchun: o'zimiz FOYDALANADIGAN qismni aniq e'lon qilamiz.
 * Nol bayt, nol yangi bog'liqlik, to'liq tip xavfsizligi.
 *
 * Manba: https://core.telegram.org/bots/webapps
 */

export interface TelegramHapticFeedback {
  impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
  notificationOccurred: (type: "error" | "success" | "warning") => void;
  selectionChanged: () => void;
}

export interface TelegramBackButton {
  isVisible: boolean;
  show: () => void;
  hide: () => void;
  onClick: (cb: () => void) => void;
  offClick: (cb: () => void) => void;
}

export type TelegramEventName =
  | "themeChanged"
  | "viewportChanged"
  | "mainButtonClicked"
  | "backButtonClicked";

export interface TelegramWebApp {
  initData: string;
  colorScheme: "light" | "dark";

  /** Joriy ko'rinadigan balandlik - klaviatura ochilganda o'zgaradi. */
  viewportHeight: number;
  /** Klaviatura/animatsiyadan qat'i nazar barqaror balandlik - layout uchun shu ishlatiladi. */
  viewportStableHeight: number;
  isExpanded: boolean;

  ready: () => void;
  expand: () => void;

  BackButton: TelegramBackButton;
  HapticFeedback: TelegramHapticFeedback;

  onEvent: (event: TelegramEventName, cb: () => void) => void;
  offEvent: (event: TelegramEventName, cb: () => void) => void;
}

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp };
  }
}

/** Telegram muhitidan tashqarida (oddiy brauzer) `undefined` qaytaradi. */
export function getWebApp(): TelegramWebApp | undefined {
  return window.Telegram?.WebApp;
}
