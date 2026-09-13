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
 * Bu kutubxona emas - 40 qator oddiy hook. Hech qanday kesh, hech qanday
 * global do'kon: sahifalar avvalgidek mustaqil qoladi.
 */

export interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  /** Xatodan keyin qayta urinish yoki mutatsiyadan keyin yangilash. */
  reload: () => void;
}

export function useAsyncData<T>(
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

  const [state, setState] = useState<{
    data: T | null;
    error: string | null;
    loading: boolean;
  }>({ data: null, error: null, loading: true });

  const [nonce, setNonce] = useState(0);
  // Kechikib kelgan eski javob yangisining ustiga yozmasligi uchun.
  const runIdRef = useRef(0);

  useEffect(() => {
    const runId = ++runIdRef.current;

    const run = fetcherRef.current;
    if (!run) {
      setState({ data: null, error: null, loading: false });
      return;
    }

    setState((s) => ({ ...s, loading: true, error: null }));

    run()
      .then((res) => {
        if (runId !== runIdRef.current) return;
        if (res.success) {
          setState({ data: res.data, error: null, loading: false });
        } else {
          setState({
            data: null,
            error: res.message || "Ma'lumotni yuklab bo'lmadi",
            loading: false,
          });
        }
      })
      .catch(() => {
        // `client.ts` dagi `request()` odatda o'zi ushlaydi, bu qo'shimcha to'r.
        if (runId !== runIdRef.current) return;
        setState({ data: null, error: "Serverga ulanib bo'lmadi", loading: false });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  return { ...state, reload };
}
