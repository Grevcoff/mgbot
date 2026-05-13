from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any


def get_batches_menu(batches: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает список партий с кнопками действий"""
    keyboard = []
    
    # Добавляем существующие партии
    for batch in batches:
        stage_emoji = {
            'soak': '💧',
            'dark': '🌑',
            'light': '☀️',
            'ready': '✅'
        }.get(batch['current_stage'], '❓')
        
        # Получаем количество непроданных лотов
        total_lots = batch.get('total_lots', 0)
        sold_lots = batch.get('sold_lots', 0)
        written_off_lots = batch.get('written_off_lots', 0)
        available_lots = total_lots - sold_lots - written_off_lots
        
        # Формируем текст кнопки с информацией о лотках
        if available_lots > 0:
            button_text = f"{stage_emoji} Партия #{batch['id']} ({batch['variety_name']}) - {available_lots} лот."
        else:
            button_text = f"{stage_emoji} Партия #{batch['id']} ({batch['variety_name']}) - нет лот."
        
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"batch_view_{batch['id']}"
        )])
    
    # Всегда добавляем кнопку "Добавить партию"
    keyboard.append([InlineKeyboardButton(
        text="➕ Добавить партию",
        callback_data="batch_add"
    )])
    
    # Всегда добавляем кнопку "Архив"
    keyboard.append([InlineKeyboardButton(
        text="📁 Архив",
        callback_data="batches_archive"
    )])
    
    # Всегда добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="back_to_menu"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_archive_batches_menu(batches: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает список архивных партий"""
    keyboard = []
    
    # Добавляем архивные партии
    for batch in batches:
        stage_emoji = {
            'soak': '💧',
            'dark': '🌑',
            'light': '☀️',
            'ready': '✅'
        }.get(batch['current_stage'], '❓')
        
        # Формируем текст с информацией о статусе лотов
        if batch.get('sold_lots', 0) > 0:
            status_info = f"Продано: {batch.get('sold_lots', 0)}"
        if batch.get('written_off_lots', 0) > 0:
            if status_info:
                status_info += f", Списано: {batch.get('written_off_lots', 0)}"
            else:
                status_info = f"Списано: {batch.get('written_off_lots', 0)}"
        
        button_text = f"{stage_emoji} Партия #{batch['id']} ({batch['variety_name']}) - {status_info}"
        
        keyboard.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"batch_view_{batch['id']}"
        )])
    
    # Кнопки возврата
    keyboard.append([InlineKeyboardButton(
        text="◀️ К активным партиям",
        callback_data="batches_list"
    )])
    keyboard.append([InlineKeyboardButton(
        text="🏠 Главное меню",
        callback_data="back_to_menu"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_batch_actions(batch_id: int, current_stage: str) -> InlineKeyboardMarkup:
    """Создает кнопки действий для партии"""
    keyboard = []
    
    # Кнопки в зависимости от этапа
    if current_stage != 'ready':
        keyboard.append([InlineKeyboardButton(
            text="✅ Перевести дальше",
            callback_data=f"batch_next_{batch_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text="� Детали",
        callback_data=f"batch_details_{batch_id}"
    )])
    
    if current_stage == 'ready':
        keyboard.append([InlineKeyboardButton(
            text="🛒 Начать продажу",
            callback_data=f"batch_sell_{batch_id}"
        )])
    
    if current_stage == 'ready':
        keyboard.append([InlineKeyboardButton(
            text="📋 Списать лоток",
            callback_data=f"lot_write_off_{batch_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text="📋 Списать все",
        callback_data=f"batch_write_off_{batch_id}"
    )])
    
    keyboard.append([InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="batches_list"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_stage_transition_buttons(batch_id: int, next_stage: str) -> InlineKeyboardMarkup:
    """Создает кнопки для уведомления о переходе этапа"""
    keyboard = []
    
    stage_names = {
        'soak': 'Темнота',
        'dark': 'Свет',
        'light': 'Готово'
    }
    
    next_stage_name = stage_names.get(next_stage, next_stage)
    
    keyboard.append([InlineKeyboardButton(
        text=f"✅ {next_stage_name}",
        callback_data=f"stage_next_{batch_id}"
    )])
    
    keyboard.append([InlineKeyboardButton(
        text="⏰ Напомнить через 1ч",
        callback_data=f"stage_remind_{batch_id}"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_varieties_for_batch(varieties: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает список культур для создания партии"""
    keyboard = []
    
    for variety in varieties:
        keyboard.append([InlineKeyboardButton(
            text=f"🌱 {variety['name']}",
            callback_data=f"batch_variety_{variety['id']}"
        )])
    
    if keyboard:
        keyboard.append([InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_menu"
        )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_batch_details_keyboard(batch_id: int) -> InlineKeyboardMarkup:
    """Кнопка для возврата к деталям партии"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="◀️ Назад к партии",
            callback_data=f"batch_view_{batch_id}"
        )]
    ])


def get_batch_delete_confirm(batch_id: int) -> InlineKeyboardMarkup:
    """Кнопки подтверждения удаления партии"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🗑️ Да, удалить",
            callback_data=f"batch_delete_confirm_{batch_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="batches_list"
        )]
    ])


def get_batch_write_off_confirm(batch_id: int) -> InlineKeyboardMarkup:
    """Кнопки подтверждения списания партии"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📋 Да, списать",
            callback_data=f"batch_write_off_confirm_{batch_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"batch_view_{batch_id}"
        )]
    ])


def get_lot_write_off_selection(lots: List[Dict], batch_id: int) -> InlineKeyboardMarkup:
    """Кнопки выбора лота для списания"""
    keyboard = []
    
    # Группируем лоты по строкам (по 5 в строке)
    row = []
    for lot in lots:
        row.append(InlineKeyboardButton(
            text=lot['lot_code'],
            callback_data=f"lot_write_off_confirm_{lot['id']}_{batch_id}"
        ))
        
        if len(row) == 5:
            keyboard.append(row)
            row = []
    
    if row:  # Добавляем оставшиеся лоты
        keyboard.append(row)
    
    # Кнопка отмены
    keyboard.append([InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=f"batch_view_{batch_id}"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_lot_write_off_confirm(lot_id: int, batch_id: int) -> InlineKeyboardMarkup:
    """Кнопки подтверждения списания лота"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📋 Да, списать лоток",
            callback_data=f"lot_write_off_execute_{lot_id}_{batch_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"lot_write_off_{batch_id}"
        )]
    ])
