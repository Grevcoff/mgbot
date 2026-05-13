from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import Database
from states.sell import SellProcess
from keyboards.sell import get_ready_batches, get_lot_selection_buttons, get_cart_actions, get_price_keyboard
from keyboards.main import main_menu
from utils.helpers import format_price, validate_number
from config import MAX_PRICE, MIN_PRICE

# Глобальная переменная для доступа к БД (устанавливается в main.py)
db = None

router = Router()

@router.callback_query(F.data == "sell_start")
async def sell_start_handler(callback: CallbackQuery, state: FSMContext):
    """Начало процесса продажи"""
    # Очищаем предыдущие данные
    await state.update_data(cart=[], temp_price=0.0, current_batch_id=None, selected_lots=[])
    
    # Получаем партии готовые к продаже
    ready_batches = await db.get_ready_batches()
    
    if not ready_batches:
        await callback.message.edit_text(
            "🛒 *Продажа лотков*\n\n"
            "Нет партий готовых к продаже!",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
            ]),
            parse_mode="Markdown"
        )
        return
    
    await state.set_state(SellProcess.choosing_batch)
    
    await callback.message.edit_text(
        "🛒 *Продажа лотков*\n\n"
        "Выберите партию для продажи:",
        reply_markup=get_ready_batches(ready_batches),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("sell_batch_"))
async def sell_batch_handler(callback: CallbackQuery, state: FSMContext):
    """Выбор партии для продажи"""
    batch_id = int(callback.data.split("_")[-1])
    
    # Получаем доступные лоты партии
    available_lots = await db.get_available_lots(batch_id)
    
    if not available_lots:
        await callback.answer("Нет доступных лотков в этой партии", show_alert=True)
        return
    
    await state.update_data(
        current_batch_id=batch_id,
        selected_lots=[]
    )
    await state.set_state(SellProcess.choosing_lots)
    
    await callback.message.edit_text(
        "🛒 *Выбор лотков*\n\n"
        "Выберите лотки для продажи (нажмите на номера):",
        reply_markup=get_lot_selection_buttons(available_lots, []),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("sell_lot_"))
async def sell_lot_handler(callback: CallbackQuery, state: FSMContext):
    """Выбор/отмена выбора лота"""
    lot_id = int(callback.data.split("_")[-1])
    data = await state.get_data()
    selected_lots = data.get('selected_lots', [])
    current_batch_id = data.get('current_batch_id')
    
    # Переключаем выбор лота
    if lot_id in selected_lots:
        selected_lots.remove(lot_id)
    else:
        selected_lots.append(lot_id)
    
    await state.update_data(selected_lots=selected_lots)
    
    # Обновляем клавиатуру
    available_lots = await db.get_available_lots(current_batch_id)
    await callback.message.edit_reply_markup(
        reply_markup=get_lot_selection_buttons(available_lots, selected_lots)
    )
    await callback.answer()

@router.callback_query(F.data == "sell_add_to_cart")
async def sell_add_to_cart_handler(callback: CallbackQuery, state: FSMContext):
    """Добавление выбранных лотов в корзину"""
    data = await state.get_data()
    selected_lots = data.get('selected_lots', [])
    cart = data.get('cart', [])
    
    if not selected_lots:
        await callback.answer("Выберите хотя бы один лоток", show_alert=True)
        return
    
    # Показываем выбор цены
    await state.set_state(SellProcess.viewing_cart)
    
    await callback.message.edit_text(
        f"🛒 *Цена продажи*\n\n"
        f"Выбрано лотков: {len(selected_lots)}\n\n"
        f"Установите цену для выбранных лотков:",
        reply_markup=get_price_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "price_default")
async def price_default_handler(callback: CallbackQuery, state: FSMContext):
    """Использование стандартной цены"""
    data = await state.get_data()
    selected_lots = data.get('selected_lots', [])
    current_batch_id = data.get('current_batch_id')
    
    # Получаем информацию о партии для стандартной цены
    batch = await db.get_batch(current_batch_id)
    if not batch:
        await callback.answer("Ошибка получения данных партии", show_alert=True)
        return
    
    # Добавляем лоты в корзину со стандартной ценой
    cart = data.get('cart', [])
    cart.extend(selected_lots)
    
    await state.update_data(
        cart=cart,
        temp_price=batch['default_sale_price'],
        selected_lots=[]
    )
    
    # Показываем корзину
    await show_cart(callback.message, state, db)
    await callback.answer()

@router.callback_query(F.data == "price_custom")
async def price_custom_handler(callback: CallbackQuery, state: FSMContext):
    """Запрос пользовательской цены"""
    await callback.message.edit_text(
        "💰 *Введите цену продажи*\n\n"
        f"Укажите цену за один лоток ({MIN_PRICE}-{MAX_PRICE} ₽):",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Отмена", callback_data="sell_cancel_price")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(SellProcess.viewing_cart, F.text)
async def custom_price_handler(message: Message, state: FSMContext):
    """Обработка пользовательской цены"""
    price = validate_number(message.text, MIN_PRICE, MAX_PRICE)
    
    if price is None:
        await message.answer(
            f"❌ Введите число от {MIN_PRICE} до {MAX_PRICE}. Попробуйте снова:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="◀️ Отмена", callback_data="sell_cancel_price")]
            ])
        )
        return
    
    data = await state.get_data()
    selected_lots = data.get('selected_lots', [])
    cart = data.get('cart', [])
    
    # Добавляем лоты в корзину с пользовательской ценой
    cart.extend(selected_lots)
    
    await state.update_data(
        cart=cart,
        temp_price=price,
        selected_lots=[]
    )
    
    # Показываем корзину
    await show_cart(message, state, db)

async def show_cart(message: types.Message | CallbackQuery, state: FSMContext, db: Database):
    """Показ корзины"""
    data = await state.get_data()
    cart = data.get('cart', [])
    
    if not cart:
        text = "🛒 *Корзина пуста*\n\nДобавьте лотки для продажи."
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Добавить лотки", callback_data="sell_add_more")],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ])
    else:
        # Получаем информацию о лотках в корзине
        cart_items = []
        total_amount = 0.0
        
        for lot_id in cart:
            lot = await db.get_lot_by_id(lot_id)  # Получаем по ID
            if lot:
                sale_price = lot.get('sale_price')
                if sale_price is not None:
                    total_amount += float(sale_price)
                else:
                    total_amount += data.get('temp_price', 0.0)
            else:
                # Если лот не найден, используем стандартную цену
                total_amount += data.get('temp_price', 0.0)
        
        text = (
            f"🛒 *Корзина*\n\n"
            f"📦 Лотков в корзине: {len(cart)}\n"
            f"💰 Общая сумма: {format_price(total_amount)}"
        )
        
        keyboard = get_cart_actions()
    
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "sell_add_more")
async def sell_add_more_handler(callback: CallbackQuery, state: FSMContext):
    """Добавление ещё лотков в корзину"""
    ready_batches = await db.get_ready_batches()
    
    await state.set_state(SellProcess.choosing_batch)
    
    await callback.message.edit_text(
        "🛒 *Добавление лотков*\n\n"
        "Выберите партию:",
        reply_markup=get_ready_batches(ready_batches),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "sell_clear_cart")
async def sell_clear_cart_handler(callback: CallbackQuery, state: FSMContext):
    """Очистка корзины"""
    await state.update_data(cart=[], temp_price=0.0)
    
    await callback.message.edit_text(
        "🛒 *Корзина очищена*\n\n",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Добавить лотки", callback_data="sell_start")],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "sell_checkout")
async def sell_checkout_handler(callback: CallbackQuery, state: FSMContext):
    """Начало оформления заказа"""
    data = await state.get_data()
    cart = data.get('cart', [])
    
    if not cart:
        await callback.answer("Корзина пуста", show_alert=True)
        return
    
    await state.set_state(SellProcess.entering_buyer)
    
    await callback.message.edit_text(
        "💰 *Оформление заказа*\n\n"
        f"Лотков в заказе: {len(cart)}\n\n"
        "Введите имя покупателя:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Отмена", callback_data="sell_cancel_checkout")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(SellProcess.entering_buyer, F.text)
async def sell_buyer_handler(message: Message, state: FSMContext):
    """Обработка имени покупателя и создание заказа"""
    buyer_name = message.text.strip()
    
    if len(buyer_name) < 2:
        await message.answer(
            "❌ Имя должно содержать минимум 2 символа. Попробуйте снова:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="◀️ Отмена", callback_data="sell_cancel_checkout")]
            ])
        )
        return
    
    data = await state.get_data()
    cart = data.get('cart', [])
    temp_price = data.get('temp_price', 0.0)
    
    try:
        # Создаём заказ
        prices = [temp_price] * len(cart)
        order_id = await db.create_order(buyer_name, cart, prices)
        
        # Получаем информацию о заказе
        order = await db.get_order(order_id)
        
        await state.clear()
        
        await message.answer(
            f"✅ *Заказ оформлен!*\n\n"
            f"📋 *Номер заказа:* #{order_id}\n"
            f"👤 *Покупатель:* {buyer_name}\n"
            f"📦 *Лотков:* {len(cart)}\n"
            f"💰 *Сумма:* {format_price(order['total_amount'])}\n\n"
            f"Лотки отмечены как проданные.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ]),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при оформлении заказа: {str(e)}",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="◀️ Назад", callback_data="sell_view_cart")]
            ])
        )

@router.callback_query(F.data == "sell_cancel_price")
async def sell_cancel_price_handler(callback: CallbackQuery, state: FSMContext):
    """Отмена ввода цены"""
    data = await state.get_data()
    selected_lots = data.get('selected_lots', [])
    current_batch_id = data.get('current_batch_id')
    
    # Возвращаемся к выбору лотов
    await state.set_state(SellProcess.choosing_lots)
    
    available_lots = await db.get_available_lots(current_batch_id)
    await callback.message.edit_text(
        "🛒 *Выбор лотков*\n\n"
        "Выберите лотки для продажи (нажмите на номера):",
        reply_markup=get_lot_selection_buttons(available_lots, selected_lots),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "sell_cancel_checkout")
async def sell_cancel_checkout_handler(callback: CallbackQuery, state: FSMContext):
    """Отмена оформления заказа"""
    await show_cart(callback, state, db)
    await callback.answer()

@router.callback_query(F.data == "sell_view_cart")
async def sell_view_cart_handler(callback: CallbackQuery, state: FSMContext):
    """Просмотр корзины"""
    await show_cart(callback, state, db)
    await callback.answer()

@router.callback_query(F.data == "cancel", StateFilter(SellProcess))
async def sell_cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Отмена процесса продажи"""
    await state.clear()
    
    await callback.message.edit_text(
        "🛒 *Продажа отменена*\n\n",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()
