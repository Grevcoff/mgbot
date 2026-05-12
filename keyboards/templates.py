from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict

def templates_menu(varieties: List[Dict]) -> InlineKeyboardMarkup:
    """Меню шаблонов культур"""
    keyboard = []
    
    # Добавляем кнопки для каждой культуры
    for variety in varieties:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🌱 {variety['name']}",
                callback_data=f"template_edit_{variety['id']}"
            )
        ])
    
    # Добавляем кнопки управления
    keyboard.extend([
        [InlineKeyboardButton(text="➕ Добавить шаблон", callback_data="template_add")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def template_actions(variety_id: int) -> InlineKeyboardMarkup:
    """Действия с шаблоном"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"template_edit_data_{variety_id}")],
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"template_delete_{variety_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="templates_list")]
        ]
    )
    return keyboard

def template_delete_confirm(variety_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Да, удалить", callback_data=f"template_delete_confirm_{variety_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"template_edit_{variety_id}")]
        ]
    )
    return keyboard
