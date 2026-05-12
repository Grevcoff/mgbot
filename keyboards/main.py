from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🌱 Мои партии"), KeyboardButton(text="➕ Новая партия")],
            [KeyboardButton(text="🛒 Продажа лотков"), KeyboardButton(text="📦 Шаблоны культур")],
            [KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def admin_menu() -> InlineKeyboardMarkup:
    """Админское меню"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Сбросить БД", callback_data="admin_reset_db")],
            [InlineKeyboardButton(text="📤 Экспорт данных", callback_data="admin_export")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ]
    )
    return keyboard

def cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )
    return keyboard

def back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой назад"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back")]
        ]
    )
    return keyboard
