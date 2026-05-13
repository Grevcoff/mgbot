from aiogram.fsm.state import State, StatesGroup


class ResetDB(StatesGroup):
    """Состояния для сброса базы данных"""
    waiting_code = State()
