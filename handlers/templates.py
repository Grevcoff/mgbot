from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from database import Database
from states.templates import TemplateForm
from keyboards.templates import templates_menu, template_actions, template_delete_confirm
from keyboards.main import back_keyboard
from utils.helpers import validate_number, format_hours
from config import MAX_SEEDS_PER_LOT, MIN_SEEDS_PER_LOT, MAX_PRICE, MIN_PRICE, MAX_HOURS

# Глобальная переменная для доступа к БД (устанавливается в main.py)
db = None

import asyncio
from functools import wraps

def retry_on_network_error(max_retries=3, delay=1):
    """Декоратор для retry при сетевых ошибках"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if "ClientConnectorError" in str(e) or "ServerDisconnectedError" in str(e):
                        if attempt < max_retries - 1:
                            await asyncio.sleep(delay * (attempt + 1))
                            continue
                        else:
                            raise e
                    else:
                        raise e
            return None
        return wrapper
    return decorator

router = Router()

@router.callback_query(F.data == "templates_list")
async def templates_list_handler(callback: CallbackQuery):
    """Показать список шаблонов культур"""
    varieties = await db.get_all_varieties()
    
    if not varieties:
        await callback.message.edit_text(
            "📦 *Шаблоны культур*\n\n"
            "Пока нет ни одного шаблона. Создайте первый!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить шаблон", callback_data="template_add")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
            ]),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            "📦 *Шаблоны культур*\n\n"
            "Выберите шаблон для управления:",
            reply_markup=templates_menu(varieties),
            parse_mode="Markdown"
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("template_edit_"))
async def template_view_handler(callback: CallbackQuery):
    """Просмотр деталей шаблона"""
    variety_id = int(callback.data.split("_")[-1])
    variety = await db.get_variety(variety_id)
    
    if not variety:
        await callback.answer("Шаблон не найден", show_alert=True)
        return
    
    total_hours = variety['soak_hours'] + variety['dark_hours'] + variety['light_hours']
    lot_cost = (variety['seeds_per_lot'] * variety['seed_cost_per_gram'] + variety['base_cost'])
    
    text = (
        f"🌱 *{variety['name']}*\n\n"
        f"📊 *Параметры:*\n"
        f"• Семян на лоток: {variety['seeds_per_lot']}г\n"
        f"• Цена семян: {variety['seed_cost_per_gram']}₽/г\n"
        f"• Базовая стоимость: {variety['base_cost']}₽\n"
        f"• Цена продажи: {variety['default_sale_price']}₽\n\n"
        f"⏱️ *Время цикла:*\n"
        f"• Замачивание: {variety['soak_hours']}ч\n"
        f"• Темнота: {variety['dark_hours']}ч\n"
        f"• Свет: {variety['light_hours']}ч\n"
        f"• **Итого:** {format_hours(total_hours)}\n\n"
        f"💰 *Себестоимость лотка:* {lot_cost:.2f}₽"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=template_actions(variety_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "template_add")
async def template_add_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания нового шаблона"""
    await state.set_state(TemplateForm.name)
    await state.update_data(editing_id=None, temp_data={})
    
    await callback.message.edit_text(
        "🌱 *Создание нового шаблона*\n\n"
        "Шаг 1/8: Введите название культуры:",
        reply_markup=back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("template_edit_data_"))
async def template_edit_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования шаблона"""
    variety_id = int(callback.data.split("_")[-1])
    variety = await db.get_variety(variety_id)
    
    if not variety:
        await callback.answer("Шаблон не найден", show_alert=True)
        return
    
    await state.set_state(TemplateForm.name)
    await state.update_data(
        editing_id=variety_id,
        temp_data={
            'name': variety['name'],
            'seeds_per_lot': variety['seeds_per_lot'],
            'seed_cost': variety['seed_cost_per_gram'],
            'base_cost': variety['base_cost'],
            'default_price': variety['default_sale_price'],
            'soak_hours': variety['soak_hours'],
            'dark_hours': variety['dark_hours'],
            'light_hours': variety['light_hours']
        }
    )
    
    await callback.message.edit_text(
        f"✏️ *Редактирование шаблона*\n\n"
        f"Текущее название: {variety['name']}\n\n"
        f"Введите новое название или отправьте текущее без изменений:",
        reply_markup=back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(TemplateForm.name)
async def template_name_handler(message: Message, state: FSMContext):
    """Обработка названия культуры"""
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer(
            "❌ Название должно содержать минимум 2 символа. Попробуйте снова:",
            reply_markup=back_keyboard()
        )
        return
    
    data = await state.get_data()
    temp_data = data.get('temp_data', {})
    temp_data['name'] = name
    await state.update_data(temp_data=temp_data)
    
    await state.set_state(TemplateForm.seeds_per_lot)
    
    current_value = temp_data.get('seeds_per_lot', 0)
    await message.answer(
        f"🌱 *Создание шаблона*\n\n"
        f"Шаг 2/8: Сколько грамм семян нужно на один лоток?\n"
        f"Текущее значение: {current_value}г",
        reply_markup=back_keyboard(),
        parse_mode="Markdown"
    )

@router.message(TemplateForm.seeds_per_lot)
async def template_seeds_handler(message: Message, state: FSMContext):
    """Обработка количества семян"""
    value = validate_number(message.text, MIN_SEEDS_PER_LOT, MAX_SEEDS_PER_LOT)
    
    if value is None:
        await message.answer(
            f"❌ Введите число от {MIN_SEEDS_PER_LOT} до {MAX_SEEDS_PER_LOT}. Попробуйте снова:",
            reply_markup=back_keyboard()
        )
        return
    
    data = await state.get_data()
    temp_data = data.get('temp_data', {})
    temp_data['seeds_per_lot'] = value
    await state.update_data(temp_data=temp_data)
    
    await state.set_state(TemplateForm.seed_cost)
    
    current_value = temp_data.get('seed_cost', 0)
    await message.answer(
        f"🌱 *Создание шаблона*\n\n"
        f"Шаг 3/8: Цена семян за грамм (₽)?\n"
        f"Текущее значение: {current_value}₽",
        reply_markup=back_keyboard(),
        parse_mode="Markdown"
    )

@router.message(TemplateForm.seed_cost)
async def template_seed_cost_handler(message: Message, state: FSMContext):
    """Обработка цены семян"""
    value = validate_number(message.text, MIN_PRICE, MAX_PRICE)
    
    if value is None:
        await message.answer(
            f"❌ Введите число от {MIN_PRICE} до {MAX_PRICE}. Попробуйте снова:",
            reply_markup=back_keyboard()
        )
        return
    
    data = await state.get_data()
    temp_data = data.get('temp_data', {})
    temp_data['seed_cost'] = value
    await state.update_data(temp_data=temp_data)
    
    await state.set_state(TemplateForm.base_cost)
    
    current_value = temp_data.get('base_cost', 0)
    await message.answer(
        f"🌱 *Создание шаблона*\n\n"
        f"Шаг 4/8: Базовая стоимость лотка (контейнер + субстрат, ₽)?\n"
        f"Текущее значение: {current_value}₽",
        reply_markup=back_keyboard(),
        parse_mode="Markdown"
    )

@router.message(TemplateForm.base_cost)
async def template_base_cost_handler(message: Message, state: FSMContext):
    """Обработка базовой стоимости"""
    value = validate_number(message.text, MIN_PRICE, MAX_PRICE)
    
    if value is None:
        await message.answer(
            f"❌ Введите число от {MIN_PRICE} до {MAX_PRICE}. Попробуйте снова:",
            reply_markup=back_keyboard()
        )
        return
    
    data = await state.get_data()
    temp_data = data.get('temp_data', {})
    temp_data['base_cost'] = value
    await state.update_data(temp_data=temp_data)
    
    await state.set_state(TemplateForm.default_price)
    
    current_value = temp_data.get('default_price', 0)
    await message.answer(
        f"🌱 *Создание шаблона*\n\n"
        f"Шаг 5/8: Цена продажи по умолчанию (₽)?\n"
        f"Текущее значение: {current_value}₽",
        reply_markup=back_keyboard(),
        parse_mode="Markdown"
    )

@router.message(TemplateForm.default_price)
async def template_default_price_handler(message: Message, state: FSMContext):
    """Обработка цены продажи"""
    value = validate_number(message.text, MIN_PRICE, MAX_PRICE)
    
    if value is None:
        await message.answer(
            f"❌ Введите число от {MIN_PRICE} до {MAX_PRICE}. Попробуйте снова:",
            reply_markup=back_keyboard()
        )
        return
    
    data = await state.get_data()
    temp_data = data.get('temp_data', {})
    temp_data['default_price'] = value
    await state.update_data(temp_data=temp_data)
    
    await state.set_state(TemplateForm.soak_hours)
    
    current_value = temp_data.get('soak_hours', 0)
    await message.answer(
        f"🌱 *Создание шаблона*\n\n"
        f"Шаг 6/8: Часы замачивания (0 если не нужно)?\n"
        f"Текущее значение: {current_value}ч",
        reply_markup=back_keyboard(),
        parse_mode="Markdown"
    )

@router.message(TemplateForm.soak_hours)
async def template_soak_hours_handler(message: Message, state: FSMContext):
    """Обработка часов замачивания"""
    value = validate_number(message.text, 0, MAX_HOURS, is_int=True)
    
    if value is None:
        await message.answer(
            f"❌ Введите целое число от 0 до {MAX_HOURS}. Попробуйте снова:",
            reply_markup=back_keyboard()
        )
        return
    
    data = await state.get_data()
    temp_data = data.get('temp_data', {})
    temp_data['soak_hours'] = int(value)
    await state.update_data(temp_data=temp_data)
    
    await state.set_state(TemplateForm.dark_hours)
    
    current_value = temp_data.get('dark_hours', 0)
    await message.answer(
        f"🌱 *Создание шаблона*\n\n"
        f"Шаг 7/8: Часы в темноте?\n"
        f"Текущее значение: {current_value}ч",
        reply_markup=back_keyboard(),
        parse_mode="Markdown"
    )

@router.message(TemplateForm.dark_hours)
async def template_dark_hours_handler(message: Message, state: FSMContext):
    """Обработка часов в темноте"""
    value = validate_number(message.text, 0, MAX_HOURS, is_int=True)
    
    if value is None:
        await message.answer(
            f"❌ Введите целое число от 0 до {MAX_HOURS}. Попробуйте снова:",
            reply_markup=back_keyboard()
        )
        return
    
    data = await state.get_data()
    temp_data = data.get('temp_data', {})
    temp_data['dark_hours'] = int(value)
    await state.update_data(temp_data=temp_data)
    
    await state.set_state(TemplateForm.light_hours)
    
    current_value = temp_data.get('light_hours', 0)
    lot_cost = (temp_data['seeds_per_lot'] * temp_data['seed_cost'] + temp_data['base_cost'])
    total_hours = temp_data['soak_hours'] + temp_data['dark_hours'] + current_value
    
    await message.answer(
        f"🌱 *Создание шаблона*\n\n"
        f"Шаг 8/8: Часы на свету?\n"
        f"Текущее значение: {current_value}ч\n\n"
        f"💡 *Предварительный расчёт:*\n"
        f"• Итого цикл: {format_hours(total_hours)}\n"
        f"• Себестоимость лотка: {lot_cost:.2f}₽",
        reply_markup=back_keyboard(),
        parse_mode="Markdown"
    )

@router.message(TemplateForm.light_hours)
async def template_light_hours_handler(message: Message, state: FSMContext):
    """Обработка часов на свету и сохранение шаблона"""
    value = validate_number(message.text, 0, MAX_HOURS, is_int=True)
    
    if value is None:
        await message.answer(
            f"❌ Введите целое число от 0 до {MAX_HOURS}. Попробуйте снова:",
            reply_markup=back_keyboard()
        )
        return
    
    data = await state.get_data()
    temp_data = data.get('temp_data', {})
    temp_data['light_hours'] = int(value)
    
    editing_id = data.get('editing_id')
    
    # Расчёт итоговых показателей
    lot_cost = (temp_data['seeds_per_lot'] * temp_data['seed_cost'] + temp_data['base_cost'])
    total_hours = temp_data['soak_hours'] + temp_data['dark_hours'] + temp_data['light_hours']
    
    try:
        if editing_id:
            # Обновление существующего шаблона с retry
            await retry_on_network_error()(db.update_variety)(
                editing_id,
                name=temp_data['name'],
                seeds_per_lot=temp_data['seeds_per_lot'],
                seed_cost_per_gram=temp_data['seed_cost'],
                base_cost=temp_data['base_cost'],
                default_sale_price=temp_data['default_price'],
                soak_hours=temp_data['soak_hours'],
                dark_hours=temp_data['dark_hours'],
                light_hours=temp_data['light_hours']
            )
            action = "обновлён"
        else:
            # Создание нового шаблона с retry
            await retry_on_network_error()(db.add_variety)(
                temp_data['name'],
                temp_data['seeds_per_lot'],
                temp_data['seed_cost'],
                temp_data['base_cost'],
                temp_data['default_price'],
                temp_data['soak_hours'],
                temp_data['dark_hours'],
                temp_data['light_hours']
            )
            action = "создан"
        
        await state.clear()
        
        await message.answer(
            f"✅ Шаблон '{temp_data['name']}' успешно {action}!\n\n"
            f"📊 *Параметры:*\n"
            f"• Итого цикл: {format_hours(total_hours)}\n"
            f"• Себестоимость лотка: {lot_cost:.2f}₽\n"
            f"• Цена продажи: {temp_data['default_price']}₽",
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        
        # Показать обновлённый список шаблонов
        varieties = await db.get_all_varieties()
        await message.answer(
            "📦 *Шаблоны культур*\n\nВыберите шаблон для управления:",
            reply_markup=templates_menu(varieties),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        if "ClientConnectorError" in str(e) or "ServerDisconnectedError" in str(e):
            await message.answer(
                "❌ Проблемы с соединением при сохранении шаблона.\n\n"
                "Попробуйте ещё раз через несколько секунд.",
                reply_markup=back_keyboard()
            )
        else:
            await message.answer(
                f"❌ Ошибка при сохранении шаблона: {str(e)}",
                reply_markup=back_keyboard()
            )

@router.callback_query(F.data.startswith("template_delete_"))
async def template_delete_handler(callback: CallbackQuery):
    """Начало удаления шаблона"""
    variety_id = int(callback.data.split("_")[-1])
    variety = await db.get_variety(variety_id)
    
    if not variety:
        await callback.answer("Шаблон не найден", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"🗑️ *Удаление шаблона*\n\n"
        f"Вы уверены, что хотите удалить '{variety['name']}'?\n"
        f"Если есть активные партии, шаблон будет помечен как неактивный.",
        reply_markup=template_delete_confirm(variety_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("template_delete_confirm_"))
async def template_delete_confirm_handler(callback: CallbackQuery):
    """Подтверждение удаления шаблона"""
    variety_id = int(callback.data.split("_")[-1])
    variety = await db.get_variety(variety_id)
    
    if not variety:
        await callback.answer("Шаблон не найден", show_alert=True)
        return
    
    success = await db.soft_delete_variety(variety_id)
    
    if success:
        await callback.message.edit_text(
            f"✅ Шаблон '{variety['name']}' удалён",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="templates_list")]
            ])
        )
    else:
        await callback.answer("Ошибка при удалении", show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data == "cancel", StateFilter(TemplateForm))
@router.callback_query(F.data == "back", StateFilter(TemplateForm))
async def template_cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Отмена создания/редактирования шаблона"""
    await state.clear()
    
    varieties = await db.get_all_varieties()
    
    if not varieties:
        await callback.message.edit_text(
            "📦 *Шаблоны культур*\n\n"
            "Пока нет ни одного шаблона. Создайте первый!",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="➕ Добавить шаблон", callback_data="template_add")],
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
            ]),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            "📦 *Шаблоны культур*\n\nВыберите шаблон для управления:",
            reply_markup=templates_menu(varieties),
            parse_mode="Markdown"
        )
    
    await callback.answer()
