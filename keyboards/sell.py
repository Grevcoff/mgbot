from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict

def sell_batches_menu(batches: List[Dict]) -> InlineKeyboardMarkup:
    """Меню выбора партий для продажи"""
    keyboard = []
    
    for batch in batches:
        text = f"🌱 {batch['variety_name']} - {batch['quantity']}шт"
        keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"sell_batch_{batch['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def sell_lots_selection(lots: List[Dict], selected_lots: List[int]) -> InlineKeyboardMarkup:
    """Выбор лотков для продажи"""
    keyboard = []
    
    # Группируем лоты по строкам (по 4 в ряд)
    for i in range(0, len(lots), 4):
        row = []
        for j in range(i, min(i + 4, len(lots))):
            lot = lots[j]
            lot_id = lot['id']
            lot_number = lot['lot_code'].split('-')[-1]
            
            # Определяем статус кнопки
            if lot_id in selected_lots:
                emoji = "✅"
            else:
                emoji = "⭕"
            
            row.append(
                InlineKeyboardButton(
                    text=f"{emoji}{lot_number}",
                    callback_data=f"sell_lot_{lot_id}"
                )
            )
        
        if row:  # Добавляем только непустые строки
            keyboard.append(row)
    
    # Кнопки управления
    if selected_lots:
        keyboard.append([
            InlineKeyboardButton(text="✅ Добавить в заказ", callback_data="sell_add_to_cart")
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="cancel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def sell_cart_keyboard(cart_items: List[Dict], total_amount: float) -> InlineKeyboardMarkup:
    """Клавиатура корзины"""
    keyboard = []
    
    if cart_items:
        keyboard.extend([
            [InlineKeyboardButton(text="➕ Добавить ещё культуры", callback_data="sell_add_more")],
            [InlineKeyboardButton(text="💰 Оформить заказ", callback_data="sell_checkout")],
            [InlineKeyboardButton(text="🗑️ Очистить корзину", callback_data="sell_clear_cart")]
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="cancel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def sell_price_keyboard() -> InlineKeyboardMarkup:
    """Выбор цены для лотков"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Стандартная цена", callback_data="price_default")],
            [InlineKeyboardButton(text="✏️ Указать свою цену", callback_data="price_custom")],
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="cancel")]
        ]
    )
    return keyboard
