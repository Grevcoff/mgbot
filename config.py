import os
from typing import List

# Токен Telegram бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in environment variables")

# ID администратора бота
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
if not ADMIN_ID or ADMIN_ID == 0:
    raise ValueError("ADMIN_ID not set in environment variables")

# Database settings
DB_PATH = "microgreen_bot.db"

# Scheduler settings
CHECK_INTERVAL_MIN = 15  # Check timers every 15 minutes

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "bot.log"

# Bot settings
BOT_NAME = "MicroGreen Bot"
BOT_DESCRIPTION = "Бот для учёта микрозелени"

# Stage names in Russian
STAGE_NAMES = {
    "soak": "Замачивание",
    "dark": "Темнота", 
    "light": "Свет",
    "ready": "Готово к продаже"
}

# Stage transitions
STAGE_TRANSITIONS = {
    "soak": "dark",
    "dark": "light", 
    "light": "ready",
    "ready": None
}

# Time formatting
TIME_FORMAT = "%d.%m.%Y %H:%M"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Pagination
ITEMS_PER_PAGE = 8

# Validation
MAX_BATCH_QUANTITY = 100
MIN_SEEDS_PER_LOT = 0.1
MAX_SEEDS_PER_LOT = 100.0
MIN_PRICE = 0.01
MAX_PRICE = 10000.0
MAX_HOURS = 1000

# Security
RESET_CONFIRM_CODE = os.getenv("RESET_CONFIRM_CODE", "123456")
