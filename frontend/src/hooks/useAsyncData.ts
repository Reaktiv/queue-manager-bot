import { useCallback, useEffect, useRef, useState } from "react";
import type { ApiResponse } from "../types";

/*
 * Ma'lumot yuklashning yagona shakli: yuklanmoqda / xato / ma'lumot / qayta urinish.
 *
 * NEGA kerak: ilgari har bir sahifa shunday yozardi -
 *     api.listTasks(id).then((r) => setTasks(r.data || []))
 * ya'ni `r.success === false` holati JIM-JIT yutib yuborilardi va
 * foydalanuvchiga "Hali vazifa yo'q" degan BO'SH holat ko'rsatilardi.
 * Server xatosi "ma'lumot yo'q" ga aylanib qolardi - admin uchun bu
 * chalg'ituvchi. STEP 3 ning 13-bo'limi aniq "API error" va "retry"
 * holatlarini talab qiladi, shuning uchun shu yerda markazlashtiramiz.
 *
 * KESH (stale-while-revalidate): komponent qayta o'rnatilganda - masalan
 * foydalanuvchi guruhlar ro'yxatiga qaytib, keyin YANA o'sha guruhga
 * kirganda - ekran har safar bo'sh skeletdan boshlanardi, garchi bir
 * necha soniya oldin xuddi shu ma'lumot allaqachon yuklangan bo'lsa ham.
 * Bu ilova "qotib" his qilinishining asosiy sababi edi: har bosishda
 * to'liq qayta yuklanish. Endi so'nggi muvaffaqiyatli javob modul
 * darajasidagi keshda saqlanadi va DARHOL ko'rsatiladi, so'rov esa orqa
 * fonda (`revalidating`) yuboriladi - foydalanuvchi bo'sh skeletni FAQAT
 * ilova umrida shu kalit uchun BIRINCHI marta ko'radi.
 */

export interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  /** Keshdagi ma'lumot ko'rsatilib, orqa fonda yangilanayotganda `true`. */
  revalidating: boolean;
  /** Xatodan keyin qayta urinish yoki mutatsiyadan keyin yangilash. */
  reload: () => void;
}

interface CacheEntry {
  data: unknown;
}

// Ilova umri davomida yashaydigan oddiy Map - sahifa yopilganda (yoki
// qayta yuklanganda) tozalanadi. Bir nechta o'nlab kalitdan oshmaydi
// (har bir ekran/parametr birikmasi uchun bittadan), shuning uchun
// tozalash strategiyasi (LRU va h.k.) ortiqcha murakkablik bo'lardi.
const cache = new Map<string, CacheEntry>();

function buildKey(namespace: string, deps: unknown[]): string {
  return `${namespace}:${JSON.stringify(deps)}`;
}

export function useAsyncData<T>(
  /**
   * Kesh kaliti negizi - shu ma'lumot turini nomlaydi (masalan
   * `"group-tasks"`). `deps` bilan birga to'liq kalitni hosil qiladi,
   * shuning uchun bir xil `namespace`dagi turli parametrlar (masalan
   * boshqa-boshqa `group.id`) mustaqil keshlanadi.
   */
  namespace: string,
  /**
   * `null` = hali so'ramaymiz (foydalanuvchi yo'q, sheet yopiq, bo'lim
   * ochilmagan). Ilgari chaqiruv joylari buning o'rniga soxta hal
   * bo'lgan promise qaytarardi (`Promise.resolve({success:true,...})`) -
   * bu naqsh beshta joyda takrorlangan va niyatni yashirgan edi.
   */
  fetcher: (() => Promise<ApiResponse<T>>) | null,
  deps: unknown[]
): AsyncState<T> {
  /*
   * Fetcher har renderda yangi funksiya bo'ladi; uni deps'ga qo'shsak
   * cheksiz sikl hosil bo'lardi. Shuning uchun ref orqali saqlaymiz.
   * Yozish render paytida emas, effekt ichida amalga oshadi: render
   * toza (side-effectsiz) bo'lishi kerak, aks holda React render'ni
   * commit qilmasdan tashlab yuborsa ref eskirgan qiymat bilan qolardi.
   * Bu effekt fetch effektidan OLDIN e'lon qilingan - effektlar e'lon
   * tartibida ishlaydi, shuning uchun fetch doim eng so'nggi fetcher'ni ko'radi.
   */
  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  const key = buildKey(namespace, deps);

  const [state, setState] = useState<{ data: T | null; error: string | null; loading: boolean }>(
    () => {
      const cached = cache.get(key);
      return cached
        ? { data: cached.data as T, error: null, loading: false }
        : { data: null, error: null, loading: true };
    }
  );
  const [revalidating, setRevalidating] = useState(false);

  const [nonce, setNonce] = useState(0);
  // Kechikib kelgan eski javob yangisining ustiga yozmasligi uchun.
  const runIdRef = useRef(0);

  useEffect(() => {
    const runId = ++runIdRef.current;
    const run = fetcherRef.current;

    if (!run) {
      setState({ data: null, error: null, loading: false });
      setRevalidating(false);
      return;
    }

    const entry = cache.get(key);
    if (entry) {
      // Keshda bor - darhol ko'rsatamiz, orqa fonda yangilaymiz. Bo'sh
      // skelet YO'Q: foydalanuvchi eski (bir necha soniya oldingi)
      // ma'lumotni darhol ko'radi, u orqa fonda jimgina yangilanadi.
      setState({ data: entry.data as T, error: null, loading: false });
      setRevalidating(true);
    } else {
      setState((s) => ({ ...s, loading: true, error: null }));
      setRevalidating(false);
    }

    run()
      .then((res) => {
        if (runId !== runIdRef.current) return;
        if (res.success) {
          cache.set(key, { data: res.data });
          setState({ data: res.data, error: null, loading: false });
        } else if (entry) {
          // Orqa fondagi yangilanish muvaffaqiyatsiz bo'ldi, lekin
          // ekranda allaqachon ishlaydigan (eski) ma'lumot bor - uni
          // bitta vaqtinchalik xato bilan almashtirish orqaga qadam
          // bo'lardi. Eski ma'lumot qoladi, xato jimgina e'tiborsiz
          // qoldiriladi (xuddi shu narsa `catch`da ham amal qiladi).
          setState({ data: entry.data as T, error: null, loading: false });
        } else {
          setState({
            data: null,
            error: res.message || "Ma'lumotni yuklab bo'lmadi",
            loading: false,
          });
        }
        setRevalidating(false);
      })
      .catch(() => {
        // `client.ts` dagi `request()` odatda o'zi ushlaydi, bu qo'shimcha to'r.
        if (runId !== runIdRef.current) return;
        if (entry) {
          setState({ data: entry.data as T, error: null, loading: false });
        } else {
          setState({ data: null, error: "Serverga ulanib bo'lmadi", loading: false });
        }
        setRevalidating(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, revalidating, reload };
}
