from aiogram.fsm.state import State, StatesGroup

class TemplateForm(StatesGroup):
    name = State()           # Название культуры
    seeds_per_lot = State()  # Семян на лоток (грамм)
    seed_cost = State()      # Цена семян за грамм
    base_cost = State()      # Базовая стоимость (контейнер + субстрат)
    default_price = State()  # Цена продажи по умолчанию
    soak_hours = State()     # Часы замачивания
    dark_hours = State()     # Часы в темноте
    light_hours = State()    # Часы на свету
    
    # Data stored in FSM:
    # editing_id: int - ID редактируемого шаблона (None для нового)
    # temp_data: dict - временные данные формы
