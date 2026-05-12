from aiogram.fsm.state import State, StatesGroup
from typing import List

class SellProcess(StatesGroup):
    choosing_batch = State()  # Выбор партии для продажи
    choosing_lots = State()   # Выбор конкретных лотков
    viewing_cart = State()    # Просмотр корзины
    entering_buyer = State()  # Ввод имени покупателя
    
    # Data stored in FSM:
    # cart: List[int] - список ID выбранных лотков
    # temp_price: float - временная цена для выбранных лотков
    # current_batch_id: int - ID текущей партии
    # selected_lots: List[int] - выбранные лоты в текущей партии
