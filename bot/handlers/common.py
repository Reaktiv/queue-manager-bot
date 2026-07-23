"""
Barcha holatlarda ishlashi shart bo'lgan umumiy buyruqlar (masalan, /cancel).

Bu router main.py da eng birinchi bo'lib ro'yxatdan o'tkaziladi - shunda
boshqa routerlardagi FSM holat handlerlari (masalan, CreateTaskStates.waiting_for_name,
F.text) /cancel matnini o'zining kirish ma'lumoti sifatida "yutib yubormaydi".

Diqqat: bu handler HECH QANDAY state filtriga ega emas - shu sababli u har
qanday FSM holatida (yoki holat umuman bo'lmaganda ham) ishlaydi. `Command`
filtri holatdan qat'iy nazar ishlaydi, lekin aiogram'da bir xil update uchun
routerlar ro'yxatdan o'tkazilgan tartibda tekshiriladi va birinchi mos kelgan
handler ishga tushgach qidiruv to'xtaydi - shuning uchun bu router `main.py`da
ENG BIRINCHI bo'lib qo'shilishi SHART (boshqa har qanday tartib /cancel'ni
davom eta olmasligiga olib kelishi mumkin).
`ignore_case=True` - foydalanuvchi "/Cancel" yoki "/CANCEL" deb yozsa ham ishlaydi.
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

router = Router(name="common")


@router.message(Command("cancel", ignore_case=True))
async def handle_cancel(message: Message, state: FSMContext) -> None:
    """/cancel - joriy FSM jarayonini (qaysi holatda bo'lishidan qat'iy nazar) to'xtatadi.

    `active_` prefiksli data kalitlari (masalan, tanlangan guruh konteksti)
    ataylab saqlab qolinadi - ular alohida "joriy tanlov" ma'lumoti, FSM
    jarayonining bir qismi emas.
    """
    current_state = await state.get_state()
    data = await state.get_data()
    active_data = {k: v for k, v in data.items() if k.startswith("active_")}
    await state.clear()
    if active_data:
        await state.set_data(active_data)

    if current_state is None:
        await message.answer("ℹ️ Hozir bekor qilinadigan faol jarayon yo'q.")
    else:
        await message.answer("✅ Amal bekor qilindi.")
