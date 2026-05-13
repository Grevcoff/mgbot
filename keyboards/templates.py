from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any


def get_varieties_list(varieties: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает список культур с кнопками для редактирования и удаления"""
    keyboard = []
    
    for variety in varieties:
        keyboard.append([InlineKeyboardButton(
            text=f"🌱 {variety['name']}",
            callback_data=f"template_edit_{variety['id']}"
        )])
    
        
    keyboard.append([InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="back_to_menu"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_template_actions(variety_id: int) -> InlineKeyboardMarkup:
    """Создает кнопки действий для шаблона культуры"""
    keyboard = [
        [InlineKeyboardButton(
            text="✏️ Редактировать",
            callback_data=f"template_edit_data_{variety_id}"
        )],
        [InlineKeyboardButton(
            text="🗑️ Удалить",
            callback_data=f"template_delete_{variety_id}"
        )],
        [InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="templates_list"
        )]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_step_navigation(current_step: int, total_steps: int) -> InlineKeyboardMarkup:
    """Создает кнопки навигации для пошаговой формы"""
    keyboard = []
    
    # Кнопка "Назад" (кроме первого шага)
    if current_step > 1:
        keyboard.append([InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back"
        )])
    
    # Кнопка "Далее" (кроме последнего шага)
    if current_step < total_steps:
        keyboard.append([InlineKeyboardButton(
            text="➡️ Далее",
            callback_data="next"
        )])
    
    # Кнопка "Отмена" всегда доступна
    keyboard.append([InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="cancel"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_template_delete_confirm(variety_id: int) -> InlineKeyboardMarkup:
    """Создает кнопки подтверждения удаления шаблона"""
    keyboard = [
        [InlineKeyboardButton(
            text="🗑️ Да, удалить",
            callback_data=f"template_delete_confirm_{variety_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="templates_list"
        )]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_add_template_button() -> InlineKeyboardMarkup:
    """Создает кнопку добавления нового шаблона"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➕ Добавить шаблон",
            callback_data="template_add"
        )]
    ])


def get_edit_parameter_menu(variety_id: int) -> InlineKeyboardMarkup:
    """Создает меню выбора параметра для редактирования"""
    keyboard = [
        [InlineKeyboardButton(
            text="📝 Название культуры",
            callback_data=f"edit_param_name_{variety_id}"
        )],
        [InlineKeyboardButton(
            text="🌾 Семян на лоток (г)",
            callback_data=f"edit_param_seeds_{variety_id}"
        )],
        [InlineKeyboardButton(
            text="💰 Цена семян (₽/г)",
            callback_data=f"edit_param_seed_cost_{variety_id}"
        )],
        [InlineKeyboardButton(
            text="📦 Базовая стоимость (₽)",
            callback_data=f"edit_param_base_cost_{variety_id}"
        )],
        [InlineKeyboardButton(
            text="💳 Цена продажи (₽)",
            callback_data=f"edit_param_price_{variety_id}"
        )],
        [InlineKeyboardButton(
            text="⏰ Замачивание (часы)",
            callback_data=f"edit_param_soak_{variety_id}"
        )],
        [InlineKeyboardButton(
            text="🌑 Темнота (часы)",
            callback_data=f"edit_param_dark_{variety_id}"
        )],
        [InlineKeyboardButton(
            text="☀️ Свет (часы)",
            callback_data=f"edit_param_light_{variety_id}"
        )],
        [InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="templates_list"
        )]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
