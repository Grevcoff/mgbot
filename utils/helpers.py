import re
from datetime import datetime, timedelta
from typing import Optional, Union

def validate_number(text: str, min_val: float, max_val: float, is_int: bool = False) -> Optional[Union[int, float]]:
    """Валидация числового значения"""
    try:
        # Удаляем все символы кроме цифр, точки и запятой
        cleaned = re.sub(r'[^\d.,]', '', text.replace(',', '.'))
        
        if not cleaned:
            return None
        
        if is_int:
            value = int(float(cleaned))
        else:
            value = float(cleaned)
        
        if min_val <= value <= max_val:
            return value
        return None
    except (ValueError, TypeError):
        return None

def format_hours(hours: int) -> str:
    """Форматирование часов в читаемый формат"""
    if hours < 24:
        return f"{hours}ч"
    
    days = hours // 24
    remaining_hours = hours % 24
    
    if remaining_hours == 0:
        return f"{days}д"
    else:
        return f"{days}д {remaining_hours}ч"

def format_datetime(dt: datetime) -> str:
    """Форматирование даты и времени"""
    return dt.strftime("%d.%m.%Y %H:%M")

def format_duration(start: datetime, end: datetime = None) -> str:
    """Форматирование продолжительности"""
    if end is None:
        end = datetime.now()
    
    duration = end - start
    total_hours = int(duration.total_seconds() / 3600)
    
    return format_hours(total_hours)

def format_price(price: float) -> str:
    """Форматирование цены"""
    return f"{price:.2f}₽"

def parse_lot_code(lot_code: str) -> Optional[tuple]:
    """Парсинг кода лотка MG-YYYY-BB-LL"""
    match = re.match(r'MG-(\d{4})-(\d{2})-(\d{2})', lot_code.upper())
    if match:
        year = int(match.group(1))
        batch_id = int(match.group(2))
        lot_number = int(match.group(3))
        return year, batch_id, lot_number
    return None

def generate_lot_code(year: int, batch_id: int, lot_number: int) -> str:
    """Генерация кода лотка с форматом MG-YYYY-BB-LL"""
    return f"MG-{year}-{batch_id:02d}-{lot_number:02d}"

def calculate_lot_cost(seeds_per_lot: float, seed_cost_per_gram: float, base_cost: float) -> float:
    """Расчёт себестоимости лотка"""
    return seeds_per_lot * seed_cost_per_gram + base_cost

def calculate_profit(sale_price: float, lot_cost: float) -> float:
    """Расчёт прибыли"""
    return sale_price - lot_cost

def calculate_profit_margin(sale_price: float, lot_cost: float) -> float:
    """Расчёт маржинальности в процентах"""
    if sale_price == 0:
        return 0
    return ((sale_price - lot_cost) / sale_price) * 100

def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезка текста с добавлением многоточия"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def safe_int(value: any, default: int = 0) -> int:
    """Безопасное преобразование в int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value: any, default: float = 0.0) -> float:
    """Безопасное преобразование во float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
