import aiosqlite
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "microgreen_bot.db"):
        self.db_path = db_path
        self.lock = asyncio.Lock()
    
    async def init(self):
        """Initialize database with all tables"""
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS varieties (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        seeds_per_lot REAL NOT NULL,
                        seed_cost_per_gram REAL NOT NULL,
                        base_cost REAL NOT NULL,
                        default_sale_price REAL NOT NULL,
                        soak_hours INTEGER NOT NULL DEFAULT 0,
                        dark_hours INTEGER NOT NULL,
                        light_hours INTEGER NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS batches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        variety_id INTEGER NOT NULL,
                        quantity INTEGER NOT NULL,
                        current_stage TEXT NOT NULL,
                        stage_started_at DATETIME NOT NULL,
                        notified BOOLEAN DEFAULT 0,
                        FOREIGN KEY (variety_id) REFERENCES varieties(id)
                    )
                ''')
                
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS lots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        batch_id INTEGER NOT NULL,
                        lot_code TEXT UNIQUE NOT NULL,
                        status TEXT NOT NULL DEFAULT 'growing',
                        snapshot_cost REAL NOT NULL,
                        sale_price REAL,
                        FOREIGN KEY (batch_id) REFERENCES batches(id)
                    )
                ''')
                
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        buyer_name TEXT NOT NULL,
                        total_amount REAL NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS order_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        lot_id INTEGER NOT NULL,
                        price_at_sale REAL NOT NULL,
                        FOREIGN KEY (order_id) REFERENCES orders(id),
                        FOREIGN KEY (lot_id) REFERENCES lots(id)
                    )
                ''')
                
                # Создание индексов для ускорения запросов
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_batches_stage_notified ON batches(current_stage, notified)
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_lots_batch_status ON lots(batch_id, status)
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at)
                ''')
                
                await db.execute('''
                    CREATE INDEX IF NOT EXISTS idx_varieties_name_active ON varieties(name, is_active)
                ''')
                
                await db.commit()
                logger.info("Database initialized successfully")
                logger.debug("Created DB indexes")
    
    async def reset_db(self):
        """Drop and recreate all tables"""
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DROP TABLE IF EXISTS order_items")
                await db.execute("DROP TABLE IF EXISTS orders")
                await db.execute("DROP TABLE IF EXISTS lots")
                await db.execute("DROP TABLE IF EXISTS batches")
                await db.execute("DROP TABLE IF EXISTS varieties")
                await db.commit()
        await self.init()
    
    # Varieties CRUD
    async def add_variety(self, name: str, seeds_per_lot: float, seed_cost_per_gram: float,
                          base_cost: float, default_sale_price: float, soak_hours: int,
                          dark_hours: int, light_hours: int) -> int:
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    INSERT INTO varieties (name, seeds_per_lot, seed_cost_per_gram, base_cost,
                                          default_sale_price, soak_hours, dark_hours, light_hours)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, seeds_per_lot, seed_cost_per_gram, base_cost,
                      default_sale_price, soak_hours, dark_hours, light_hours))
                await db.commit()
                return cursor.lastrowid
    
    async def get_variety(self, variety_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT * FROM varieties WHERE id = ? AND is_active = 1
            ''', (variety_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
    
    async def get_all_varieties(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT * FROM varieties WHERE is_active = 1 ORDER BY name
            ''') as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    
    async def update_variety(self, variety_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        
        # Логирование для отладки
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"update_variety called with kwargs: {kwargs}")
        
        set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [variety_id]
        
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(f'''
                    UPDATE varieties SET {set_clause} WHERE id = ?
                ''', values)
                await db.commit()
                return True
    
    async def soft_delete_variety(self, variety_id: int) -> bool:
        """Check if variety has active batches, then soft delete or hard delete"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check for active batches
            async with db.execute('''
                SELECT COUNT(*) FROM batches WHERE variety_id = ?
            ''', (variety_id,)) as cursor:
                active_batches = (await cursor.fetchone())[0]
                
            if active_batches > 0:
                # Soft delete
                async with self.lock:
                    async with aiosqlite.connect(self.db_path) as db:
                        await db.execute('''
                            UPDATE varieties SET is_active = 0 WHERE id = ?
                        ''', (variety_id,))
                        await db.commit()
                return True
            else:
                # Hard delete
                async with self.lock:
                    async with aiosqlite.connect(self.db_path) as db:
                        await db.execute('''
                            DELETE FROM varieties WHERE id = ?
                        ''', (variety_id,))
                        await db.commit()
                return True
    
    # Batches CRUD
    async def add_batch(self, variety_id: int, quantity: int) -> int:
        stage_started_at = datetime.now()
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    INSERT INTO batches (variety_id, quantity, current_stage, stage_started_at)
                    VALUES (?, ?, 'soak', ?)
                ''', (variety_id, quantity, stage_started_at))
                batch_id = cursor.lastrowid
                
                # Create lots for this batch
                variety = await self.get_variety(variety_id)
                if not variety:
                    raise ValueError("Variety not found")
                
                lot_cost = (variety['seeds_per_lot'] * variety['seed_cost_per_gram'] + 
                           variety['base_cost'])
                
                year = datetime.now().year
                
                # Нумерация лотов внутри каждой партии с 01
                for i in range(quantity):
                    lot_number = i + 1  # Начинаем с 1 для каждой партии
                    lot_code = f'MG-{year}-{batch_id:02d}-{lot_number:02d}'
                    await db.execute('''
                        INSERT INTO lots (batch_id, lot_code, snapshot_cost)
                        VALUES (?, ?, ?)
                    ''', (batch_id, lot_code, lot_cost))
                
                await db.commit()
                return batch_id
    
    async def get_batch(self, batch_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT b.*, v.name as variety_name, v.soak_hours, v.dark_hours, v.light_hours, v.default_sale_price
                FROM batches b
                JOIN varieties v ON b.variety_id = v.id
                WHERE b.id = ?
            ''', (batch_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
    
    async def get_ready_batches(self) -> List[Dict]:
        """Get batches that are ready for sale (current_stage = 'ready') AND have available lots"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT b.*, v.name as variety_name,
                       (SELECT COUNT(*) FROM lots WHERE batch_id = b.id AND status = 'growing') as available_lots
                FROM batches b
                JOIN varieties v ON b.variety_id = v.id
                WHERE b.current_stage = 'ready'
                AND b.id IN (
                    SELECT DISTINCT batch_id FROM lots 
                    WHERE status = 'growing' AND batch_id = b.id
                )
                ORDER BY b.stage_started_at
            ''') as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    
    async def get_all_batches(self) -> List[Dict]:
        """Get only batches with available lots (not sold or written off)"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT b.*, v.name as variety_name,
                       (SELECT COUNT(*) FROM lots WHERE batch_id = b.id) as total_lots,
                       (SELECT COUNT(*) FROM lots WHERE batch_id = b.id AND status = 'sold') as sold_lots,
                       (SELECT COUNT(*) FROM lots WHERE batch_id = b.id AND status = 'written_off') as written_off_lots
                FROM batches b
                JOIN varieties v ON b.variety_id = v.id
                WHERE b.id IN (
                    SELECT DISTINCT batch_id FROM lots 
                    WHERE status NOT IN ('sold', 'written_off')
                )
                ORDER BY b.stage_started_at DESC
            ''') as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    
    async def get_archived_batches(self) -> List[Dict]:
        """Get batches with no available lots (all sold or written off)"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT b.*, v.name as variety_name,
                       (SELECT COUNT(*) FROM lots WHERE batch_id = b.id) as total_lots,
                       (SELECT COUNT(*) FROM lots WHERE batch_id = b.id AND status = 'sold') as sold_lots,
                       (SELECT COUNT(*) FROM lots WHERE batch_id = b.id AND status = 'written_off') as written_off_lots
                FROM batches b
                JOIN varieties v ON b.variety_id = v.id
                WHERE b.id NOT IN (
                    SELECT DISTINCT batch_id FROM lots 
                    WHERE status NOT IN ('sold', 'written_off')
                )
                ORDER BY b.stage_started_at DESC
            ''') as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    
    async def update_batch_stage(self, batch_id: int, new_stage: str) -> bool:
        stage_started_at = datetime.now()
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    UPDATE batches SET current_stage = ?, stage_started_at = ?, notified = 0
                    WHERE id = ?
                ''', (new_stage, stage_started_at, batch_id))
                await db.commit()
                return True
    
    async def get_batches_ready_for_notification(self) -> List[Dict]:
        """Get batches that have completed their current stage but haven't been notified"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT b.*, v.name as variety_name, v.soak_hours, v.dark_hours, v.light_hours
                FROM batches b
                JOIN varieties v ON b.variety_id = v.id
                WHERE b.notified = 0
            ''') as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                batches = [dict(zip(columns, row)) for row in rows]
                
                ready_batches = []
                now = datetime.now()
                
                for batch in batches:
                    started = datetime.fromisoformat(batch['stage_started_at'])
                    elapsed_hours = (now - started).total_seconds() / 3600
                    
                    required_hours = 0
                    if batch['current_stage'] == 'soak':
                        required_hours = batch['soak_hours']
                    elif batch['current_stage'] == 'dark':
                        required_hours = batch['dark_hours']
                    elif batch['current_stage'] == 'light':
                        required_hours = batch['light_hours']
                    
                    if elapsed_hours >= required_hours and required_hours > 0:
                        ready_batches.append(batch)
                
                return ready_batches
    
    async def mark_batch_notified(self, batch_id: int) -> bool:
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    UPDATE batches SET notified = 1 WHERE id = ?
                ''', (batch_id,))
                await db.commit()
                return True
    
    # Lots CRUD
    async def get_available_lots(self, batch_id: int) -> List[Dict]:
        """Get lots that are available for sale (status = 'growing')"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT * FROM lots 
                WHERE batch_id = ? AND status = 'growing'
                ORDER BY lot_code
            ''', (batch_id,)) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    
    async def get_lot_by_id(self, lot_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT l.*, b.variety_id, v.name as variety_name
                FROM lots l
                JOIN batches b ON l.batch_id = b.id
                JOIN varieties v ON b.variety_id = v.id
                WHERE l.id = ?
            ''', (lot_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
    
    async def get_all_lots(self) -> List[Dict]:
        """Get all lots with variety information"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT l.*, b.variety_id, v.name as variety_name
                FROM lots l
                JOIN batches b ON l.batch_id = b.id
                JOIN varieties v ON b.variety_id = v.id
                ORDER BY l.id
            ''') as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    
    async def get_lot_by_code(self, lot_code: str) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT l.*, b.variety_id, v.name as variety_name
                FROM lots l
                JOIN batches b ON l.batch_id = b.id
                JOIN varieties v ON b.variety_id = v.id
                WHERE l.lot_code = ?
            ''', (lot_code,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
    
    async def update_lot_status(self, lot_id: int, status: str, sale_price: float = None) -> bool:
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                if sale_price is not None:
                    await db.execute('''
                        UPDATE lots SET status = ?, sale_price = ? WHERE id = ?
                    ''', (status, sale_price, lot_id))
                else:
                    await db.execute('''
                        UPDATE lots SET status = ? WHERE id = ?
                    ''', (status, lot_id))
                await db.commit()
                return True
    
    # Orders CRUD
    async def create_order(self, buyer_name: str, lot_ids: List[int], prices: List[float]) -> int:
        total_amount = sum(prices)
        
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    INSERT INTO orders (buyer_name, total_amount)
                    VALUES (?, ?)
                ''', (buyer_name, total_amount))
                order_id = cursor.lastrowid
                
                # Create order items and update lot status
                for lot_id, price in zip(lot_ids, prices):
                    await db.execute('''
                        INSERT INTO order_items (order_id, lot_id, price_at_sale)
                        VALUES (?, ?, ?)
                    ''', (order_id, lot_id, price))
                    
                    await db.execute('''
                        UPDATE lots SET status = 'sold', sale_price = ? WHERE id = ?
                    ''', (price, lot_id))
                
                await db.commit()
                return order_id
    
    async def get_order(self, order_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT o.*, COUNT(oi.id) as items_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.id = ?
                GROUP BY o.id
            ''', (order_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
    
    async def get_order_items(self, order_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT oi.*, l.lot_code, v.name as variety_name
                FROM order_items oi
                JOIN lots l ON oi.lot_id = l.id
                JOIN batches b ON l.batch_id = b.id
                JOIN varieties v ON b.variety_id = v.id
                WHERE oi.order_id = ?
                ORDER BY l.lot_code
            ''', (order_id,)) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    
    async def get_all_orders(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT o.*, COUNT(oi.id) as items_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                GROUP BY o.id
                ORDER BY o.created_at DESC
            ''') as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    
    async def write_off_batch(self, batch_id: int) -> bool:
        """Write off all unsold lots in a batch (mark as written_off)"""
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                try:
                    # Update all unsold lots to written_off status
                    await db.execute('''
                        UPDATE lots 
                        SET status = 'written_off' 
                        WHERE batch_id = ? AND status = 'growing'
                    ''', (batch_id,))
                    
                    # Check if all lots are now sold/written_off
                    async with db.execute('''
                        SELECT COUNT(*) FROM lots 
                        WHERE batch_id = ? AND status = 'growing'
                    ''', (batch_id,)) as cursor:
                        growing_count = (await cursor.fetchone())[0]
                    
                    # If no growing lots left, batch will automatically appear in archive
                    # No need to change stage - get_archived_batches handles this logic
                    
                    await db.commit()
                    return True
                except Exception as e:
                    await db.rollback()
                    raise e
    
    async def write_off_lot(self, lot_id: int) -> bool:
        """Write off a single lot (mark as written_off)"""
        async with self.lock:
            async with aiosqlite.connect(self.db_path) as db:
                try:
                    await db.execute('''
                        UPDATE lots 
                        SET status = 'written_off' 
                        WHERE id = ? AND status = 'growing'
                    ''', (lot_id,))
                    
                    await db.commit()
                    return True
                except Exception as e:
                    await db.rollback()
                    raise e
    
    # Statistics
    async def get_statistics(self) -> Dict:
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            
            # Total varieties
            async with db.execute('''
                SELECT COUNT(*) FROM varieties WHERE is_active = 1
            ''') as cursor:
                stats['total_varieties'] = (await cursor.fetchone())[0]
            
            # Active batches by stage
            async with db.execute('''
                SELECT current_stage, COUNT(*) FROM batches GROUP BY current_stage
            ''') as cursor:
                rows = await cursor.fetchall()
                stats['batches_by_stage'] = {row[0]: row[1] for row in rows}
            
            # Total lots and sold lots (excluding ready batches from growing)
            async with db.execute('''
                SELECT status, COUNT(*) FROM lots 
                WHERE status != 'growing' OR batch_id NOT IN (
                    SELECT id FROM batches WHERE current_stage = 'ready'
                )
                GROUP BY status
            ''') as cursor:
                rows = await cursor.fetchall()
                stats['lots_by_status'] = {row[0]: row[1] for row in rows}
            
            # Total revenue
            async with db.execute('''
                SELECT COALESCE(SUM(total_amount), 0) FROM orders
            ''') as cursor:
                stats['total_revenue'] = (await cursor.fetchone())[0]
            
            # Ready for sale
            async with db.execute('''
                SELECT COUNT(*) FROM lots WHERE status = 'growing' AND batch_id IN (
                    SELECT id FROM batches WHERE current_stage = 'ready'
                )
            ''') as cursor:
                stats['ready_for_sale'] = (await cursor.fetchone())[0]
            
            return stats
