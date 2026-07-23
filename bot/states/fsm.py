"""
Bot uchun barcha FSM (Finite State Machine) holatlari - bitta joyda,
chunki turli handlerlar bir-birining state'iga murojaat qilishi mumkin.
"""
from aiogram.fsm.state import State, StatesGroup


class JoinGroupStates(StatesGroup):
    waiting_for_invite_code = State()


class CreateGroupStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_chat_id = State()


class CreateTaskStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_interval_days = State()
    waiting_for_start_date = State()
    waiting_for_reminder_interval_min = State()
    waiting_for_reminder_interval_max = State()
    waiting_for_reminder_start_hour = State()
    waiting_for_reminder_end_hour = State()
    waiting_for_photo_requirement = State()
    confirm = State()


class CompletionStates(StatesGroup):
    waiting_for_photo = State()


class SwapStates(StatesGroup):
    waiting_for_first_member = State()
    waiting_for_second_member = State()


class EditReminderStates(StatesGroup):
    waiting_for_min = State()
    waiting_for_max = State()
    waiting_for_start_hour = State()
    waiting_for_end_hour = State()
