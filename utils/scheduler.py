import asyncio
import logging
from datetime import datetime
from typing import List

from database import Database
from keyboards.batches import stage_transition_notification
from config import CHECK_INTERVAL_MIN, ADMIN_ID, STAGE_TRANSITIONS, STAGE_NAMES

logger = logging.getLogger(__name__)

class NotificationScheduler:
    def __init__(self, db: Database, bot):
        self.db = db
        self.bot = bot
        self.running = False
        self.task = None
    
    async def start(self):
        """Запуск планировщика"""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        logger.info("Notification scheduler started")
    
    async def stop(self):
        """Остановка планировщика"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Notification scheduler stopped")
    
    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                await self._check_stages()
                await asyncio.sleep(CHECK_INTERVAL_MIN * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке
    
    async def _check_stages(self):
        """Проверка завершённых этапов"""
        try:
            ready_batches = await self.db.get_batches_ready_for_notification()
            
            for batch in ready_batches:
                await self._send_stage_notification(batch)
                await self.db.mark_batch_notified(batch['id'])
                
        except Exception as e:
            logger.error(f"Error checking stages: {e}")
    
    async def _send_stage_notification(self, batch: dict):
        """Отправка уведомления о завершении этапа"""
        try:
            current_stage = batch['current_stage']
            next_stage = STAGE_TRANSITIONS.get(current_stage)
            
            if not next_stage:
                return  # Финальный этап
            
            stage_name = STAGE_NAMES.get(current_stage, current_stage)
            next_stage_name = STAGE_NAMES.get(next_stage, next_stage)
            
            # Рассчитываем длительность этапа
            started_at = datetime.fromisoformat(batch['stage_started_at'])
            duration = datetime.now() - started_at
            hours = int(duration.total_seconds() / 3600)
            
            text = (
                f"⏰ *Этап завершён!*\n\n"
                f"🌱 *{batch['variety_name']}*\n"
                f"📦 Партия #{batch['id']} ({batch['quantity']} лотков)\n\n"
                f"✅ Этап \"{stage_name}\" завершён за {hours}ч\n"
                f"➡️ Готов к переходу на \"{next_stage_name}\"\n\n"
                f"Нажмите кнопку для перевода на следующий этап:"
            )
            
            keyboard = stage_transition_notification(batch['id'], next_stage)
            
            # Отправляем уведомление админу
            await self.bot.send_message(
                chat_id=ADMIN_ID,
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
            logger.info(f"Sent stage notification for batch {batch['id']}")
            
        except Exception as e:
            logger.error(f"Error sending notification for batch {batch['id']}: {e}")
    
    async def send_manual_reminder(self, batch_id: int):
        """Отправка ручного напоминания через час"""
        try:
            batch = await self.db.get_batch(batch_id)
            if not batch:
                return
            
            # Сбрасываем флаг уведомления, чтобы напомнить через час
            await self.db.update_batch_stage(batch_id, batch['current_stage'])
            
            await self.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"⏰ Напоминание для партии #{batch_id} установлено на 1 час",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error setting manual reminder for batch {batch_id}: {e}")

# Глобальная функция для обработки callback'ов от уведомлений
async def handle_stage_callback(callback_query, db: Database, bot):
    """Обработка кнопок из уведомлений о завершении этапа"""
    try:
        data = callback_query.data
        
        if data.startswith("stage_next_"):
            batch_id = int(data.split("_")[-1])
            batch = await db.get_batch(batch_id)
            
            if not batch:
                await callback_query.answer("Партия не найдена", show_alert=True)
                return
            
            current_stage = batch['current_stage']
            next_stage = STAGE_TRANSITIONS.get(current_stage)
            
            if not next_stage:
                await callback_query.answer("Партия уже на финальном этапе", show_alert=True)
                return
            
            # Обновляем этап
            success = await db.update_batch_stage(batch_id, next_stage)
            
            if success:
                stage_name = STAGE_NAMES.get(next_stage, next_stage)
                
                await callback_query.message.edit_text(
                    f"✅ Партия #{batch_id} переведена на этап: {stage_name}\n\n"
                    f"🌱 {batch['variety_name']}",
                    parse_mode="Markdown"
                )
                
                await callback_query.answer(f"Переведено на этап: {stage_name}")
                
            else:
                await callback_query.answer("Ошибка при обновлении этапа", show_alert=True)
        
        elif data.startswith("stage_remind_"):
            batch_id = int(data.split("_")[-1])
            
            # Создаём планировщик для напоминания
            scheduler = NotificationScheduler(db, bot)
            await scheduler.send_manual_reminder(batch_id)
            
            await callback_query.answer("Напомню через час")
            
    except Exception as e:
        logger.error(f"Error handling stage callback: {e}")
        await callback_query.answer("Произошла ошибка", show_alert=True)
