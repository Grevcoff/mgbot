from aiogram.fsm.state import State, StatesGroup

class AddBatch(StatesGroup):
    choosing_variety = State()  # Выбор культуры
    entering_quantity = State()  # Ввод количества лотков
    
    # Data stored in FSM:
    # selected_variety_id: int - ID выбранной культуры
