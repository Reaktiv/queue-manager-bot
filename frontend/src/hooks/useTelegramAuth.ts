import { useEffect, useState } from "react";
import { api, setTokens } from "../api/client";
import type { AuthUser } from "../types";

declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        initData: string;
        ready: () => void;
        expand: () => void;
        colorScheme: "light" | "dark";
      };
    };
  }
}

interface AuthState {
  loading: boolean;
  error: string | null;
  user: AuthUser | null;
}

/**
 * Mini App ochilganda Telegram avtomatik `initData` beradi. Biz shu
 * ma'lumotni backend'ga yuborib, JWT olamiz. Agar Telegram tashqarisida
 * (oddiy brauzerda) ochilsa - xato ko'rsatiladi (bu ilova faqat Mini App
 * sifatida ishlashi kerak).
 */
export function useTelegramAuth(): AuthState {
  const [state, setState] = useState<AuthState>({ loading: true, error: null, user: null });

  useEffect(() => {
    const webApp = window.Telegram?.WebApp;

    if (!webApp || !webApp.initData) {
      setState({
        loading: false,
        error: "Bu ilova faqat Telegram Mini App sifatida ishlaydi. Iltimos, botdagi tugma orqali oching.",
        user: null,
      });
      return;
    }

    webApp.ready();
    webApp.expand();

    api
      .loginWithTelegram(webApp.initData)
      .then((response) => {
        if (response.success && response.data) {
          setTokens(response.data.access_token, response.data.refresh_token);
          setState({ loading: false, error: null, user: response.data.user });
        } else {
          setState({ loading: false, error: response.message || "Kirish muvaffaqiyatsiz", user: null });
        }
      })
      .catch(() => {
        setState({ loading: false, error: "Backend bilan bog'lanib bo'lmadi", user: null });
      });
  }, []);

  return state;
}
