from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict
from config import STAGE_NAMES

def batches_menu(batches: List[Dict]) -> InlineKeyboardMarkup:
    """Меню партий"""
    keyboard = []
    
    for batch in batches:
        stage_name = STAGE_NAMES.get(batch['current_stage'], batch['current_stage'])
        text = f"🌱 {batch['variety_name']} - {batch['quantity']}шт ({stage_name})"
        keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"batch_view_{batch['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="➕ Создать партию", callback_data="batch_add"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def batch_actions(batch_id: int, current_stage: str) -> InlineKeyboardMarkup:
    """Действия с партией"""
    keyboard = []
    
    if current_stage == "ready":
        keyboard.append([
            InlineKeyboardButton(text="🛒 Продать лотки", callback_data=f"batch_sell_{batch_id}")
        ])
    
    keyboard.extend([
        [InlineKeyboardButton(text="📊 Детали", callback_data=f"batch_details_{batch_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="batches_list")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def stage_transition_notification(batch_id: int, next_stage: str) -> InlineKeyboardMarkup:
    """Кнопки для уведомления о завершении этапа"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Перевести дальше", callback_data=f"stage_next_{batch_id}")],
            [InlineKeyboardButton(text="⏸️ Напомнить через 1ч", callback_data=f"stage_remind_{batch_id}")]
        ]
    )
    return keyboard

def varieties_for_batch(varieties: List[Dict]) -> InlineKeyboardMarkup:
    """Выбор культуры для новой партии"""
    keyboard = []
    
    for variety in varieties:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🌱 {variety['name']}",
                callback_data=f"batch_variety_{variety['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="cancel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
