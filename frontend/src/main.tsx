import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

/*
 * Mavzuni BIRINCHI bo'yashdan oldin, sinxron o'rnatamiz.
 *
 * `index.html` Telegram skriptini modul skriptdan oldin yuklaydi, shuning
 * uchun `window.Telegram` shu yerda allaqachon mavjud. Ilgari mavzu faqat
 * `useTelegramAuth` effektida o'rnatilardi - ya'ni birinchi kadr noto'g'ri
 * mavzuda chizilib, keyin almashardi (miltillash). Bundan tashqari
 * `index.css` da butun yorug' palitra `@media (prefers-color-scheme)`
 * bloki ichida IKKINCHI marta takrorlangan edi; endi u kerak emas.
 *
 * Ish vaqtidagi o'zgarishlarni (foydalanuvchi Telegram mavzusini
 * almashtirsa) `useTelegramViewport` dagi `themeChanged` obunasi ushlaydi -
 * mavzuni boshqaradigan yagona joy o'sha.
 */
const prefersLight =
  typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: light)").matches;
const scheme = window.Telegram?.WebApp?.colorScheme ?? (prefersLight ? "light" : "dark");
document.documentElement.dataset.theme = scheme === "light" ? "light" : "dark";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
