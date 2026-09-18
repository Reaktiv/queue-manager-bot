"""
Bot xabarlari uchun oddiy i18n (ko'p tillilik) tizimi.

Foydalanish:
    from bot.i18n.translator import t
    text = t("welcome", lang="uz", name="Xojiakbar")

Standart til - "uz". Agar tarjima topilmasa, "uz" ga qaytadi.
"""

TRANSLATIONS: dict[str, dict[str, str]] = {
    "uz": {
        "welcome": "👋 Assalomu alaykum, {name}!\n\nBu bot orqali siz uy/ofis vazifalarini navbat bilan boshqarishingiz mumkin.\n\n📌 Guruhga qo'shilish uchun /join buyrug'ini bosing va taklif kodini kiriting.\n📌 Yangi guruh yaratish uchun /creategroup buyrug'ini bosing.\n❓ Barcha buyruqlar uchun /help",
        "ask_invite_code": "🔑 Guruhga qo'shilish uchun taklif kodini yuboring:",
        "joined_group": "✅ Siz \"{group_name}\" guruhiga muvaffaqiyatli qo'shildingiz!",
        "invalid_invite_code": "❌ Taklif kodi noto'g'ri yoki muddati o'tgan. Qaytadan urinib ko'ring.",
        "ask_group_name": "🏠 Yangi guruh nomini kiriting (masalan, \"Bizning uy\"):",
        "group_created": "✅ \"{name}\" guruhi yaratildi!\n\n🔑 Taklif kodi: <code>{invite_code}</code>\n\nBu kodni a'zolaringizga yuboring - ular /join buyrug'i orqali qo'shilishadi.",
        "no_active_group": "⚠️ Avval faol guruhni tanlang: /mygroups",
        "no_tasks": "🎉 Hozircha sizga tayinlangan vazifa yo'q (yoki navbat sizda emas).",
        "task_assigned_to_you": "📋 <b>{task}</b>\n\nSiz hozir navbatdasiz!",
        "ask_photo": "📷 Vazifani tasdiqlash uchun rasm yuboring (yoki tavsif bilan birga).",
        "task_completed": "✅ Vazifa muvaffaqiyatli yakunlandi! Navbat keyingi a'zoga o'tdi.",
        "task_pending_vote": "📤 Rasmingiz guruhga yuborildi - guruhdoshlaringiz bajarilganini tasdiqlashini kuting.",
        "not_your_turn": "❌ Hozir navbat sizda emas - vazifani bajara olmaysiz.",
        "stats_header": "📊 <b>Sizning statistikangiz:</b>",
        "reminder": "⏰ Eslatma: {user}, \"{task}\" vazifasini bajarish vaqti keldi! ({group})",
        "completed_notification": "✅ {user} \"{task}\" vazifasini muvaffaqiyatli bajardi.",
        "overdue_notification": "🔴 \"{task}\" vazifasi muddati o'tdi va hali ham {user} zimmasida.",
    },
    "ru": {
        "welcome": "👋 Здравствуйте, {name}!\n\nЭтот бот поможет вам управлять домашними/офисными задачами по очереди.\n\n📌 Чтобы присоединиться к группе, нажмите /join и введите код приглашения.\n📌 Чтобы создать новую группу, нажмите /creategroup.\n❓ Все команды: /help",
        "ask_invite_code": "🔑 Отправьте код приглашения для присоединения к группе:",
        "joined_group": "✅ Вы успешно присоединились к группе \"{group_name}\"!",
        "invalid_invite_code": "❌ Неверный или устаревший код приглашения. Попробуйте снова.",
        "ask_group_name": "🏠 Введите название новой группы (например, \"Наш дом\"):",
        "group_created": "✅ Группа \"{name}\" создана!\n\n🔑 Код приглашения: <code>{invite_code}</code>\n\nОтправьте этот код участникам - они смогут присоединиться через /join.",
        "no_active_group": "⚠️ Сначала выберите активную группу: /mygroups",
        "no_tasks": "🎉 Пока нет назначенных вам задач (или сейчас не ваша очередь).",
        "task_assigned_to_you": "📋 <b>{task}</b>\n\nСейчас ваша очередь!",
        "ask_photo": "📷 Отправьте фото для подтверждения задачи (можно с подписью).",
        "task_completed": "✅ Задача успешно завершена! Очередь передана следующему участнику.",
        "task_pending_vote": "📤 Ваше фото отправлено в группу - дождитесь подтверждения от участников.",
        "not_your_turn": "❌ Сейчас не ваша очередь - вы не можете выполнить задачу.",
        "stats_header": "📊 <b>Ваша статистика:</b>",
        "reminder": "⏰ Напоминание: {user}, пора выполнить задачу \"{task}\"! ({group})",
        "completed_notification": "✅ {user} успешно выполнил(а) задачу \"{task}\".",
        "overdue_notification": "🔴 Срок задачи \"{task}\" истёк, она всё ещё на {user}.",
    },
    "en": {
        "welcome": "👋 Hello, {name}!\n\nThis bot helps you manage household/office duties in turns.\n\n📌 To join a group, press /join and enter the invite code.\n📌 To create a new group, press /creategroup.\n❓ All commands: /help",
        "ask_invite_code": "🔑 Send the invite code to join a group:",
        "joined_group": "✅ You successfully joined \"{group_name}\"!",
        "invalid_invite_code": "❌ Invalid or expired invite code. Please try again.",
        "ask_group_name": "🏠 Enter a name for the new group (e.g. \"Our home\"):",
        "group_created": "✅ Group \"{name}\" created!\n\n🔑 Invite code: <code>{invite_code}</code>\n\nShare this code with your members - they can join via /join.",
        "no_active_group": "⚠️ Please select an active group first: /mygroups",
        "no_tasks": "🎉 No tasks assigned to you right now (or it's not your turn).",
        "task_assigned_to_you": "📋 <b>{task}</b>\n\nIt's your turn now!",
        "ask_photo": "📷 Send a photo to confirm the task (caption optional).",
        "task_completed": "✅ Task completed successfully! The queue moved to the next member.",
        "task_pending_vote": "📤 Your photo was sent to the group - wait for members to confirm it.",
        "not_your_turn": "❌ It's not your turn - you can't complete this task.",
        "stats_header": "📊 <b>Your statistics:</b>",
        "reminder": "⏰ Reminder: {user}, it's time to do \"{task}\"! ({group})",
        "completed_notification": "✅ {user} successfully completed \"{task}\".",
        "overdue_notification": "🔴 \"{task}\" is overdue and still assigned to {user}.",
    },
}

DEFAULT_LANGUAGE = "uz"


def t(key: str, lang: str | None = None, **kwargs: str) -> str:
    """
    Berilgan kalit va til bo'yicha tarjima matnini qaytaradi, placeholder'larni
    to'ldiradi. Til topilmasa yoki kalit mavjud bo'lmasa - "uz" ga qaytadi.
    """
    lang = lang if lang in TRANSLATIONS else DEFAULT_LANGUAGE
    template = TRANSLATIONS[lang].get(key) or TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
