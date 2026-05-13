from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite
from datetime import datetime

from database import Database
from states.batches import AddBatch
from states.sell import SellProcess
from keyboards.batches import get_batches_menu, get_batch_actions, get_stage_transition_buttons, get_varieties_for_batch, get_archive_batches_menu, get_batch_write_off_confirm, get_lot_write_off_selection, get_lot_write_off_confirm
from keyboards.sell import get_lot_selection_buttons
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
            reply_markup=get_batches_menu(batches),
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
        reply_markup=get_varieties_for_batch(varieties),
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
            f"🏷️ Коды: MG-{datetime.now().year}-{batch_id:02d}-01, 02, 03...\n"
            f"⏱️ Этап: {STAGE_NAMES['soak']}",
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        
        # Показать обновлённый список партий
        batches = await db.get_all_batches()
        await message.answer(
            "🌱 *Мои партии*\n\nВыберите партию для управления:",
            reply_markup=get_batches_menu(batches),
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
        f"• {'Выросло' if batch['current_stage'] == 'ready' else 'Растёт'}: {lots_stats.get('growing', 0)}\n"
        f"• Продано: {lots_stats.get('sold', 0)}\n"
        f"• Списано: {lots_stats.get('written_off', 0)}\n\n"
        f"⏱️ *Текущий этап:* {stage_name}\n"
        f"• Начат: {format_datetime(datetime.fromisoformat(batch['stage_started_at']))}\n"
        f"• Длительность: {duration}\n\n"
        f"💡 *Полный цикл:* {format_hours(batch['soak_hours'] + batch['dark_hours'] + batch['light_hours'])}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_batch_actions(batch_id, batch['current_stage']),
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
    
    # Очищаем предыдущие данные и начинаем продажу
    await state.update_data(cart=[], temp_price=0.0, current_batch_id=batch_id, selected_lots=[])
    
    # Получаем доступные лоты партии
    available_lots = await db.get_available_lots(batch_id)
    
    if not available_lots:
        await callback.answer("Нет доступных лотков в этой партии", show_alert=True)
        return
    
    await state.set_state(SellProcess.choosing_lots)
    
    await callback.message.edit_text(
        "🛒 *Выбор лотков*\n\n"
        "Выберите лотки для продажи (нажмите на номера):",
        reply_markup=get_lot_selection_buttons(available_lots, []),
        parse_mode="Markdown"
    )
    await callback.answer()

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
        try:
            await callback.message.edit_text(
                "🌱 *Мои партии*\n\nВыберите партию для управления:",
                reply_markup=get_batches_menu(batches),
                parse_mode="Markdown"
            )
        except Exception as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
    
    await callback.answer()


@router.callback_query(F.data.startswith("batch_next_"))
async def batch_next_handler(callback: CallbackQuery):
    """Перевод партии на следующий этап"""
    batch_id = int(callback.data.split("_")[-1])
    batch = await db.get_batch(batch_id)
    
    if not batch:
        await callback.answer("Партия не найдена", show_alert=True)
        return
    
    current_stage = batch['current_stage']
    
    # Определяем следующий этап
    stage_transitions = {
        'soak': 'dark',
        'dark': 'light', 
        'light': 'ready'
    }
    
    next_stage = stage_transitions.get(current_stage)
    if not next_stage:
        await callback.answer("Партия уже на финальном этапе", show_alert=True)
        return
    
    try:
        success = await db.update_batch_stage(batch_id, next_stage)
        if success:
            stage_names = {
                'dark': 'Темнота',
                'light': 'Свет', 
                'ready': 'Готово'
            }
            # Получаем обновленные данные партии
            updated_batch = await db.get_batch(batch_id)
            
            # Получаем информацию о лотках
            async with aiosqlite.connect(db.db_path) as conn:
                async with conn.execute('''
                    SELECT status, COUNT(*) FROM lots WHERE batch_id = ? GROUP BY status
                ''', (batch_id,)) as cursor:
                    lots_stats = dict(await cursor.fetchall())
            
            stage_name = STAGE_NAMES.get(updated_batch['current_stage'], updated_batch['current_stage'])
            
            # Безопасная обработка stage_started_at
            try:
                if updated_batch['stage_started_at']:
                    duration = format_duration(
                        datetime.fromisoformat(updated_batch['stage_started_at'])
                    )
                    start_time = format_datetime(datetime.fromisoformat(updated_batch['stage_started_at']))
                else:
                    duration = "0ч"
                    start_time = "Неизвестно"
            except Exception as e:
                duration = "Ошибка"
                start_time = "Ошибка"
            
            total_lots = lots_stats.get('growing', 0) + lots_stats.get('sold', 0) + lots_stats.get('written_off', 0)
            
            text = (
                f"🌱 *{updated_batch['variety_name']}*\n\n"
                f"📊 *Информация о партии:*\n"
                f"• ID: {updated_batch['id']}\n"
                f"• Всего лотков: {updated_batch['quantity']}\n"
                f"• {'Выросло' if batch['current_stage'] == 'ready' else 'Растёт'}: {lots_stats.get('growing', 0)}\n"
                f"• Продано: {lots_stats.get('sold', 0)}\n"
                f"• Списано: {lots_stats.get('written_off', 0)}\n\n"
                f"⏱️ *Текущий этап:* {stage_name}\n"
                f"• Начат: {start_time}\n"
                f"• Длительность: {duration}\n\n"
                f"💡 *Полный цикл:* {format_hours(updated_batch['soak_hours'] + updated_batch['dark_hours'] + updated_batch['light_hours'])}"
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=get_batch_actions(batch_id, updated_batch['current_stage']),
                parse_mode="Markdown"
            )
            
            await callback.answer(f"✅ Партия переведена на этап: {stage_names.get(next_stage, next_stage)}")
        else:
            await callback.answer("❌ Не удалось перевести партию", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("lot_write_off_") & ~F.data.startswith("lot_write_off_confirm_") & ~F.data.startswith("lot_write_off_execute_"))
async def lot_write_off_handler(callback: CallbackQuery):
    """Начало списания единичного лота"""
    batch_id = int(callback.data.split("_")[-1])
    batch = await db.get_batch(batch_id)
    
    if not batch:
        await callback.answer("Партия не найдена", show_alert=True)
        return
    
    # Получаем доступные лоты для списания
    available_lots = await db.get_available_lots(batch_id)
    
    if not available_lots:
        await callback.answer("Нет доступных лотов для списания", show_alert=True)
        return
    
    try:
        await callback.message.edit_text(
            f"📋 *Списание лотка*\n\n"
            f"Партия: {batch['variety_name']}\n"
            f"Доступно лотков: {len(available_lots)}\n\n"
            f"Выберите лоток для списания:",
            reply_markup=get_lot_write_off_selection(available_lots, batch_id),
            parse_mode="Markdown"
        )
    except Exception as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто показываем уведомление
            await callback.answer("Для списания выберите лоток из списка ниже", show_alert=False)
        else:
            raise
    await callback.answer()


@router.callback_query(F.data.startswith("lot_write_off_confirm_"))
async def lot_write_off_confirm_handler(callback: CallbackQuery):
    """Подтверждение списания лота"""
    parts = callback.data.split("_")
    lot_id = int(parts[4])
    batch_id = int(parts[5])
    
    lot = await db.get_lot_by_id(lot_id)
    batch = await db.get_batch(batch_id)
    
    if not lot or not batch:
        await callback.answer("Лот или партия не найдены", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"📋 *Списание лотка*\n\n"
        f"Лоток: {lot['lot_code']}\n"
        f"Партия: {batch['variety_name']}\n"
        f"Себестоимость: {lot['snapshot_cost']}₽\n\n"
        f"Лоток будет списан как убыток!\n"
        f"Подтвердите:",
        reply_markup=get_lot_write_off_confirm(lot_id, batch_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lot_write_off_execute_"))
async def lot_write_off_execute_handler(callback: CallbackQuery):
    """Выполнение списания лота"""
    parts = callback.data.split("_")
    lot_id = int(parts[4])
    batch_id = int(parts[5])
    
    lot = await db.get_lot_by_id(lot_id)
    
    if not lot:
        await callback.answer("Лот не найден", show_alert=True)
        return
    
    try:
        success = await db.write_off_lot(lot_id)
        if success:
            await callback.answer(f"📋 Лоток {lot['lot_code']} списан", show_alert=True)
            
            # Возвращаем к списку лотов для списания
            available_lots = await db.get_available_lots(batch_id)
            if available_lots:
                await callback.message.edit_text(
                    f"📋 *Списание лотка*\n\n"
                    f"Партия: {lot.get('variety_name', 'Unknown')}\n"
                    f"Осталось доступно: {len(available_lots)}\n\n"
                    f"Выберите следующий лоток:",
                    reply_markup=get_lot_write_off_selection(available_lots, batch_id),
                    parse_mode="Markdown"
                )
            else:
                # Если больше нет лотов, возвращаем к просмотру партии
                await callback.message.edit_text(
                    f"✅ Все лотки списаны!\n\n"
                    f"Партия: {lot.get('variety_name', 'Unknown')}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="◀️ Назад",
                            callback_data=f"batch_view_{batch_id}"
                        )]
                    ]),
                    parse_mode="Markdown"
                )
        else:
            await callback.answer("❌ Не удалось списать лоток", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("batch_write_off_") & ~F.data.startswith("batch_write_off_confirm_"))
async def batch_write_off_handler(callback: CallbackQuery):
    """Списание партии"""
    batch_id = int(callback.data.split("_")[-1])
    batch = await db.get_batch(batch_id)
    
    if not batch:
        await callback.answer("Партия не найдена", show_alert=True)
        return
    
    # Получаем информацию о лотках
    lots = await db.get_available_lots(batch_id)
    sold_lots_count = len([lot for lot in await db.get_all_lots() if lot['batch_id'] == batch_id and lot['status'] == 'sold'])
    
    try:
        await callback.message.edit_text(
            f"📋 *Списание партии*\n\n"
            f"Партия: {batch['variety_name']}\n"
            f"Всего лотков: {batch['quantity']}\n"
            f"Продано: {sold_lots_count}\n"
            f"Доступно для списания: {len(lots)}\n\n"
            f"Непроданные лоты будут списаны как убытки!\n"
            f"Подтвердите:",
            reply_markup=get_batch_write_off_confirm(batch_id),
            parse_mode="Markdown"
        )
    except Exception as e:
        if "message is not modified" in str(e):
            # Если сообщение не изменилось, просто показываем уведомление
            await callback.answer("Для списания используйте кнопки ниже", show_alert=False)
        else:
            raise
    await callback.answer()


@router.callback_query(F.data.startswith("batch_write_off_confirm_"))
async def batch_write_off_confirm_handler(callback: CallbackQuery):
    """Подтверждение списания партии"""
    batch_id = int(callback.data.split("_")[-1])
    batch = await db.get_batch(batch_id)
    
    if not batch:
        await callback.answer("Партия не найдена", show_alert=True)
        return
    
    try:
        success = await db.write_off_batch(batch_id)
        if success:
            # Получаем количество списанных лотов
            all_lots = await db.get_all_lots()
            written_off_count = len([lot for lot in all_lots if lot['batch_id'] == batch_id and lot['status'] == 'written_off'])
            
            # Показываем уведомление о успешном списании
            await callback.answer(f"📋 Партия '{batch['variety_name']}' списана ({written_off_count} лот.)", show_alert=True)
            
            # Возвращаем к списку партий
            try:
                updated_batches = await db.get_all_batches()
                await callback.message.edit_text(
                    "🌱 *Мои партии*\n\n" + ("Нет активных партий" if not updated_batches else f"Активных партий: {len(updated_batches)}"),
                    reply_markup=get_batches_menu(updated_batches),
                    parse_mode="Markdown"
                )
            except Exception as e:
                if "message is not modified" in str(e):
                    # Если сообщение не изменилось, просто показываем уведомление
                    await callback.answer("Партия списана. Нажмите 'Назад' для возврата к списку", show_alert=False)
                else:
                    raise
        else:
            await callback.answer("❌ Не удалось списать партию", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data == "batches_archive")
async def batches_archive_handler(callback: CallbackQuery):
    """Показать архивные партии"""
    archived_batches = await db.get_archived_batches()
    
    if not archived_batches:
        await callback.message.edit_text(
            "📁 *Архив партий*\n\n"
            "В архиве нет партий.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="◀️ К активным партиям", callback_data="batches_list")],
                [types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
            ]),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            "📁 *Архив партий*\n\n"
            "Партии без доступных лотов:",
            reply_markup=get_archive_batches_menu(archived_batches),
            parse_mode="Markdown"
        )
    await callback.answer()
