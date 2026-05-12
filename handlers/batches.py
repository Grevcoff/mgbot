from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
import aiosqlite
from datetime import datetime

from database import Database
from states.batches import AddBatch
from keyboards.batches import batches_menu, batch_actions, stage_transition_notification, varieties_for_batch
from keyboards.main import back_keyboard
from utils.helpers import format_duration, format_datetime, validate_number, format_hours
from config import STAGE_NAMES, STAGE_TRANSITIONS, MAX_BATCH_QUANTITY

# Глобальная переменная для доступа к БД (устанавливается в main.py)
db = None

router = Router()

@router.callback_query(F.data == "batches_list")
async def batches_list_handler(callback: CallbackQuery):
    """Показать список партий"""
    batches = await db.get_all_batches()
    
    if not batches:
        await callback.message.edit_text(
            "🌱 *Мои партии*\n\n"
            "Пока нет ни одной партии. Создайте первую!",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="➕ Создать партию", callback_data="batch_add")],
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
            ]),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            "🌱 *Мои партии*\n\n"
            "Выберите партию для управления:",
            reply_markup=batches_menu(batches),
            parse_mode="Markdown"
        )
    
    await callback.answer()

@router.callback_query(F.data == "batch_add")
async def batch_add_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания новой партии"""
    varieties = await db.get_all_varieties()
    
    if not varieties:
        await callback.answer(
            "Сначала создайте хотя бы один шаблон культуры!",
            show_alert=True
        )
        return
    
    await state.set_state(AddBatch.choosing_variety)
    
    await callback.message.edit_text(
        "🌱 *Создание новой партии*\n\n"
        "Выберите культуру:",
        reply_markup=varieties_for_batch(varieties),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("batch_variety_"))
async def batch_variety_handler(callback: CallbackQuery, state: FSMContext):
    """Выбор культуры для партии"""
    variety_id = int(callback.data.split("_")[-1])
    
    await state.update_data(selected_variety_id=variety_id)
    await state.set_state(AddBatch.entering_quantity)
    
    await callback.message.edit_text(
        "🌱 *Создание новой партии*\n\n"
        "Введите количество лотков в партии:",
        reply_markup=back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AddBatch.entering_quantity)
async def batch_quantity_handler(message: Message, state: FSMContext):
    """Обработка количества лотков"""
    quantity = validate_number(message.text, 1, MAX_BATCH_QUANTITY, is_int=True)
    
    if quantity is None:
        await message.answer(
            f"❌ Введите целое число от 1 до {MAX_BATCH_QUANTITY}. Попробуйте снова:",
            reply_markup=back_keyboard()
        )
        return
    
    data = await state.get_data()
    variety_id = data['selected_variety_id']
    
    try:
        batch_id = await db.add_batch(variety_id, int(quantity))
        batch = await db.get_batch(batch_id)
        
        await state.clear()
        
        await message.answer(
            f"✅ Партия успешно создана!\n\n"
            f"🌱 *{batch['variety_name']}*\n"
            f"📦 Количество: {batch['quantity']} лотков\n"
            f"🏷️ Коды: MG-{datetime.now().year}-{batch_id:03d}xxx\n"
            f"⏱️ Этап: {STAGE_NAMES['soak']}",
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        
        # Показать обновлённый список партий
        batches = await db.get_all_batches()
        await message.answer(
            "🌱 *Мои партии*\n\nВыберите партию для управления:",
            reply_markup=batches_menu(batches),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при создании партии: {str(e)}",
            reply_markup=back_keyboard()
        )

@router.callback_query(F.data.startswith("batch_view_"))
async def batch_view_handler(callback: CallbackQuery):
    """Просмотр деталей партии"""
    batch_id = int(callback.data.split("_")[-1])
    batch = await db.get_batch(batch_id)
    
    if not batch:
        await callback.answer("Партия не найдена", show_alert=True)
        return
    
    # Получаем информацию о лотках
    async with db.db_path:
        async with aiosqlite.connect(db.db_path) as conn:
            async with conn.execute('''
                SELECT status, COUNT(*) FROM lots WHERE batch_id = ? GROUP BY status
            ''', (batch_id,)) as cursor:
                lots_stats = dict(await cursor.fetchall())
    
    stage_name = STAGE_NAMES.get(batch['current_stage'], batch['current_stage'])
    duration = format_duration(
        datetime.fromisoformat(batch['stage_started_at'])
    )
    
    total_lots = lots_stats.get('growing', 0) + lots_stats.get('sold', 0) + lots_stats.get('written_off', 0)
    
    text = (
        f"🌱 *{batch['variety_name']}*\n\n"
        f"📊 *Информация о партии:*\n"
        f"• ID: {batch['id']}\n"
        f"• Всего лотков: {batch['quantity']}\n"
        f"• Растёт: {lots_stats.get('growing', 0)}\n"
        f"• Продано: {lots_stats.get('sold', 0)}\n"
        f"• Списано: {lots_stats.get('written_off', 0)}\n\n"
        f"⏱️ *Текущий этап:* {stage_name}\n"
        f"• Начат: {format_datetime(datetime.fromisoformat(batch['stage_started_at']))}\n"
        f"• Длительность: {duration}\n\n"
        f"💡 *Полный цикл:* {format_hours(batch['soak_hours'] + batch['dark_hours'] + batch['light_hours'])}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=batch_actions(batch_id, batch['current_stage']),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("batch_details_"))
async def batch_details_handler(callback: CallbackQuery):
    """Подробная информация о партии с лотами"""
    batch_id = int(callback.data.split("_")[-1])
    batch = await db.get_batch(batch_id)
    
    if not batch:
        await callback.answer("Партия не найдена", show_alert=True)
        return
    
    # Получаем все лоты партии
    async with aiosqlite.connect(db.db_path) as conn:
        async with conn.execute('''
            SELECT lot_code, status, sale_price FROM lots WHERE batch_id = ? ORDER BY lot_code
        ''', (batch_id,)) as cursor:
            lots = await cursor.fetchall()
    
    text = (
        f"🌱 *{batch['variety_name']} - Детали*\n\n"
        f"📦 *Лоты партии:*\n"
    )
    
    for lot_code, status, sale_price in lots:
        status_emoji = {"growing": "🌱", "sold": "✅", "written_off": "❌"}.get(status, "❓")
        price_info = f" ({sale_price}₽)" if sale_price and status == "sold" else ""
        text += f"{status_emoji} {lot_code}{price_info}\n"
    
    text += f"\n📊 *Итого:* {len(lots)} лотков"
    
    await callback.message.edit_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data=f"batch_view_{batch_id}")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("stage_next_"))
async def stage_next_handler(callback: CallbackQuery):
    """Перевод партии на следующий этап"""
    batch_id = int(callback.data.split("_")[-1])
    batch = await db.get_batch(batch_id)
    
    if not batch:
        await callback.answer("Партия не найдена", show_alert=True)
        return
    
    current_stage = batch['current_stage']
    next_stage = STAGE_TRANSITIONS.get(current_stage)
    
    if not next_stage:
        await callback.answer("Партия уже на финальном этапе", show_alert=True)
        return
    
    success = await db.update_batch_stage(batch_id, next_stage)
    
    if success:
        stage_name = STAGE_NAMES.get(next_stage, next_stage)
        await callback.message.edit_text(
            f"✅ Партия переведена на этап: {stage_name}\n\n"
            f"🌱 {batch['variety_name']}",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="batches_list")]
            ])
        )
    else:
        await callback.answer("Ошибка при обновлении этапа", show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data.startswith("stage_remind_"))
async def stage_remind_handler(callback: CallbackQuery):
    """Напомнить через час (просто закрываем уведомление)"""
    await callback.answer("Напомню через час", show_alert=True)

@router.callback_query(F.data.startswith("batch_sell_"))
async def batch_sell_handler(callback: CallbackQuery, state: FSMContext):
    """Начало продажи лотков из партии"""
    batch_id = int(callback.data.split("_")[-1])
    
    await state.update_data(current_batch_id=batch_id)
    # Здесь будет переход к FSM продажи
    
    await callback.answer("Переход к продаже...", show_alert=True)

@router.callback_query(F.data == "cancel", StateFilter(AddBatch))
@router.callback_query(F.data == "back", StateFilter(AddBatch))
async def batch_cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Отмена создания партии"""
    await state.clear()
    
    batches = await db.get_all_batches()
    
    if not batches:
        await callback.message.edit_text(
            "🌱 *Мои партии*\n\n"
            "Пока нет ни одной партии. Создайте первую!",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="➕ Создать партию", callback_data="batch_add")],
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
            ]),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            "🌱 *Мои партии*\n\nВыберите партию для управления:",
            reply_markup=batches_menu(batches),
            parse_mode="Markdown"
        )
    
    await callback.answer()
