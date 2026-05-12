from aiogram import Router, F, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery

from database import Database
from keyboards.main import main_menu, admin_menu
from utils.helpers import format_price
from config import ADMIN_ID

# Глобальная переменная для доступа к БД (устанавливается в main.py)
db = None

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message):
    """Обработка команды /start"""
    await message.answer(
        f"🌱 *{message.from_user.first_name}*, добро пожаловать в MicroGreen Bot!\n\n"
        "Этот бот поможет вам вести учёт микрозелени:\n"
        "• 🌱 Управление партиями\n"
        "• ⏰ Отслеживание этапов роста\n"
        "• 🛒 Продажа лотков\n"
        "• 📊 Статистика и отчёты\n\n"
        "Выберите действие в меню:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@router.message(lambda m: m.text == "📊 Статистика")
async def statistics_handler(message: Message):
    """Показ статистики"""
    stats = await db.get_statistics()
    
    text = (
        "📊 *Статистика проекта*\n\n"
        f"🌱 *Культуры:* {stats['total_varieties']}\n\n"
        f"📦 *Партии по этапам:*\n"
    )
    
    # Статистика по партиям
    stage_names = {
        'soak': 'Замачивание',
        'dark': 'Темнота', 
        'light': 'Свет',
        'ready': 'Готово'
    }
    
    for stage, count in stats.get('batches_by_stage', {}).items():
        stage_name = stage_names.get(stage, stage)
        text += f"• {stage_name}: {count}\n"
    
    text += f"\n📋 *Лотки:*\n"
    
    # Статистика по лоткам
    for status, count in stats.get('lots_by_status', {}).items():
        status_emoji = {
            'growing': '🌱 Растёт',
            'sold': '✅ Продано',
            'written_off': '❌ Списано'
        }.get(status, f"❓ {status}")
        text += f"• {status_emoji}: {count}\n"
    
    text += f"\n💰 *Финансы:*\n"
    text += f"• Общая выручка: {format_price(stats['total_revenue'])}\n"
    text += f"• Готово к продаже: {stats['ready_for_sale']} лотков"
    
    await message.answer(text, reply_markup=main_menu(), parse_mode="Markdown")

@router.message(lambda m: m.text == "🌱 Мои партии")
async def my_batches_handler(message: Message):
    """Переход к списку партий"""
    batches = await db.get_all_batches()
    
    if not batches:
        await message.answer(
            "🌱 *Мои партии*\n\n"
            "Пока нет ни одной партии. Создайте первую!",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="➕ Создать партию", callback_data="batch_add")],
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
            ]),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "🌱 *Мои партии*\n\n"
            "Выберите партию для управления:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="📋 Список партий", callback_data="batches_list")],
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
            ]),
            parse_mode="Markdown"
        )

@router.message(lambda m: m.text == "➕ Новая партия")
async def new_batch_handler(message: Message):
    """Создание новой партии"""
    await message.answer(
        "🌱 *Создание новой партии*\n\n"
        "Перейдите к выбору культуры:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Создать партию", callback_data="batch_add")]
        ]),
        parse_mode="Markdown"
    )

@router.message(lambda m: m.text == "🛒 Продажа лотков")
async def sell_handler(message: Message):
    """Переход к продаже"""
    await message.answer(
        "🛒 *Продажа лотков*\n\n"
        "Начать процесс продажи:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🛒 Начать продажу", callback_data="sell_start")]
        ]),
        parse_mode="Markdown"
    )

@router.message(lambda m: m.text == "📦 Шаблоны культур")
async def templates_handler(message: Message):
    """Переход к шаблонам культур"""
    varieties = await db.get_all_varieties()
    
    if not varieties:
        await message.answer(
            "📦 *Шаблоны культур*\n\n"
            "Пока нет ни одного шаблона. Создайте первый!",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="➕ Добавить шаблон", callback_data="template_add")],
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
            ]),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "📦 *Шаблоны культур*\n\n"
            "Выберите шаблон для управления:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="📋 Список шаблонов", callback_data="templates_list")]
            ]),
            parse_mode="Markdown"
        )

@router.message(lambda m: m.text == "⚙️ Настройки")
async def settings_handler(message: Message):
    """Настройки бота"""
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "⚙️ *Настройки*\n\n"
            "Административные функции:",
            reply_markup=admin_menu(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "⚙️ *Настройки*\n\n"
            "У вас нет доступа к административным функциям.",
            reply_markup=main_menu(),
            parse_mode="Markdown"
        )

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "🌱 *MicroGreen Bot*\n\n"
        "Выберите действие в меню:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_"))
async def admin_handler(callback: CallbackQuery):
    """Обработка административных функций"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    action = callback.data.split("_")[1]
    
    if action == "reset_db":
        await callback.message.edit_text(
            "⚠️ *Сброс базы данных*\n\n"
            "Это действие удалит все данные! Подтвердите:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🗑️ Да, удалить всё", callback_data="admin_reset_confirm")],
                [types.InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")]
            ]),
            parse_mode="Markdown"
        )
        await callback.answer()
    
    elif action == "reset_confirm":
        try:
            await db.reset_db()
            await callback.message.edit_text(
                "✅ База данных успешно сброшена",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            await callback.message.edit_text(
                f"❌ Ошибка при сбросе БД: {str(e)}",
                reply_markup=admin_menu(),
                parse_mode="Markdown"
            )
        await callback.answer()
    
    elif action == "export":
        # Простая функция экспорта (можно расширить)
        try:
            varieties = await db.get_all_varieties()
            batches = await db.get_all_batches()
            orders = await db.get_all_orders()
            
            export_text = (
                f"📤 *Экспорт данных*\n\n"
                f"🌱 Культур: {len(varieties)}\n"
                f"📦 Партий: {len(batches)}\n"
                f"💰 Заказов: {len(orders)}\n\n"
                f"Данные успешно собраны."
            )
            
            await callback.message.edit_text(
                export_text,
                reply_markup=admin_menu(),
                parse_mode="Markdown"
            )
        except Exception as e:
            await callback.message.edit_text(
                f"❌ Ошибка при экспорте: {str(e)}",
                reply_markup=admin_menu(),
                parse_mode="Markdown"
            )
        await callback.answer()
    
    elif action == "back":
        await callback.message.edit_text(
            "⚙️ *Настройки*\n\n"
            "Выберите действие:",
            reply_markup=admin_menu(),
            parse_mode="Markdown"
        )
        await callback.answer()

# Обработка неизвестных сообщений (перенесено в конец main.py для правильного порядка)
# @router.message(F.text)
# async def unknown_message_handler(message: Message):
#     """Обработка неизвестных сообщений"""
#     await message.answer(
#         "❌ Неизвестная команда.\n\n"
#         "Используйте кнопки главного меню для навигации.",
#         reply_markup=main_menu()
#     )
