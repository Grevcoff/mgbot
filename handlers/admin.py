import csv
import os
from datetime import datetime
from typing import List, Dict, Any

from aiogram import Router, F, types
from aiogram.types import FSInputFile, CallbackQuery
from database import Database
from config import ADMIN_ID, RESET_CONFIRM_CODE

router = Router()

# Глобальная переменная для доступа к БД (устанавливается в main.py)
db = None


@router.callback_query(F.data == "admin_export")
async def admin_export_handler(callback: CallbackQuery):
    """Обработчик кнопки Экспорт данных"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    try:
        # Получаем статистику для показа
        orders = await db.get_all_orders()
        lots = await db.get_all_lots()
        varieties = await db.get_all_varieties()
        
        # Базовая статистика
        total_orders = len(orders)
        total_lots = len(lots)
        total_varieties = len(varieties)
        
        # Считаем проданные лоты и выручку
        sold_lots = [lot for lot in lots if lot['status'] == 'sold']
        total_sold = len(sold_lots)
        total_revenue = sum(lot['sale_price'] for lot in sold_lots if lot['sale_price'])
        
        # Считаем списанные лоты
        written_off_lots = [lot for lot in lots if lot['status'] == 'written_off']
        total_written_off = len(written_off_lots)
        
        # Считаем растущие лоты
        growing_lots = [lot for lot in lots if lot['status'] == 'growing']
        total_growing = len(growing_lots)
        
        # Создаем CSV файл
        csv_content = []
        csv_content.append(['Тип данных', 'Количество', 'Дополнительная информация'])
        csv_content.append(['Всего заказов', total_orders, ''])
        csv_content.append(['Всего лотков', total_lots, f'Продано: {total_sold}, Растёт: {total_growing}, Списано: {total_written_off}'])
        csv_content.append(['Всего культур', total_varieties, ''])
        csv_content.append(['Общая выручка', f'{total_revenue}₽', f'По {len(sold_lots)} проданным лоткам'])
        csv_content.append(['Списано лотков', total_written_off, f'Убытки по списанным лоткам'])
        
        # Создаем файл
        from datetime import datetime
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            import csv
            writer = csv.writer(file)
            writer.writerows(csv_content)
        
        # Отправляем файл
        await callback.message.answer_document(
            document=FSInputFile(filename),
            caption=f"📊 *Экспорт данных*\n\n"
                   f"📈 Всего заказов: {total_orders}\n"
                   f"🌱 Всего лотков: {total_lots}\n"
                   f"💰 Общая выручка: {total_revenue}₽\n"
                   f"📦 Всего культур: {total_varieties}",
            parse_mode="Markdown"
        )
        
        # Удаляем временный файл
        import os
        os.remove(filename)
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при экспорте: {str(e)}")
    
    await callback.answer()


@router.callback_query(F.data == "admin_reset_db")
async def admin_reset_db_handler(callback: CallbackQuery):
    """Обработчик кнопки Сбросить БД"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚠️ *Сброс базы данных*\n\n"
        "Это действие удалит все данные!\n\n"
        "Для подтверждения введите код подтверждения:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(F.text & F.from_user.id == ADMIN_ID)
async def admin_reset_code_handler(message: types.Message):
    """Обработка кода подтверждения сброса БД"""
    if message.text.strip() == RESET_CONFIRM_CODE:
        try:
            await db.reset_db()
            await message.answer(
                "✅ База данных успешно сброшена",
                reply_markup=types.ReplyKeyboardMarkup(
                    keyboard=[
                        [types.KeyboardButton(text="📊 Статистика")],
                        [types.KeyboardButton(text="🌱 Мои партии"), types.KeyboardButton(text="➕ Новая партия")],
                        [types.KeyboardButton(text="🛒 Продажа лотков"), types.KeyboardButton(text="📦 Шаблоны культур")],
                        [types.KeyboardButton(text="⚙️ Настройки")]
                    ],
                    resize_keyboard=True
                )
            )
        except Exception as e:
            await message.answer(f"❌ Ошибка при сбросе БД: {str(e)}")
    # Не отвечаем на другие сообщения, чтобы не конфликтовать с другими обработчиками



@router.message(F.text == "/export")
async def export_handler(message: types.Message):
    """Экспорт данных в CSV только для админа"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        # Получаем статистику для показа
        orders = await db.get_all_orders()
        lots = await db.get_all_lots()
        varieties = await db.get_all_varieties()
        
        # Базовая статистика
        total_orders = len(orders)
        total_lots = len(lots)
        total_varieties = len(varieties)
        
        # Финансовые показатели
        sold_lots = [lot for lot in lots if lot['status'] == 'sold']
        written_off_lots = [lot for lot in lots if lot['status'] == 'written_off']
        
        total_revenue = sum(order['total_amount'] for order in orders)
        total_cost_sold = sum(lot['snapshot_cost'] for lot in sold_lots if lot['snapshot_cost'])
        profits = [(lot['sale_price'] - lot['snapshot_cost']) 
                  for lot in sold_lots 
                  if lot['sale_price'] and lot['snapshot_cost']]
        total_profit = sum(profits)
        total_losses = sum(lot['snapshot_cost'] for lot in written_off_lots if lot['snapshot_cost'])
        
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Показываем расширенную статистику
        stats_text = (
            f"📤 *Экспорт данных*\n\n"
            f"📊 *Общая статистика:*\n"
            f"🌱 Культур: {total_varieties}\n"
            f"📦 Партий: {len(set(lot['batch_id'] for lot in lots))}\n"
            f"💰 Заказов: {total_orders}\n\n"
            f"📈 *Финансовые показатели:*\n"
            f"💵 Общая выручка: {total_revenue:.2f}₽\n"
            f"💸 Общие убытки: {total_losses:.2f}₽\n"
            f"📊 Общая прибыль: {total_profit:.2f}₽\n"
            f"📈 Маржа: {profit_margin:.1f}%\n"
            f"🧾 Средний чек: {avg_order_value:.2f}₽\n\n"
            f"📋 *Статус лотов:*\n"
            f"✅ Продано: {len(sold_lots)}\n"
            f"❌ Списано: {len(written_off_lots)}\n"
            f"🌱 В выращивании: {len([lot for lot in lots if lot['status'] == 'growing'])}\n\n"
            f"📁 *Данные успешно собраны.*"
        )
        
        await message.answer(stats_text, parse_mode="Markdown")
        
        # Создаем директорию для экспорта
        os.makedirs("exports", exist_ok=True)
        
        # Генерируем имя файла с датой
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Экспорт лотов
        lots_file = f"exports/lots_export_{date_str}.csv"
        await export_lots(lots_file)
        
        # Экспорт заказов
        orders_file = f"exports/orders_export_{date_str}.csv"
        await export_orders(orders_file)
        
        # Экспорт сводки
        summary_file = f"exports/summary_export_{date_str}.csv"
        await export_summary(summary_file)
        
        # Отправляем файлы с обработкой ошибок
        try:
            await message.answer_document(
                FSInputFile(lots_file),
                caption="📊 Экспорт лотов"
            )
        except Exception as e:
            if "message is not modified" in str(e):
                pass  # Игнорируем ошибку если содержимое не изменилось
            else:
                raise
        
        try:
            await message.answer_document(
                FSInputFile(orders_file),
                caption="📋 Экспорт заказов"
            )
        except Exception as e:
            if "message is not modified" in str(e):
                pass  # Игнорируем ошибку если содержимое не изменилось
            else:
                raise
        
        try:
            await message.answer_document(
                FSInputFile(summary_file),
                caption="📈 Сводка по продажам"
            )
        except Exception as e:
            if "message is not modified" in str(e):
                pass  # Игнорируем ошибку если содержимое не изменилось
            else:
                raise
        
        await message.answer("✅ Экспорт завершен успешно!")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при экспорте: {str(e)}")


async def export_lots(filename: str):
    """Экспорт всех лотов в CSV"""
    lots = await db.get_all_lots()
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['code', 'variety', 'status', 'cost', 'sale_price', 'profit']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for lot in lots:
            profit = 0.0
            if lot['sale_price']:
                profit = lot['sale_price'] - lot['snapshot_cost']
            
            writer.writerow({
                'code': lot['lot_code'],
                'variety': lot.get('variety_name', ''),
                'status': lot['status'],
                'cost': lot['snapshot_cost'],
                'sale_price': lot['sale_price'] or 0.0,
                'profit': profit
            })


async def export_orders(filename: str):
    """Экспорт всех заказов в CSV"""
    orders = await db.get_all_orders()
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['id', 'buyer_name', 'total_amount', 'created_at', 'items_count']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for order in orders:
            items = await db.get_order_items(order['id'])
            writer.writerow({
                'id': order['id'],
                'buyer_name': order['buyer_name'],
                'total_amount': order['total_amount'],
                'created_at': order['created_at'],
                'items_count': len(items)
            })


async def export_summary(filename: str):
    """Расширенный экспорт сводки по продажам с бизнес-метриками"""
    orders = await db.get_all_orders()
    lots = await db.get_all_lots()
    
    # Базовая статистика
    total_orders = len(orders)
    total_lots = len(lots)
    
    # Статистика по лотам
    sold_lots = [lot for lot in lots if lot['status'] == 'sold']
    written_off_lots = [lot for lot in lots if lot['status'] == 'written_off']
    growing_lots = [lot for lot in lots if lot['status'] == 'growing']
    
    sold_count = len(sold_lots)
    written_off_count = len(written_off_lots)
    growing_count = len(growing_lots)
    
    # Финансовые показатели
    total_revenue = sum(order['total_amount'] for order in orders)
    
    # Себестоимость проданных лотов
    total_cost_sold = sum(lot['snapshot_cost'] for lot in sold_lots if lot['snapshot_cost'])
    
    # Прибыль от продаж
    profits = [(lot['sale_price'] - lot['snapshot_cost']) 
              for lot in sold_lots 
              if lot['sale_price'] and lot['snapshot_cost']]
    total_profit = sum(profits)
    
    # Убытки от списаний
    losses = [lot['snapshot_cost'] for lot in written_off_lots if lot['snapshot_cost']]
    total_losses = sum(losses)
    
    # Маржа (%)
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    # Средний чек
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # ROI (возврат инвестиций)
    total_investment = sum(lot['snapshot_cost'] for lot in lots if lot['snapshot_cost'])
    roi = ((total_revenue - total_investment) / total_investment * 100) if total_investment > 0 else 0
    
    # Процент списаний
    written_off_percent = (written_off_count / total_lots * 100) if total_lots > 0 else 0
    
    # Топ культур по продажам
    variety_stats = {}
    for lot in sold_lots:
        if lot['sale_price']:
            variety = lot.get('variety_name', 'Неизвестно')
            revenue = lot['sale_price']
            variety_stats[variety] = variety_stats.get(variety, 0) + revenue
    
    top_varieties = sorted(variety_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Топ культур по прибыли
    variety_profit_stats = {}
    for lot in sold_lots:
        if lot['sale_price'] and lot['snapshot_cost']:
            variety = lot.get('variety_name', 'Неизвестно')
            profit = lot['sale_price'] - lot['snapshot_cost']
            variety_profit_stats[variety] = variety_profit_stats.get(variety, 0) + profit
    
    top_profit_varieties = sorted(variety_profit_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['metric', 'value', 'unit']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Общие показатели
        writer.writerow({'metric': 'Всего заказов', 'value': total_orders, 'unit': 'шт'})
        writer.writerow({'metric': 'Всего лотов', 'value': total_lots, 'unit': 'шт'})
        writer.writerow({'metric': 'Продано лотов', 'value': sold_count, 'unit': 'шт'})
        writer.writerow({'metric': 'Списано лотов', 'value': written_off_count, 'unit': 'шт'})
        writer.writerow({'metric': 'В выращивании', 'value': growing_count, 'unit': 'шт'})
        
        # Финансовые показатели
        writer.writerow({'metric': 'Общая выручка', 'value': f"{total_revenue:.2f}", 'unit': '₽'})
        writer.writerow({'metric': 'Себестоимость проданных', 'value': f"{total_cost_sold:.2f}", 'unit': '₽'})
        writer.writerow({'metric': 'Общая прибыль', 'value': f"{total_profit:.2f}", 'unit': '₽'})
        writer.writerow({'metric': 'Общие убытки', 'value': f"{total_losses:.2f}", 'unit': '₽'})
        writer.writerow({'metric': 'Чистая прибыль', 'value': f"{total_profit - total_losses:.2f}", 'unit': '₽'})
        writer.writerow({'metric': 'Маржа', 'value': f"{profit_margin:.2f}", 'unit': '%'})
        writer.writerow({'metric': 'ROI', 'value': f"{roi:.2f}", 'unit': '%'})
        writer.writerow({'metric': 'Средний чек', 'value': f"{avg_order_value:.2f}", 'unit': '₽'})
        writer.writerow({'metric': 'Процент списаний', 'value': f"{written_off_percent:.2f}", 'unit': '%'})
        
        # Топ культур по выручке
        writer.writerow({'metric': 'ТОП-5 культур по выручке', 'value': '', 'unit': ''})
        for i, (variety, revenue) in enumerate(top_varieties, 1):
            writer.writerow({'metric': f'Топ-{i}: {variety}', 'value': f"{revenue:.2f}", 'unit': '₽'})
        
        # Топ культур по прибыли
        writer.writerow({'metric': 'ТОП-5 культур по прибыли', 'value': '', 'unit': ''})
        for i, (variety, profit) in enumerate(top_profit_varieties, 1):
            writer.writerow({'metric': f'Топ-{i}: {variety}', 'value': f"{profit:.2f}", 'unit': '₽'})
        
        # Эффективность по статусам
        writer.writerow({'metric': 'ЭФФЕКТИВНОСТЬ ПО СТАТУСАМ', 'value': '', 'unit': ''})
        success_rate = (sold_count / total_lots * 100) if total_lots > 0 else 0
        writer.writerow({'metric': 'Успешность продаж', 'value': f"{success_rate:.2f}", 'unit': '%'})
        
        # Средняя прибыль на проданный лот
        avg_profit_per_lot = (total_profit / sold_count) if sold_count > 0 else 0
        writer.writerow({'metric': 'Средняя прибыль на лот', 'value': f"{avg_profit_per_lot:.2f}", 'unit': '₽'})
        
        # Средняя себестоимость лота
        avg_cost_per_lot = (total_cost_sold / sold_count) if sold_count > 0 else 0
        writer.writerow({'metric': 'Средняя себестоимость лота', 'value': f"{avg_cost_per_lot:.2f}", 'unit': '₽'})
        
        # Средняя цена продажи лота
        avg_sale_price = (total_revenue / sold_count) if sold_count > 0 else 0
        writer.writerow({'metric': 'Средняя цена продажи лота', 'value': f"{avg_sale_price:.2f}", 'unit': '₽'})
