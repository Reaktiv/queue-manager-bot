# Ishga tushirish

## Lokal ishlab chiqish (tavsiya etiladi)

Uchta terminal:

```bash
./run-backend.sh     # postgres+redis (docker) + migratsiya + backend :8005 + bot
./run-frontend.sh    # vite dev server :5175, /api -> :8005
./run-tunnel.sh      # Mini App uchun ommaviy HTTPS manzil (cloudflared)
```

`run-tunnel.sh` chiqargan `https://...` manzilini BotFather'ga qo'ying:
`/setmenubutton` -> botni tanlang -> manzilni kiriting.

Portlarni almashtirish: `BACKEND_PORT=9000 ./run-backend.sh`

## Docker (hammasi konteynerda)

```bash
docker compose up -d --build
docker compose logs -f
```
Kirish nuqtasi: http://localhost (nginx), API: http://localhost:8000/docs

## Sozlamalar

| Fayl | Vazifasi | Git'da |
|---|---|---|
| `.env` | Barcha sozlamalar va sirlar - yagona manba | yo'q |
| `.env.local` | Faqat shu mashinaga tegishli farqlar, `.env` ustidan yozadi | yo'q |

Backend ikkalasini ham loyiha ildizidan o'qiydi. Docker ichida `.env.local`
yo'q - u yerda qiymatlar `env_file` orqali environment sifatida keladi.

**`DEV_AUTH_BYPASS`** - `true` bo'lsa initData imzosi, JWT va bot secret'i
umuman tekshirilmaydi. Faqat imzosiz lokal test uchun. **Tunnel ochiq
bo'lganda hech qachon yoqmang** - manzilni bilgan har kim Super Admin bo'lib
kiradi. Default: `false`.

## Testlar va migratsiya

```bash
backend/.venv/bin/python -m pytest backend/tests -q   # 37 ta test
cd backend && .venv/bin/alembic upgrade head
```
Testlar alohida `qmb_test_db` bazasida ishlaydi (yo'q bo'lsa o'zi yaratiladi),
ishchi baza tegilmaydi.

## Tunnel haqida

ngrok'ning bepul rejimi HTML sahifa uchun o'zining ogohlantirish sahifasini
qaytaradi (`ERR_NGROK_6024`). Uni faqat maxsus header bilan chetlab o'tish
mumkin, Telegram WebView esa header qo'sha olmaydi - natijada Mini App
o'rniga o'sha sahifa ochiladi. Shuning uchun `cloudflared` ishlatiladi.
