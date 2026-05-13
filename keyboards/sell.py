from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any


def get_ready_batches(batches: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает список готовых партий для продажи"""
    keyboard = []
    
    for batch in batches:
        available_lots = batch.get('available_lots', 0)
        text = f"🌱 {batch['variety_name']} - {available_lots} лот. доступно"
        
        keyboard.append([InlineKeyboardButton(
            text=text,
            callback_data=f"sell_batch_{batch['id']}"
        )])
    
    if keyboard:
        keyboard.append([InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_menu"
        )])
    else:
        # Если нет готовых партий с лотками
        keyboard.append([InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_menu"
        )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_lot_selection_buttons(lots: List[Dict[str, Any]], selected: List[int]) -> InlineKeyboardMarkup:
    """Создает кнопки для выбора лотов с подсветкой выбранных"""
    keyboard = []
    row = []
    
    for i, lot in enumerate(lots, 1):
        lot_id = lot['id']
        is_selected = lot_id in selected
        
        # Показываем номер лота или галочку если выбран
        btn_text = f"✅" if is_selected else str(i)
        
        row.append(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"sell_lot_{lot_id}"
        ))
        
        # Новая строка каждые 5 кнопок
        if len(row) % 5 == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Кнопки действий
    if selected:
        keyboard.extend([
            [InlineKeyboardButton(
                text="🛒 Добавить в корзину",
                callback_data="sell_add_to_cart"
            )],
            [InlineKeyboardButton(
                text="❌ Отменить выбор",
                callback_data="cancel"
            )],
            [InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_menu"
            )]
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="back_to_menu"
            )]
        )
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cart_actions() -> InlineKeyboardMarkup:
    """Кнопки действий с корзиной"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➕ Добавить ещё",
            callback_data="sell_add_more"
        )],
        [InlineKeyboardButton(
            text="� Оформить",
            callback_data="sell_checkout"
        )],
        [InlineKeyboardButton(
            text="🗑️ Очистить",
            callback_data="sell_clear_cart"
        )]
    ])


def get_price_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора цены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💰 Стандартная цена",
            callback_data="price_default"
        )],
        [InlineKeyboardButton(
            text="✏️ Своя цена",
            callback_data="price_custom"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="sell_cancel_price"
        )]
    ])


def get_buyer_selection(buyers: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает список покупателей с кнопкой добавления нового"""
    keyboard = []
    
    for buyer in buyers:
        text = f"👤 {buyer['name']} - {buyer['orders_count']} заказов"
        keyboard.append([InlineKeyboardButton(
            text=text,
            callback_data=f"buyer_select_{buyer['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text="➕ Новый покупатель",
        callback_data="buyer_add_new"
    )])
    
    keyboard.append([InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="back_to_menu"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
