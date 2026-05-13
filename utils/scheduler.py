import asyncio
import logging
from datetime import datetime
from typing import Optional

from aiogram import Bot, types
from database import Database
from config import CHECK_INTERVAL_MIN, STAGE_NAMES, STAGE_TRANSITIONS

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """Класс для фоновой проверки этапов партий и отправки уведомлений"""
    
    def __init__(self, db: Database, bot: Bot):
        self.db = db
        self.bot = bot
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Запускает бесконечный цикл проверки"""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("Notification scheduler started")
    
    async def stop(self):
        """Корректная остановка"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Notification scheduler stopped")
    
    async def _run_scheduler(self):
        """Основной цикл проверки"""
        while self._running:
            try:
                await self._check_and_notify()
                await asyncio.sleep(CHECK_INTERVAL_MIN * 60)  # Конвертируем минуты в секунды
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке
    
    async def _check_and_notify(self):
        """Проверка и отправка уведомлений о завершенных этапах"""
        try:
            # Получаем все активные партии
            batches = await self.db.get_all_batches()
            current_time = datetime.now()
            
            for batch in batches:
                if batch['current_stage'] == 'ready':
                    continue  # Пропускаем готовые партии
                
                # Проверяем, завершен ли текущий этап
                stage_started = datetime.fromisoformat(batch['stage_started_at'])
                hours_elapsed = (current_time - stage_started).total_seconds() / 3600
                
                # Получаем требуемое время для текущего этапа
                required_hours = self._get_stage_hours(batch, batch['current_stage'])
                
                if hours_elapsed >= required_hours and not batch['notified']:
                    await self._send_stage_notification(batch)
        
        except Exception as e:
            logger.error(f"Error checking and notifying: {e}")
    
    def _get_stage_hours(self, batch: dict, stage: str) -> int:
        """Получает требуемое количество часов для этапа"""
        variety = batch.get('variety_data', {})
        return {
            'soak': variety.get('soak_hours', 0),
            'dark': variety.get('dark_hours', 0),
            'light': variety.get('light_hours', 0)
        }.get(stage, 0)
    
    async def _send_stage_notification(self, batch: dict):
        """Отправляет уведомление о завершении этапа"""
        try:
            variety_name = batch.get('variety_name', 'Неизвестная культура')
            stage_name = STAGE_NAMES.get(batch['current_stage'], batch['current_stage'])
            next_stage = STAGE_TRANSITIONS.get(batch['current_stage'])
            next_stage_name = STAGE_NAMES.get(next_stage, next_stage) if next_stage else "Завершено"
            
            text = (
                f"🔔 *Уведомление о партии*\n\n"
                f"🌱 {variety_name}\n"
                f"📦 Партия #{batch['id']} ({batch['quantity']} лотков)\n"
                f"⏱️ Этап '{stage_name}' завершён!\n"
                f"➡️ Следующий этап: {next_stage_name}"
            )
            
            # Создаем inline-кнопки
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
            
            if next_stage:
                keyboard.inline_keyboard.append([
                    types.InlineKeyboardButton(
                        text=f"✅ {next_stage_name}",
                        callback_data=f"stage_next_{batch['id']}"
                    )
                ])
            
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(
                    text="⏰ Напомнить через 1ч",
                    callback_data=f"stage_remind_{batch['id']}"
                )
            ])
            
            # Отправляем уведомление админу
            await self.bot.send_message(
                chat_id=batch['created_by'],
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
            # Помечаем партию как уведомлённую
            await self.db.mark_batch_notified(batch['id'])
            
            logger.info(f"Stage notification sent for batch #{batch['id']}")
            
        except Exception as e:
            logger.error(f"Error sending notification for batch #{batch['id']}: {e}")


async def handle_stage_callback(callback: types.CallbackQuery, db: Database, bot: Bot):
    """Обрабатывает callback'и от уведомлений об этапах"""
    try:
        action_parts = callback.data.split("_")
        action = action_parts[1]  # 'next' или 'remind'
        batch_id = int(action_parts[2])  # ID партии
        
        # Получаем информацию о партии
        batch = await db.get_batch(batch_id)
        if not batch:
            await callback.answer("Партия не найдена", show_alert=True)
            return
        
        if action == "next":
            # Переводим партию на следующий этап
            current_stage = batch['current_stage']
            next_stage = STAGE_TRANSITIONS.get(current_stage)
            
            if not next_stage:
                await callback.answer("Партия уже на последнем этапе", show_alert=True)
                return
            
            # Обновляем партию
            await db.update_batch_stage(
                batch_id=batch_id,
                new_stage=next_stage
            )
            
            stage_name = STAGE_NAMES.get(next_stage, next_stage)
            
            await callback.message.edit_text(
                f"✅ Партия #{batch_id} переведена на этап '{stage_name}'",
                parse_mode="Markdown"
            )
            
            await callback.answer(f"Партия переведена на этап: {stage_name}")
            logger.info(f"Batch #{batch_id} moved to stage: {next_stage}")
            
        elif action == "remind":
            # Сбрасываем флаг notified, чтобы напомнить снова через час
            await db.mark_batch_notified(batch_id, notified=False)
            
            await callback.answer("Напоминание установлено через 1 час")
            logger.info(f"Reminder set for batch #{batch_id}")
        
    except Exception as e:
        logger.error(f"Error handling stage callback {callback.data}: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
