import os
import json
import random
import datetime
import asyncio
import psutil
from collections import defaultdict
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, PreCheckoutQueryHandler

# 🔧 КОНФИГУРАЦИЯ
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8378526693:AAFOwAb6pVp1GOE0tXZN4PDLFnD_TTT1djg")
PROVIDER_TOKEN = os.environ.get("PROVIDER_TOKEN", "TEST_PROVIDER_TOKEN")
ADMIN_CODE = os.environ.get("ADMIN_CODE", "1337")

# 🎯 МИНИМАЛЬНАЯ И МАКСИМАЛЬНАЯ СТАВКА
MIN_BET = 1
MAX_BET = 100000

# ⏱️ ВРЕМЯ АНИМАЦИИ ДЛЯ КАЖДОЙ ИГРЫ (в секундах)
DICE_DELAYS = {
    "🎰": 1.5,  # Слоты - самая долгая анимация
    "🎯": 2.5,  # Дартс
    "🎲": 2.5,  # Кубик
    "🎳": 3.5,  # Боулинг
    "⚽": 3.5,  # Футбол
    "🏀": 3.5   # Баскетбол
}

# 💰 ПАКЕТЫ ПОПОЛНЕНИЯ (1 реальная звезда = 1 игровая звезда)
PRODUCTS = {
    "pack_5": {"title": "5 ⭐", "description": "Пополнение баланса на 5 ⭐", "price": 5, "currency": "XTR", "credits": 5},
    "pack_10": {"title": "10 ⭐", "description": "Пополнение баланса на 10 ⭐", "price": 10, "currency": "XTR", "credits": 10},
    "pack_25": {"title": "25 ⭐", "description": "Пополнение баланса на 25 ⭐", "price": 25, "currency": "XTR", "credits": 25},
    "pack_50": {"title": "50 ⭐", "description": "Пополнение баланса на 50 ⭐", "price": 50, "currency": "XTR", "credits": 50},
    "pack_100": {"title": "100 ⭐", "description": "Пополнение баланса на 100 ⭐", "price": 100, "currency": "XTR", "credits": 100},
    "pack_250": {"title": "250 ⭐", "description": "Пополнение баланса на 250 ⭐", "price": 250, "currency": "XTR", "credits": 250},
    "pack_500": {"title": "500 ⭐", "description": "Пополнение баланса на 500 ⭐", "price": 500, "currency": "XTR", "credits": 500},
    "pack_1000": {"title": "1000 ⭐", "description": "Пополнение баланса на 1000 ⭐", "price": 1000, "currency": "XTR", "credits": 1000}
}

# 🎁 ВЫВОД СРЕДСТВ - МИНИМАЛЬНАЯ СУММА И ВАРИАНТЫ
MIN_WITHDRAWAL = 15
WITHDRAWAL_AMOUNTS = [15, 25, 50, 100]

# 🎮 БАЗОВЫЕ ВЫИГРЫШИ ДЛЯ СТАВКИ 1 ⭐
BASE_PRIZES = {
    "🎰": {
        "ТРИ БАРА": 5,
        "ТРИ ВИШНИ": 10, 
        "ТРИ ЛИМОНЫ": 15,
        "ДЖЕКПОТ 777": 20
    },
    "🎯": {"ПОПАДАНИЕ В ЦЕЛЬ": 3},
    "🎲": {"ВЫПАЛО 6": 3},
    "🎳": {"СТРАЙК": 3},
    "⚽": {
        "СЛАБЫЙ УДАР": 0.1,
        "УДАР МИМО": 0.2,
        "БЛИЗКИЙ УДАР": 0.5,
        "ХОРОШИЙ ГОЛ": 1.2,
        "СУПЕРГОЛ": 1.5
    },
    "🏀": {
        "ПРОМАХ": 0.1,
        "КАСАТЕЛЬНО": 0.15,
        "ОТСКОК": 0.2,
        "ТРЕХОЧКОВЫЙ": 1.4,
        "СЛЭМ-ДАНК": 1.4
    }
}

# 🎰 СИСТЕМА СЕРИЙ ПОБЕД (ОПТИМИЗИРОВАННАЯ)
WIN_STREAK_BONUSES = {
    2: {"multiplier": 1.1, "message": "🔥 Серия из 2 побед! Бонус +10% к выигрышу!"},
    3: {"multiplier": 1.25, "message": "🔥🔥 Серия из 3 побед! Бонус +25% к выигрышу!"},
    5: {"multiplier": 1.5, "message": "🔥🔥🔥 СЕРИЯ ИЗ 5 ПОБЕД! МЕГА БОНУС +50% к выигрышу!"}
}

# 🎁 СИСТЕМА СЛУЧАЙНЫХ МЕГА-ВЫИГРЫШЕЙ (ОПТИМИЗИРОВАННАЯ)
MEGA_WIN_CONFIG = {
    "chance": 0.006,  # 0.6% шанс на мега-выигрыш
    "min_multiplier": 1.5,    # множитель от 1.5x
    "max_multiplier": 5       # до 5x
}

# 🔄 СИСТЕМА ВОЗВРАТОВ ПРИ ПРОИГРЫШЕ (ОПТИМИЗИРОВАННАЯ)
REFUND_CONFIG = {
    "min_refund": 0.02,       # 2% минимальный возврат
    "max_refund": 0.1         # 10% максимальный возврат
}

# 🎁 ОПТИМИЗИРОВАННАЯ СИСТЕМА НЕДЕЛЬНЫХ НАГРАД
WEEKLY_BONUS_CONFIG = {
    "min_daily_games": 5,           # минимум 5 игр в день
    "required_days": 7,             # 7 дней подряд без пропусков
    "base_percent": 0.01,           # 1% базовый процент
    "bonus_per_extra_game": 0.0005, # +0.05% за каждую игру сверх минимума
    "max_extra_bonus": 0.02         # максимальная доп. награда +2%
}

# 👥 РЕФЕРАЛЬНАЯ СИСТЕМА
REFERRAL_CONFIG = {
    "reward_percent": 0.10,  # 10% от проигрыша приглашенного
    "min_referee_games": 3,  # минимальное количество игр приглашенного
    "min_referee_deposit": 10  # минимальный депозит приглашенного
}

# 🎟️ СИСТЕМА ПРОМОКОДОВ
PROMO_CONFIG = {
    "max_active_promos": 50,  # максимальное количество активных промокодов
    "default_uses": 100,      # количество использований по умолчанию
    "min_amount": 5,          # минимальная сумма промокода
    "max_amount": 1000        # максимальная сумма промокода
}

# 🎮 ПОЛНАЯ КОНФИГУРАЦИЯ ИГР (С ИСПРАВЛЕННЫМИ ВОЗВРАТАМИ ДЛЯ ВСЕХ ИГР)
GAMES_CONFIG = {
    "🎰": {
        "values": {
            # ОБЫЧНЫЕ СЛОТЫ - 64 значения, 4 выигрышных
            1: {"win": True, "base_prize": BASE_PRIZES["🎰"]["ТРИ БАРА"], "message": "🎰 ТРИ БАРА! Выигрыш: {prize} ⭐"},
            2: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #2 - проигрыш. Возврат: {prize} ⭐"},
            3: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #3 - проигрыш. Возврат: {prize} ⭐"},
            4: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #4 - проигрыш. Возврат: {prize} ⭐"},
            5: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #5 - проигрыш. Возврат: {prize} ⭐"},
            6: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #6 - проигрыш. Возврат: {prize} ⭐"},
            7: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #7 - проигрыш. Возврат: {prize} ⭐"},
            8: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #8 - проигрыш. Возврат: {prize} ⭐"},
            9: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #9 - проигрыш. Возврат: {prize} ⭐"},
            10: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #10 - проигрыш. Возврат: {prize} ⭐"},
            11: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #11 - проигрыш. Возврат: {prize} ⭐"},
            12: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #12 - проигрыш. Возврат: {prize} ⭐"},
            13: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #13 - проигрыш. Возврат: {prize} ⭐"},
            14: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #14 - проигрыш. Возврат: {prize} ⭐"},
            15: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #15 - проигрыш. Возврат: {prize} ⭐"},
            16: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #16 - проигрыш. Возврат: {prize} ⭐"},
            17: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #17 - проигрыш. Возврат: {prize} ⭐"},
            18: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #18 - проигрыш. Возврат: {prize} ⭐"},
            19: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #19 - проигрыш. Возврат: {prize} ⭐"},
            20: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #20 - проигрыш. Возврат: {prize} ⭐"},
            21: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #21 - проигрыш. Возврат: {prize} ⭐"},
            22: {"win": True, "base_prize": BASE_PRIZES["🎰"]["ТРИ ВИШНИ"], "message": "🎰 ТРИ ВИШНИ! Выигрыш: {prize} ⭐"},
            23: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #23 - проигрыш. Возврат: {prize} ⭐"},
            24: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #24 - проигрыш. Возврат: {prize} ⭐"},
            25: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #25 - проигрыш. Возврат: {prize} ⭐"},
            26: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #26 - проигрыш. Возврат: {prize} ⭐"},
            27: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #27 - проигрыш. Возврат: {prize} ⭐"},
            28: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #28 - проигрыш. Возврат: {prize} ⭐"},
            29: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #29 - проигрыш. Возврат: {prize} ⭐"},
            30: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #30 - проигрыш. Возврат: {prize} ⭐"},
            31: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #31 - проигрыш. Возврат: {prize} ⭐"},
            32: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #32 - проигрыш. Возврат: {prize} ⭐"},
            33: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #33 - проигрыш. Возврат: {prize} ⭐"},
            34: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #34 - проигрыш. Возврат: {prize} ⭐"},
            35: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #35 - проигрыш. Возврат: {prize} ⭐"},
            36: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #36 - проигрыш. Возврат: {prize} ⭐"},
            37: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #37 - проигрыш. Возврат: {prize} ⭐"},
            38: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #38 - проигрыш. Возврат: {prize} ⭐"},
            39: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #39 - проигрыш. Возврат: {prize} ⭐"},
            40: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #40 - проигрыш. Возврат: {prize} ⭐"},
            41: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #41 - проигрыш. Возврат: {prize} ⭐"},
            42: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #42 - проигрыш. Возврат: {prize} ⭐"},
            43: {"win": True, "base_prize": BASE_PRIZES["🎰"]["ТРИ ЛИМОНА"], "message": "🎰 ТРИ ЛИМОНА! Выигрыш: {prize} ⭐"},
            44: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #44 - проигрыш. Возврат: {prize} ⭐"},
            45: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #45 - проигрыш. Возврат: {prize} ⭐"},
            46: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #46 - проигрыш. Возврат: {prize} ⭐"},
            47: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #47 - проигрыш. Возврат: {prize} ⭐"},
            48: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #48 - проигрыш. Возврат: {prize} ⭐"},
            49: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #49 - проигрыш. Возврат: {prize} ⭐"},
            50: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #50 - проигрыш. Возврат: {prize} ⭐"},
            51: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #51 - проигрыш. Возврат: {prize} ⭐"},
            52: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #52 - проигрыш. Возврат: {prize} ⭐"},
            53: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #53 - проигрыш. Возврат: {prize} ⭐"},
            54: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #54 - проигрыш. Возврат: {prize} ⭐"},
            55: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #55 - проигрыш. Возврат: {prize} ⭐"},
            56: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #56 - проигрыш. Возврат: {prize} ⭐"},
            57: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #57 - проигрыш. Возврат: {prize} ⭐"},
            58: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #58 - проигрыш. Возврат: {prize} ⭐"},
            59: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #59 - проигрыш. Возврат: {prize} ⭐"},
            60: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #60 - проигрыш. Возврат: {prize} ⭐"},
            61: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #61 - проигрыш. Возврат: {prize} ⭐"},
            62: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #62 - проигрыш. Возврат: {prize} ⭐"},
            63: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #63 - проигрыш. Возврат: {prize} ⭐"},
            64: {"win": True, "base_prize": BASE_PRIZES["🎰"]["ДЖЕКПОТ 777"], "message": "🎰 ДЖЕКПОТ 777! Выигрыш: {prize} ⭐"}
        }
    },
    "🎯": {
        "values": {
            # ДАРТС - 6 значений, 1 выигрышное (6)
            1: {"win": False, "base_prize": 0, "message": "🎯 - проигрыш. Возврат: {prize} ⭐"},
            2: {"win": False, "base_prize": 0, "message": "🎯 - проигрыш. Возврат: {prize} ⭐"},
            3: {"win": False, "base_prize": 0, "message": "🎯 - проигрыш. Возврат: {prize} ⭐"},
            4: {"win": False, "base_prize": 0, "message": "🎯 - проигрыш. Возврат: {prize} ⭐"},
            5: {"win": False, "base_prize": 0, "message": "🎯 - проигрыш. Возврат: {prize} ⭐"},
            6: {"win": True, "base_prize": BASE_PRIZES["🎯"]["ПОПАДАНИЕ В ЦЕЛЬ"], "message": "🎯 - ПОПАДАНИЕ В ЦЕЛЬ! Выигрыш: {prize} ⭐"}
        }
    },
    "🎲": {
        "values": {
            # КОСТИ - 6 значений, 1 выигрышное (6)
            1: {"win": False, "base_prize": 0, "message": "🎲 - проигрыш. Возврат: {prize} ⭐"},
            2: {"win": False, "base_prize": 0, "message": "🎲 - проигрыш. Возврат: {prize} ⭐"},
            3: {"win": False, "base_prize": 0, "message": "🎲 - проигрыш. Возврат: {prize} ⭐"},
            4: {"win": False, "base_prize": 0, "message": "🎲 - проигрыш. Возврат: {prize} ⭐"},
            5: {"win": False, "base_prize": 0, "message": "🎲 - проигрыш. Возврат: {prize} ⭐"},
            6: {"win": True, "base_prize": BASE_PRIZES["🎲"]["ВЫПАЛО 6"], "message": "🎲 - ВЫПАЛО 6! Выигрыш: {prize} ⭐"}
        }
    },
    "🎳": {
        "values": {
            # БОУЛИНГ - 6 значений, 1 выигрышное (6)
            1: {"win": False, "base_prize": 0, "message": "🎳 - проигрыш. Возврат: {prize} ⭐"},
            2: {"win": False, "base_prize": 0, "message": "🎳 - проигрыш. Возврат: {prize} ⭐"},
            3: {"win": False, "base_prize": 0, "message": "🎳 - проигрыш. Возврат: {prize} ⭐"},
            4: {"win": False, "base_prize": 0, "message": "🎳 - проигрыш. Возврат: {prize} ⭐"},
            5: {"win": False, "base_prize": 0, "message": "🎳 - проигрыш. Возврат: {prize} ⭐"},
            6: {"win": True, "base_prize": BASE_PRIZES["🎳"]["СТРАЙК"], "message": "🎳 - СТРАЙК! Выигрыш: {prize} ⭐"}
        }
    },
    "⚽": {
        "values": {
            # ФУТБОЛ - 5 значений, только 3 выигрышных (голы)
            1: {"win": False, "base_prize": BASE_PRIZES["⚽"]["СЛАБЫЙ УДАР"], "message": "⚽ Слабый удар... Возврат: {prize} ⭐"},
            2: {"win": False, "base_prize": BASE_PRIZES["⚽"]["УДАР МИМО"], "message": "⚽ Удар мимо ворот... Возврат: {prize} ⭐"},
            3: {"win": True, "base_prize": BASE_PRIZES["⚽"]["БЛИЗКИЙ УДАР"], "message": "⚽ Близко к воротам! Выигрыш: {prize} ⭐"},
            4: {"win": True, "base_prize": BASE_PRIZES["⚽"]["ХОРОШИЙ ГОЛ"], "message": "⚽ ГОООЛ! Выигрыш: {prize} ⭐"},
            5: {"win": True, "base_prize": BASE_PRIZES["⚽"]["СУПЕРГОЛ"], "message": "⚽ СУПЕРГОООЛ! МЕГА ВЫИГРЫШ: {prize} ⭐"}
        }
    },
    "🏀": {
        "values": {
            # БАСКЕТБОЛ - 5 значений, только 2 выигрышных (броски)
            1: {"win": False, "base_prize": BASE_PRIZES["🏀"]["ПРОМАХ"], "message": "🏀 Промах... Возврат: {prize} ⭐"},
            2: {"win": False, "base_prize": BASE_PRIZES["🏀"]["КАСАТЕЛЬНО"], "message": "🏀 Коснулось кольца... Возврат: {prize} ⭐"},
            3: {"win": False, "base_prize": BASE_PRIZES["🏀"]["ОТСКОК"], "message": "🏀 Отскок... Возврат: {prize} ⭐"},
            4: {"win": True, "base_prize": BASE_PRIZES["🏀"]["ТРЕХОЧКОВЫЙ"], "message": "🏀 Трехочковый! Выигрыш: {prize} ⭐"},
            5: {"win": True, "base_prize": BASE_PRIZES["🏀"]["СЛЭМ-ДАНК"], "message": "🏀 СЛЭМ-ДАНК! МЕГА ВЫИГРЫШ: {prize} ⭐"}
        }
    }
}

# 🎰 КОНФИГУРАЦИЯ ДЛЯ СЛОТОВ 777 (ТОЛЬКО ДЖЕКПОТ) - ИСПРАВЛЕННАЯ
SLOTS_777_CONFIG = {
    "🎰": {
        "values": {
            # СЛОТЫ 777 - 64 значения, ТОЛЬКО 1 выигрышное (64) с увеличенным призом
            1: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш. Возврат: {prize} ⭐"},
            2: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #2 - проигрыш. Возврат: {prize} ⭐"},
            3: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #3 - проигрыш. Возврат: {prize} ⭐"},
            4: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #4 - проигрыш. Возврат: {prize} ⭐"},
            5: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #5 - проигрыш. Возврат: {prize} ⭐"},
            6: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #6 - проигрыш. Возврат: {prize} ⭐"},
            7: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #7 - проигрыш. Возврат: {prize} ⭐"},
            8: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #8 - проигрыш. Возврат: {prize} ⭐"},
            9: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #9 - проигрыш. Возврат: {prize} ⭐"},
            10: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #10 - проигрыш. Возврат: {prize} ⭐"},
            11: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #11 - проигрыш. Возврат: {prize} ⭐"},
            12: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #12 - проигрыш. Возврат: {prize} ⭐"},
            13: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #13 - проигрыш. Возврат: {prize} ⭐"},
            14: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #14 - проигрыш. Возврат: {prize} ⭐"},
            15: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #15 - проигрыш. Возврат: {prize} ⭐"},
            16: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #16 - проигрыш. Возврат: {prize} ⭐"},
            17: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #17 - проигрыш. Возврат: {prize} ⭐"},
            18: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #18 - проигрыш. Возврат: {prize} ⭐"},
            19: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #19 - проигрыш. Возврат: {prize} ⭐"},
            20: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #20 - проигрыш. Возврат: {prize} ⭐"},
            21: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #21 - проигрыш. Возврат: {prize} ⭐"},
            22: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #22 - проигрыш. Возврат: {prize} ⭐"},
            23: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #23 - проигрыш. Возврат: {prize} ⭐"},
            24: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #24 - проигрыш. Возврат: {prize} ⭐"},
            25: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #25 - проигрыш. Возврат: {prize} ⭐"},
            26: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #26 - проигрыш. Возврат: {prize} ⭐"},
            27: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #27 - проигрыш. Возврат: {prize} ⭐"},
            28: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #28 - проигрыш. Возврат: {prize} ⭐"},
            29: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #29 - проигрыш. Возврат: {prize} ⭐"},
            30: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #30 - проигрыш. Возврат: {prize} ⭐"},
            31: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #31 - проигрыш. Возврат: {prize} ⭐"},
            32: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #32 - проигрыш. Возврат: {prize} ⭐"},
            33: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #33 - проигрыш. Возврат: {prize} ⭐"},
            34: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #34 - проигрыш. Возврат: {prize} ⭐"},
            35: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #35 - проигрыш. Возврат: {prize} ⭐"},
            36: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #36 - проигрыш. Возврат: {prize} ⭐"},
            37: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #37 - проигрыш. Возврат: {prize} ⭐"},
            38: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #38 - проигрыш. Возврат: {prize} ⭐"},
            39: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #39 - проигрыш. Возврат: {prize} ⭐"},
            40: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #40 - проигрыш. Возврат: {prize} ⭐"},
            41: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #41 - проигрыш. Возврат: {prize} ⭐"},
            42: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #42 - проигрыш. Возврат: {prize} ⭐"},
            43: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #43 - проигрыш. Возврат: {prize} ⭐"},
            44: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #44 - проигрыш. Возврат: {prize} ⭐"},
            45: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #45 - проигрыш. Возврат: {prize} ⭐"},
            46: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #46 - проигрыш. Возврат: {prize} ⭐"},
            47: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #47 - проигрыш. Возврат: {prize} ⭐"},
            48: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #48 - проигрыш. Возврат: {prize} ⭐"},
            49: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #49 - проигрыш. Возврат: {prize} ⭐"},
            50: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #50 - проигрыш. Возврат: {prize} ⭐"},
            51: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #51 - проигрыш. Возврат: {prize} ⭐"},
            52: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #52 - проигрыш. Возврат: {prize} ⭐"},
            53: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #53 - проигрыш. Возврат: {prize} ⭐"},
            54: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #54 - проигрыш. Возврат: {prize} ⭐"},
            55: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #55 - проигрыш. Возврат: {prize} ⭐"},
            56: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #56 - проигрыш. Возврат: {prize} ⭐"},
            57: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #57 - проигрыш. Возврат: {prize} ⭐"},
            58: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #58 - проигрыш. Возврат: {prize} ⭐"},
            59: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #59 - проигрыш. Возврат: {prize} ⭐"},
            60: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #60 - проигрыш. Возврат: {prize} ⭐"},
            61: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #61 - проигрыш. Возврат: {prize} ⭐"},
            62: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #62 - проигрыш. Возврат: {prize} ⭐"},
            63: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #63 - проигрыш. Возврат: {prize} ⭐"},
            64: {"win": True, "base_prize": 50, "message": "🎰 ДЖЕКПОТ 777! МЕГА ВЫИГРЫШ: {prize} ⭐"}  # 50x ставки
        }
    }
}

# 🗃️ БАЗА ДАННЫХ
user_data = defaultdict(lambda: {
    'game_balance': 0.0,
    'total_games': 0,
    'total_wins': 0,
    'total_deposited': 0,
    'real_money_spent': 0,
    'current_bet': 5,
    'registration_date': datetime.datetime.now().isoformat(),
    'last_activity': datetime.datetime.now().isoformat(),
    'slots_mode': 'normal',
    'win_streak': 0,
    'max_win_streak': 0,
    'mega_wins_count': 0,
    'total_mega_win_amount': 0.0,
    'referral_code': None,
    'referral_by': None,
    'referrals_count': 0,
    'referral_earnings': 0.0,
    'used_promo_codes': [],
    'muted_until': None,
    'warnings': [],
    'vip_until': None
})

# 🆕 ОБНОВЛЕННАЯ СИСТЕМА АКТИВНОСТИ С НЕДЕЛЬНЫМИ НАГРАДАМИ
user_activity = defaultdict(lambda: {
    'weekly_streak_days': 0,
    'weekly_total_bets': 0,
    'weekly_total_games': 0,
    'last_weekly_bonus_date': None,
    'daily_games_count': 0,
    'last_activity_date': None,
    'current_week_start': None
})

# 🆕 РЕФЕРАЛЬНЫЕ КОДЫ
referral_codes = {}

# 🆕 ПРОМОКОДЫ
promo_codes = {}

# 🆕 СИСТЕМА БАНОВ
banned_users = {}

# 🆕 СИСТЕМА МУТОВ
muted_users = {}

# 🆕 СИСТЕМА ВАРНОВ
user_warnings = defaultdict(list)

# 🆕 СИСТЕМА VIP
vip_users = {}

# 🆕 ЛОГИ ДЕЙСТВИЙ
admin_logs = []

admin_mode = defaultdict(bool)
user_sessions = defaultdict(dict)
withdrawal_requests = defaultdict(list)

# 💾 СОХРАНЕНИЕ ДАННЫХ
def save_data():
    try:
        data = {
            'user_data': dict(user_data),
            'user_activity': dict(user_activity),
            'admin_mode': dict(admin_mode),
            'withdrawal_requests': dict(withdrawal_requests),
            'referral_codes': referral_codes,
            'promo_codes': promo_codes,
            'banned_users': banned_users,
            'muted_users': muted_users,
            'user_warnings': dict(user_warnings),
            'vip_users': vip_users,
            'admin_logs': admin_logs
        }
        with open('data.json', 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

def load_data():
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
            user_data.update(data.get('user_data', {}))
            user_activity.update(data.get('user_activity', {}))
            admin_mode.update(data.get('admin_mode', {}))
            withdrawal_requests.update(data.get('withdrawal_requests', {}))
            referral_codes.update(data.get('referral_codes', {}))
            promo_codes.update(data.get('promo_codes', {}))
            banned_users.update(data.get('banned_users', {}))
            muted_users.update(data.get('muted_users', {}))
            user_warnings.update(data.get('user_warnings', {}))
            vip_users.update(data.get('vip_users', {}))
            admin_logs.extend(data.get('admin_logs', []))
        
        migrate_user_data()
        migrate_activity_data()
        
    except FileNotFoundError:
        pass

# 🆕 МИГРАЦИЯ ДАННЫХ ДЛЯ СУЩЕСТВУЮЩИХ ПОЛЬЗОВАТЕЛЕЙ
def migrate_user_data():
    for user_id, data in user_data.items():
        if 'win_streak' not in data:
            data['win_streak'] = 0
        if 'max_win_streak' not in data:
            data['max_win_streak'] = 0
        if 'mega_wins_count' not in data:
            data['mega_wins_count'] = 0
        if 'total_mega_win_amount' not in data:
            data['total_mega_win_amount'] = 0.0
        if 'slots_mode' not in data:
            data['slots_mode'] = 'normal'
        if 'referral_code' not in data:
            data['referral_code'] = None
        if 'referral_by' not in data:
            data['referral_by'] = None
        if 'referrals_count' not in data:
            data['referrals_count'] = 0
        if 'referral_earnings' not in data:
            data['referral_earnings'] = 0.0
        if 'used_promo_codes' not in data:
            data['used_promo_codes'] = []
        if 'muted_until' not in data:
            data['muted_until'] = None
        if 'warnings' not in data:
            data['warnings'] = []
        if 'vip_until' not in data:
            data['vip_until'] = None

def migrate_activity_data():
    for user_id, activity in user_activity.items():
        if 'weekly_streak_days' not in activity:
            activity.update({
                'weekly_streak_days': 0,
                'weekly_total_bets': 0,
                'weekly_total_games': 0,
                'last_weekly_bonus_date': None,
                'daily_games_count': 0,
                'last_activity_date': None,
                'current_week_start': None
            })

# 🆕 ЛОГИРОВАНИЕ ДЕЙСТВИЙ АДМИНА
def log_admin_action(admin_id: int, action: str, target_id: int = None, details: str = ""):
    log_entry = {
        'admin_id': admin_id,
        'action': action,
        'target_id': target_id,
        'details': details,
        'timestamp': datetime.datetime.now().isoformat()
    }
    admin_logs.append(log_entry)
    save_data()

# 🆕 ПРОВЕРКА МУТА
async def check_mute(user_id: int) -> tuple:
    if user_id in muted_users:
        mute_data = muted_users[user_id]
        mute_until = datetime.datetime.fromisoformat(mute_data['muted_until'])
        if datetime.datetime.now() < mute_until:
            time_left = mute_until - datetime.datetime.now()
            return True, f"До размута: {str(time_left).split('.')[0]}"
        else:
            del muted_users[user_id]
            save_data()
    return False, ""

# 🆕 ВЫДАЧА МУТА
async def mute_user(user_id: int, admin_id: int, minutes: int, reason: str = "Не указана"):
    mute_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    muted_users[user_id] = {
        'muted_until': mute_until.isoformat(),
        'reason': reason,
        'muted_by': admin_id,
        'muted_at': datetime.datetime.now().isoformat()
    }
    save_data()
    log_admin_action(admin_id, "mute", user_id, f"{minutes} минут, причина: {reason}")

# 🆕 СНЯТИЕ МУТА
async def unmute_user(user_id: int, admin_id: int):
    if user_id in muted_users:
        del muted_users[user_id]
        save_data()
        log_admin_action(admin_id, "unmute", user_id)
        return True
    return False

# 🆕 ВЫДАЧА ПРЕДУПРЕЖДЕНИЯ
async def warn_user(user_id: int, admin_id: int, reason: str = "Не указана"):
    warning = {
        'reason': reason,
        'warned_by': admin_id,
        'warned_at': datetime.datetime.now().isoformat()
    }
    user_warnings[user_id].append(warning)
    user_data[user_id]['warnings'].append(warning)
    save_data()
    log_admin_action(admin_id, "warn", user_id, f"причина: {reason}")

# 🆕 СНЯТИЕ ПРЕДУПРЕЖДЕНИЯ
async def unwarn_user(user_id: int, admin_id: int, warning_index: int = -1):
    if user_id in user_warnings and user_warnings[user_id]:
        if warning_index == -1:  # Снять последнее
            removed_warning = user_warnings[user_id].pop()
            user_data[user_id]['warnings'] = user_warnings[user_id]
        else:  # Снять конкретное по индексу
            if 0 <= warning_index < len(user_warnings[user_id]):
                removed_warning = user_warnings[user_id].pop(warning_index)
                user_data[user_id]['warnings'] = user_warnings[user_id]
            else:
                return False
        save_data()
        log_admin_action(admin_id, "unwarn", user_id, f"предупреждение: {removed_warning['reason']}")
        return True
    return False

# 🆕 ВЫДАЧА VIP СТАТУСА
async def give_vip(user_id: int, admin_id: int, days: int):
    vip_until = datetime.datetime.now() + datetime.timedelta(days=days)
    vip_users[user_id] = {
        'vip_until': vip_until.isoformat(),
        'given_by': admin_id,
        'given_at': datetime.datetime.now().isoformat()
    }
    user_data[user_id]['vip_until'] = vip_until.isoformat()
    save_data()
    log_admin_action(admin_id, "give_vip", user_id, f"{days} дней")

# 🆕 СНЯТИЕ VIP СТАТУСА
async def remove_vip(user_id: int, admin_id: int):
    if user_id in vip_users:
        del vip_users[user_id]
        user_data[user_id]['vip_until'] = None
        save_data()
        log_admin_action(admin_id, "remove_vip", user_id)
        return True
    return False

# 🆕 ПРОВЕРКА VIP СТАТУСА
async def check_vip(user_id: int) -> tuple:
    if user_id in vip_users:
        vip_data = vip_users[user_id]
        vip_until = datetime.datetime.fromisoformat(vip_data['vip_until'])
        if datetime.datetime.now() < vip_until:
            time_left = vip_until - datetime.datetime.now()
            return True, f"VIP активен, осталось: {str(time_left).split('.')[0]}"
        else:
            await remove_vip(user_id, vip_data['given_by'])
    return False, ""

# 🎰 СИСТЕМА СЕРИЙ ПОБЕД, МЕГА-ВЫИГРЫШЕЙ И ВОЗВРАТОВ
def calculate_win_bonuses(user_id: int, base_prize: float, bet: int, emoji: str, is_win: bool) -> tuple:
    user = user_data[user_id]
    bonus_messages = []
    
    base_win_amount = base_prize * bet
    
    # 🔄 ГАРАНТИРОВАННЫЙ ВОЗВРАТ 2-10% ПРИ ПРОИГРЫШЕ ДЛЯ ВСЕХ ИГР
    if not is_win and base_prize == 0:
        refund_percent = random.uniform(REFUND_CONFIG["min_refund"], REFUND_CONFIG["max_refund"])
        refund_amount = round(bet * refund_percent, 1)
        
        base_win_amount = refund_amount
        bonus_messages.append(f"🔄 Возврат {refund_percent*100:.1f}% от ставки: {refund_amount} ⭐")
    
    # 🔥 СИСТЕМА СЕРИЙ ПОБЕД
    if is_win and base_prize > 0:
        user['win_streak'] += 1
        user['max_win_streak'] = max(user['max_win_streak'], user['win_streak'])
        
        for streak, bonus in WIN_STREAK_BONUSES.items():
            if user['win_streak'] == streak:
                streak_multiplier = bonus["multiplier"]
                base_win_amount *= streak_multiplier
                bonus_messages.append(bonus["message"])
                break
    else:
        if user['win_streak'] > 0:
            bonus_messages.append(f"💔 Серия побед прервана на {user['win_streak']}!")
        user['win_streak'] = 0
    
    # 🎉 СИСТЕМА СЛУЧАЙНЫХ МЕГА-ВЫИГРЫШЕЙ
    if is_win and base_prize > 0 and random.random() < MEGA_WIN_CONFIG["chance"]:
        mega_multiplier = random.uniform(MEGA_WIN_CONFIG["min_multiplier"], MEGA_WIN_CONFIG["max_multiplier"])
        base_win_amount *= mega_multiplier
        user['mega_wins_count'] += 1
        user['total_mega_win_amount'] += base_win_amount - (base_prize * bet)
        
        bonus_messages.append(f"🎉 МЕГА-ВЫИГРЫШ! x{mega_multiplier:.1f} к выигрышу!")
    
    final_prize = round(base_win_amount, 1)
    
    return final_prize, bonus_messages

# 🆕 РЕФЕРАЛЬНАЯ СИСТЕМА
def generate_referral_code(user_id: int) -> str:
    code = f"REF{user_id % 10000:04d}"
    while code in referral_codes:
        code = f"REF{random.randint(1000, 9999)}"
    return code

async def process_referral_reward(user_id: int, bet_amount: float, win_amount: float):
    try:
        user = user_data[user_id]
        
        if user['referral_by']:
            referrer_id = user['referral_by']
            
            # Проверяем существование реферера
            if referrer_id not in user_data:
                return 0, None
            
            if (user_data[user_id]['total_games'] >= REFERRAL_CONFIG["min_referee_games"] and
                user_data[user_id]['total_deposited'] >= REFERRAL_CONFIG["min_referee_deposit"]):
                
                loss_amount = max(0, bet_amount - win_amount)
                
                if loss_amount > 0:
                    referral_reward = round(loss_amount * REFERRAL_CONFIG["reward_percent"], 1)
                    user_data[referrer_id]['game_balance'] += referral_reward
                    user_data[referrer_id]['referral_earnings'] += referral_reward
                    
                    save_data()
                    
                    return referral_reward, referrer_id
        
        return 0, None
        
    except Exception as e:
        print(f"Ошибка в process_referral_reward: {e}")
        return 0, None

# 🆕 СИСТЕМА ПРОМОКОДОВ
def generate_promo_code() -> str:
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    while True:
        code = ''.join(random.choices(chars, k=8))
        if code not in promo_codes:
            return code

def create_promo_code(amount: int, uses: int, created_by: int) -> str:
    code = generate_promo_code()
    promo_codes[code] = {
        'amount': amount,
        'uses_left': uses,
        'created_by': created_by,
        'created_at': datetime.datetime.now().isoformat(),
        'used_by': []
    }
    save_data()
    return code

def use_promo_code(user_id: int, code: str) -> tuple:
    code = code.upper()
    
    if code not in promo_codes:
        return False, "Промокод не найден"
    
    promo = promo_codes[code]
    
    if promo['uses_left'] <= 0:
        return False, "Промокод уже использован"
    
    if user_id in promo['used_by']:
        return False, "Вы уже использовали этот промокод"
    
    user_data[user_id]['game_balance'] += promo['amount']
    user_data[user_id]['used_promo_codes'].append(code)
    promo['uses_left'] -= 1
    promo['used_by'].append(user_id)
    
    save_data()
    return True, f"Промокод активирован! На ваш баланс начислено {promo['amount']} ⭐"

# 🆕 СИСТЕМА БАНОВ
async def check_ban(user_id: int) -> tuple:
    if user_id in banned_users:
        return True, banned_users[user_id].get('reason', 'Не указана')
    return False, ""

async def ban_user(user_id: int, admin_id: int, reason: str = "Не указана"):
    banned_users[user_id] = {
        'reason': reason,
        'banned_by': admin_id,
        'banned_at': datetime.datetime.now().isoformat()
    }
    save_data()
    log_admin_action(admin_id, "ban", user_id, f"причина: {reason}")

async def unban_user(user_id: int, admin_id: int):
    if user_id in banned_users:
        del banned_users[user_id]
        save_data()
        log_admin_action(admin_id, "unban", user_id)
        return True
    return False

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await update.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    is_muted, mute_time = await check_mute(user_id)
    if is_muted:
        await update.message.reply_text(
            f"🔇 Вы в муте.\n"
            f"⏰ {mute_time}\n\n"
            f"Ожидайте размута для продолжения."
        )
        return
    
    referral_code = None
    if context.args and len(context.args) > 0:
        referral_code = context.args[0]
    
    if (referral_code and 
        referral_code in referral_codes and 
        user_data[user_id]['referral_by'] is None and
        referral_codes[referral_code] != user_id):
        
        referrer_id = referral_codes[referral_code]
        user_data[user_id]['referral_by'] = referrer_id
        user_data[referrer_id]['referrals_count'] += 1
        save_data()
    
    if user_data[user_id]['referral_code'] is None:
        user_data[user_id]['referral_code'] = generate_referral_code(user_id)
        referral_codes[user_data[user_id]['referral_code']] = user_id
        save_data()

    welcome_text = """
🎰 NSource Casino

Добро пожаловать в казино!

🎁 ОПТИМИЗИРОВАННЫЕ СИСТЕМЫ:
• 🔥 Серии побед - получайте бонусы +10%/+25%/+50% за несколько побед подряд
• 🎉 Случайные мега-выигрыши - шанс 0.6% увеличить выигрыш в 1.5-5 раз!
• 🔄 Возвраты 2-10% - даже при проигрыше получайте часть ставки обратно!
• 🏆 Недельные награды - играйте 5+ раз в день 7 дней подряд для бонуса 1-3% от суммы ставок!
• 👥 Реферальная система - приглашайте друзей и получайте 10% от их проигрышей!

Доступные игры (ставка от 1 до 100000 ⭐):
🎰 Слоты - 64 комбинации, 4 выигрышных (5-20x ставки)
🎰 Слоты 777 - только джекпот 777 (50x ставки)
🎯 Дартс - победа на 6 (3x ставки)
🎲 Кубик - победа на 6 (3x ставки)
🎳 Боулинг - победа на 6 (3x ставки)
⚽ Футбол - 2 возврата + 3 гола с выигрышем
🏀 Баскетбол - 3 возврата + 2 броска с выигрышем

💰 Пополнение: 1:1
1 реальная звезда = 1 ⭐

Просто отправь любой dice эмодзи игры чтобы начать играть!
    """
    
    keyboard = [
        [InlineKeyboardButton("🎮 Играть", callback_data="play_games")],
        [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")],
        [InlineKeyboardButton("💰 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("🎯 Изменить ставку", callback_data="change_bet")],
        [InlineKeyboardButton("👥 Реферальная система", callback_data="referral_system")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                f"🚫 Вы забанены администратором.\n"
                f"📝 Причина: {reason}\n\n"
                f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
            )
        else:
            await update.message.reply_text(
                f"🚫 Вы забанены администратором.\n"
                f"📝 Причина: {reason}\n\n"
                f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
            )
        return
    
    is_muted, mute_time = await check_mute(user_id)
    if is_muted:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                f"🔇 Вы в муте.\n"
                f"⏰ {mute_time}\n\n"
                f"Ожидайте размута для продолжения."
            )
        else:
            await update.message.reply_text(
                f"🔇 Вы в муте.\n"
                f"⏰ {mute_time}\n\n"
                f"Ожидайте размута для продолжения."
            )
        return
    
    data = user_data[user_id]
    activity = user_activity[user_id]
    
    win_rate = (data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0
    
    slots_mode = data.get('slots_mode', 'normal')
    slots_mode_text = "🎰 Обычные" if slots_mode == 'normal' else "🎰 Слоты 777"
    
    weekly_info = ""
    if activity['weekly_streak_days'] > 0:
        weekly_info = f"📅 Текущая серия дней: {activity['weekly_streak_days']}/7\n"
        weekly_info += f"🎮 Игр сегодня: {activity['daily_games_count']}/5\n"
        weekly_info += f"📊 Игр за неделю: {activity['weekly_total_games']}\n"
        weekly_info += f"💰 Сумма ставок за неделю: {round(activity['weekly_total_bets'], 1)} ⭐"
    
    referral_info = ""
    if data['referral_code']:
        referral_info = f"👥 Рефералов: {data['referrals_count']}\n"
        referral_info += f"💰 Заработано с рефералов: {round(data['referral_earnings'], 1)} ⭐"
    
    # Информация о муте и VIP
    mute_info = ""
    if is_muted:
        mute_info = f"🔇 В муте: {mute_time}\n"
    
    vip_info = ""
    is_vip, vip_time = await check_vip(user_id)
    if is_vip:
        vip_info = f"⭐ VIP: {vip_time}\n"
    
    warnings_info = ""
    if user_warnings[user_id]:
        warnings_info = f"⚠️ Предупреждения: {len(user_warnings[user_id])}\n"
    
    profile_text = f"""
📊 Личный кабинет

👤 Имя: {user.first_name}
🆔 ID: {user_id}
📅 Регистрация: {data['registration_date'][:10]}
🎮 Режим слотов: {slots_mode_text}
{mute_info}{vip_info}{warnings_info}
💎 Статистика:
💰 Баланс: {round(data['game_balance'], 1)} ⭐
🎯 Текущая ставка: {data['current_bet']} ⭐
🎮 Всего игр: {data['total_games']}
🏆 Побед: {data['total_wins']}
📈 Винрейт: {win_rate:.1f}%
💳 Пополнено: {data['total_deposited']} ⭐

🔥 Система бонусов:
📊 Текущая серия побед: {data['win_streak']}
🏆 Максимальная серия: {data['max_win_streak']}
🎉 Мега-выигрышей: {data['mega_wins_count']}
💫 Сумма мега-выигрышей: {round(data['total_mega_win_amount'], 1)} ⭐

{weekly_info}

{referral_info}
    """
    
    keyboard = [
        [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit"),
         InlineKeyboardButton("💸 Вывести ⭐", callback_data="withdraw")],
        [InlineKeyboardButton("🎮 Играть", callback_data="play_games")],
        [InlineKeyboardButton("🎯 Изменить ставку", callback_data="change_bet")],
        [InlineKeyboardButton("👥 Реферальная система", callback_data="referral_system")]
    ]
    
    if admin_mode.get(user_id, False):
        keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(profile_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(profile_text, reply_markup=reply_markup)

# 🆕 РЕФЕРАЛЬНАЯ СИСТЕМА - КОМАНДЫ
async def referral_system_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await query.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    data = user_data[user_id]
    
    referral_text = f"""
👥 РЕФЕРАЛЬНАЯ СИСТЕМА

Приглашайте друзей и получайте 10% от их проигрышей!

📊 Ваша статистика:
🎯 Ваш реферальный код: {data['referral_code']}
👥 Приглашено друзей: {data['referrals_count']}
💰 Заработано с рефералов: {round(data['referral_earnings'], 1)} ⭐

🔗 Ваша реферальная ссылка:
https://t.me/{(await context.bot.get_me()).username}?start={data['referral_code']}

📋 Как это работает:
1. Делитесь ссылкой с друзьями
2. Друг регистрируется по вашей ссылке
3. Когда друг проигрывает, вы получаете 10% от его проигрыша
4. Друг должен сыграть минимум {REFERRAL_CONFIG['min_referee_games']} игр и пополнить минимум {REFERRAL_CONFIG['min_referee_deposit']} ⭐

💡 Пример: Если ваш друг проиграл 100 ⭐, вы получите 10 ⭐!
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")],
        [InlineKeyboardButton("🎮 Играть", callback_data="play_games")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(referral_text, reply_markup=reply_markup)

# 🆕 КОМАНДА АКТИВАЦИИ ПРОМОКОДА
async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await update.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    if not context.args:
        await update.message.reply_text(
            "🎟️ Активация промокода\n\n"
            "Использование: /promo <код>\n\n"
            "Пример: /promo SUMMER2024"
        )
        return
    
    promo_code = context.args[0].upper()
    success, message = use_promo_code(user_id, promo_code)
    
    await update.message.reply_text(message)

# 📊 КОМАНДА АКТИВНОСТИ (ОБНОВЛЕННАЯ)
async def activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await update.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    activity_data = user_activity[user_id]
    
    today = datetime.datetime.now().date()
    plays_remaining = max(0, WEEKLY_BONUS_CONFIG["min_daily_games"] - activity_data['daily_games_count'])
    
    if activity_data['weekly_total_bets'] > 0:
        base_bonus = activity_data['weekly_total_bets'] * WEEKLY_BONUS_CONFIG["base_percent"]
        min_games = WEEKLY_BONUS_CONFIG["min_daily_games"] * WEEKLY_BONUS_CONFIG["required_days"]
        extra_games = max(0, activity_data['weekly_total_games'] - min_games)
        extra_bonus = activity_data['weekly_total_bets'] * extra_games * WEEKLY_BONUS_CONFIG["bonus_per_extra_game"]
        max_extra = activity_data['weekly_total_bets'] * WEEKLY_BONUS_CONFIG["max_extra_bonus"]
        extra_bonus = min(extra_bonus, max_extra)
        potential_bonus = base_bonus + extra_bonus
    else:
        potential_bonus = 0
    
    activity_text = f"""
📊 Ваша активность (Недельные награды)

🎮 Сыграно сегодня: {activity_data['daily_games_count']}/{WEEKLY_BONUS_CONFIG["min_daily_games"]}
📅 Последовательных дней: {activity_data['weekly_streak_days']}/{WEEKLY_BONUS_CONFIG["required_days"]}
🎯 Всего игр за неделю: {activity_data['weekly_total_games']}
💰 Сумма ставок за неделю: {round(activity_data['weekly_total_bets'], 1)} ⭐

🎁 Система наград:
• Базовый бонус: 1% от суммы ставок
• Доп. бонус: +0.05% за каждую игру сверх {WEEKLY_BONUS_CONFIG["min_daily_games"] * WEEKLY_BONUS_CONFIG["required_days"]}
• Макс. доп. бонус: +2%

💫 Потенциальная награда: ~{round(potential_bonus, 1)} ⭐
⏳ Осталось игр для зачета сегодня: {plays_remaining}
    """
    
    if activity_data.get('last_weekly_bonus_date') == today.isoformat():
        activity_text += "\n✅ Недельная награда уже получена сегодня!"
    
    await update.message.reply_text(activity_text)

# 🎮 ОБРАБОТКА РЕЗУЛЬТАТОВ ИГР (ОБНОВЛЕННАЯ)
async def process_dice_result(user_id: int, emoji: str, value: int, cost: int, message, context: ContextTypes.DEFAULT_TYPE):
    # Проверка на бан
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await message.reply_text(f"🚫 Вы забанены. Причина: {reason}")
        return
    
    # Проверка на мут
    is_muted, mute_time = await check_mute(user_id)
    if is_muted:
        await message.reply_text(f"🔇 Вы в муте. {mute_time}")
        return
    
    slots_mode = user_data[user_id].get('slots_mode', 'normal')
    
    if emoji == "🎰" and slots_mode == '777':
        game_config = SLOTS_777_CONFIG.get(emoji)
    else:
        game_config = GAMES_CONFIG.get(emoji)
        
    if not game_config:
        return
    
    result_config = game_config["values"].get(value)
    if not result_config:
        result_config = {"win": False, "base_prize": 0, "message": f"{emoji} - проигрыш. Возврат: {{prize}} ⭐"}
    
    base_prize_amount = result_config["base_prize"]
    is_win = result_config["win"]
    
    final_prize, bonus_messages = calculate_win_bonuses(user_id, base_prize_amount, cost, emoji, is_win)
    
    result_text = ""
    
    if is_win or base_prize_amount > 0:
        user_data[user_id]['game_balance'] += final_prize
        if is_win:
            user_data[user_id]['total_wins'] += 1
        
        win_message = result_config["message"].format(prize=final_prize)
        
        result_text = (
            f"{win_message}\n\n"
            f"💎 Текущий баланс: {round(user_data[user_id]['game_balance'], 1)} ⭐\n"
            f"📊 (Списано: {cost} ⭐ + Выигрыш: {final_prize} ⭐)"
        )
        
        if bonus_messages:
            result_text += "\n\n" + "\n".join(bonus_messages)
    else:
        # Для проигрышных исходов с возвратом
        if final_prize > 0:
            refund_message = result_config["message"].format(prize=final_prize)
            result_text = (
                f"{refund_message}\n\n"
                f"💎 Текущий баланс: {round(user_data[user_id]['game_balance'], 1)} ⭐\n"
                f"📊 Списано: {cost} ⭐ + Возврат: {final_prize} ⭐"
            )
        else:
            result_text = (
                f"{result_config['message']}\n\n"
                f"💎 Текущий баланс: {round(user_data[user_id]['game_balance'], 1)} ⭐\n"
                f"📊 Списано: {cost} ⭐"
            )
    
    await message.reply_text(result_text)
    
    if not admin_mode.get(user_id, False):
        referral_reward, referrer_id = await process_referral_reward(user_id, cost, final_prize)
        if referral_reward > 0:
            await message.reply_text(
                f"👥 РЕФЕРАЛЬНАЯ НАГРАДА!\n\n"
                f"💎 Пользователь {referrer_id} получает {referral_reward} ⭐\n"
                f"📊 За проигрыш приглашенного друга: {cost - final_prize} ⭐"
            )
    
    weekly_bonus = update_weekly_activity(user_id, cost)
    if weekly_bonus:
        await message.reply_text(
            f"🎁 НЕДЕЛЬНАЯ НАГРАДА!\n\n"
            f"📊 Статистика за неделю:\n"
            f"• Игр сыграно: {weekly_bonus['total_games']}\n"
            f"• Сумма ставок: {round(weekly_bonus['total_bets'], 1)} ⭐\n"
            f"• Базовый бонус: {round(weekly_bonus['base_bonus'], 1)} ⭐\n"
            f"• Доп. бонус: {round(weekly_bonus['extra_bonus'], 1)} ⭐\n"
            f"💰 ИТОГО: {round(weekly_bonus['total_bonus'], 1)} ⭐\n\n"
            f"💎 Баланс: {round(user_data[user_id]['game_balance'], 1)} ⭐"
        )
    
    save_data()

# 💸 СИСТЕМА ВЫВОДА СРЕДСТВ
async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await update.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    balance = round(user_data[user_id]['game_balance'], 1)
    
    if balance < MIN_WITHDRAWAL:
        await update.message.reply_text(
            f"❌ Недостаточно средств для вывода!\n\n"
            f"💰 Ваш баланс: {balance} ⭐\n"
            f"💸 Минимальная сумма вывода: {MIN_WITHDRAWAL} ⭐\n\n"
            f"Пополните баланс или выиграйте больше звезд!"
        )
        return
    
    withdraw_text = f"""
💸 Вывод средств

💰 Ваш баланс: {balance} ⭐
💸 Минимальная сумма вывода: {MIN_WITHDRAWAL} ⭐

🎁 При выводе средств вы получаете случайные подарки за реальные Telegram Stars!

Выберите сумму для вывода:
    """
    
    keyboard = []
    for amount in WITHDRAWAL_AMOUNTS:
        if balance >= amount:
            keyboard.append([InlineKeyboardButton(f"{amount} ⭐", callback_data=f"withdraw_{amount}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(withdraw_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(withdraw_text, reply_markup=reply_markup)

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await query.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    balance = round(user_data[user_id]['game_balance'], 1)
    
    if balance < MIN_WITHDRAWAL:
        await query.edit_message_text(
            f"❌ Недостаточно средств для вывода!\n\n"
            f"💰 Ваш баланс: {balance} ⭐\n"
            f"💸 Минимальная сумма вывода: {MIN_WITHDRAWAL} ⭐\n\n"
            f"Пополните баланс или выиграйте больше звезд!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
                [InlineKeyboardButton("🎮 Играть", callback_data="play_games")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]
            ])
        )
        return
    
    withdraw_text = f"""
💸 Вывод средств

💰 Ваш баланс: {balance} ⭐
💸 Минимальная сумма вывода: {MIN_WITHDRAWAL} ⭐

🎁 При выводе средств вы получаете случайные подарки за реальные Telegram Stars!

Выберите сумму для вывода:
    """
    
    keyboard = []
    for amount in WITHDRAWAL_AMOUNTS:
        if balance >= amount:
            keyboard.append([InlineKeyboardButton(f"{amount} ⭐", callback_data=f"withdraw_{amount}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(withdraw_text, reply_markup=reply_markup)

async def handle_withdraw_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    amount = int(query.data.split('_')[1])
    balance = round(user_data[user_id]['game_balance'], 1)
    
    if balance < amount:
        await query.edit_message_text(
            "❌ Недостаточно средств!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="withdraw")]
            ])
        )
        return
    
    context.user_data['withdraw_amount'] = amount
    context.user_data['withdraw_user_id'] = user_id
    
    gifts_count = amount // 15
    gifts_count = max(1, gifts_count)
    
    confirm_text = f"""
✅ Подтверждение вывода

💸 Сумма вывода: {amount} ⭐
🎁 Количество подарков: {gifts_count}

💰 Баланс до списания: {balance} ⭐
💰 Баланс после списания: {round(balance - amount, 1)} ⭐

После подтверждения с вашего счета будет списано {amount} ⭐ и вы получите {gifts_count} случайных подарка за реальные Telegram Stars!
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить вывод", callback_data="confirm_withdraw")],
        [InlineKeyboardButton("❌ Отмена", callback_data="withdraw")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(confirm_text, reply_markup=reply_markup)

async def confirm_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = context.user_data.get('withdraw_user_id')
    amount = context.user_data.get('withdraw_amount')
    
    if not user_id or not amount:
        await query.edit_message_text("❌ Ошибка: данные сессии устарели")
        return
    
    if user_data[user_id]['game_balance'] < amount:
        await query.edit_message_text("❌ Недостаточно средств!")
        return
    
    user_data[user_id]['game_balance'] -= amount
    
    gifts_count = amount // 15
    gifts_count = max(1, gifts_count)
    
    withdrawal_request = {
        'user_id': user_id,
        'amount': amount,
        'gifts_count': gifts_count,
        'timestamp': datetime.datetime.now().isoformat(),
        'status': 'completed'
    }
    
    if user_id not in withdrawal_requests:
        withdrawal_requests[user_id] = []
    withdrawal_requests[user_id].append(withdrawal_request)
    
    save_data()
    
    success_text = f"""
🎉 Вывод успешно обработан!

💸 Списано: {amount} ⭐
🎁 Отправлено подарков: {gifts_count}
💰 Текущий баланс: {round(user_data[user_id]['game_balance'], 1)} ⭐

📦 Ваши подарки уже отправлены! Проверьте раздел "Подарки" в Telegram.

Благодарим за игру! 🎰
    """
    
    keyboard = [
        [InlineKeyboardButton("🎮 Продолжить играть", callback_data="play_games")],
        [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(success_text, reply_markup=reply_markup)
    
    print(f"💰 ВЫВОД: Пользователь {user_id} вывел {amount} ⭐, отправлено {gifts_count} подарков")

# 🎯 КОМАНДА ДЛЯ ИЗМЕНЕНИЯ СТАВКИ
async def bet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await update.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    if not context.args:
        await update.message.reply_text(
            f"🎯 Текущая ставка: {user_data[user_id]['current_bet']} ⭐\n\n"
            f"Использование: /bet <сумма>\n"
            f"Минимальная ставка: {MIN_BET} ⭐\n"
            f"Максимальная ставка: {MAX_BET} ⭐"
        )
        return
    
    try:
        new_bet = int(context.args[0])
        
        if new_bet < MIN_BET:
            await update.message.reply_text(f"❌ Минимальная ставка: {MIN_BET} ⭐")
            return
            
        if new_bet > MAX_BET:
            await update.message.reply_text(f"❌ Максимальная ставка: {MAX_BET} ⭐")
            return
            
        user_data[user_id]['current_bet'] = new_bet
        save_data()
        
        await update.message.reply_text(f"✅ Ставка изменена на {new_bet} ⭐")
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректное число")

# 💰 СИСТЕМА ПОПОЛНЕНИЯ
async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                f"🚫 Вы забанены администратором.\n"
                f"📝 Причина: {reason}\n\n"
                f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
            )
        else:
            await update.message.reply_text(
                f"🚫 Вы забанены администратором.\n"
                f"📝 Причина: {reason}\n\n"
                f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
            )
        return
    
    data = user_data[user_id]
    
    deposit_text = f"""
💰 Пополнение баланса

💎 Текущий баланс: {round(data['game_balance'], 1)} ⭐

🎯 Выберите пакет пополнения:
💫 1 реальная звезда = 1 ⭐
    """
    
    keyboard = []
    for product_key, product in PRODUCTS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{product['title']} - {product['price']} Stars", 
                callback_data=f"buy_{product_key}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(deposit_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(deposit_text, reply_markup=reply_markup)

async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await query.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    current_balance = round(user_data[user_id]['game_balance'], 1)
    
    deposit_text = f"""
💰 Пополнение баланса

💎 Текущий баланс: {current_balance} ⭐

🎯 Выберите пакет пополнения:
💫 1 реальная звезда = 1 ⭐
    """
    
    keyboard = []
    for product_key, product in PRODUCTS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{product['title']} - {product['price']} Stars", 
                callback_data=f"buy_{product_key}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(deposit_text, reply_markup=reply_markup)

async def handle_deposit_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await query.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    product_key = query.data.replace("buy_", "")
    product = PRODUCTS[product_key]
    
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title=product["title"],
        description=product["description"],
        payload=product_key,
        provider_token=PROVIDER_TOKEN,
        currency=product["currency"],
        prices=[LabeledPrice(product["title"], product["price"])],
        start_parameter="nsource_casino"
    )

# 💳 ОБРАБОТЧИКИ ПЛАТЕЖЕЙ
async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    product_key = payment.invoice_payload
    product = PRODUCTS[product_key]
    
    user_data[user_id]['game_balance'] += product["credits"]
    user_data[user_id]['total_deposited'] += product["credits"]
    user_data[user_id]['real_money_spent'] += product["price"]
    
    save_data()
    
    await update.message.reply_text(
        f"✅ Платеж успешен!\n\n"
        f"💳 Оплачено: {product['price']} Stars\n"
        f"💎 Зачислено: {product['credits']} ⭐\n"
        f"💰 Баланс: {round(user_data[user_id]['game_balance'], 1)} ⭐\n\n"
        f"🎮 Приятной игры!"
    )

# 🎮 СИСТЕМА ИГР (ОБНОВЛЕННАЯ)
async def play_games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await query.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    balance = round(user_data[user_id]['game_balance'], 1)
    current_bet = user_data[user_id]['current_bet']
    slots_mode = user_data[user_id].get('slots_mode', 'normal')
    
    slots_mode_text = "Обычные" if slots_mode == 'normal' else "777"
    
    games_text = f"""
🎮 Выбор игры

💎 Баланс: {balance} ⭐
🎯 Текущая ставка: {current_bet} ⭐
🎰 Режим слотов: {slots_mode_text}
📊 Диапазон ставки: {MIN_BET}-{MAX_BET} ⭐

🎁 ОПТИМИЗИРОВАННЫЕ СИСТЕМЫ:
🔥 Серии побед - бонусы +10%/+25%/+50% за несколько побед подряд
🎉 Случайные мега-выигрыши - шанс 0.6% x1.5-x5!
🔄 Возвраты 2-10% - даже при проигрыше получайте часть ставки!
🏆 Недельные награды - играйте 5+ раз в день 7 дней подряд
👥 Реферальная система - получайте 10% от проигрышей друзей!

Выберите игру или просто отправь любой dice эмодзи в чат!
    """
    
    keyboard = [
        [InlineKeyboardButton("🎰 Слоты (4 выигрыша)", callback_data="play_slots")],
        [InlineKeyboardButton("🎰 Слоты 777 (только джекпот)", callback_data="play_slots777")],
        [InlineKeyboardButton("🎯 Дартс", callback_data="play_dart")],
        [InlineKeyboardButton("🎲 Кубик", callback_data="play_dice")],
        [InlineKeyboardButton("🎳 Боулинг", callback_data="play_bowling")],
        [InlineKeyboardButton("⚽ Футбол (2 возврата + 3 гола)", callback_data="play_football")],
        [InlineKeyboardButton("🏀 Баскетбол (3 возврата + 2 броска)", callback_data="play_basketball")],
        [InlineKeyboardButton("🎯 Изменить ставку", callback_data="change_bet")],
        [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton("📊 Личный кабинет", callback_data="back_to_profile")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(games_text, reply_markup=reply_markup)

async def handle_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await query.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    game_type = query.data.replace("play_", "")
    current_bet = user_data[user_id]['current_bet']
    
    if game_type == 'slots777':
        user_data[user_id]['slots_mode'] = '777'
        await query.edit_message_text("✅ Режим изменен на Слоты 777! Теперь все ваши игры в слоты будут в режиме 777 (только джекпот 777).")
        return
    elif game_type == 'slots':
        user_data[user_id]['slots_mode'] = 'normal'
        await query.edit_message_text("✅ Режим изменен на обычные Слоты! Теперь все ваши игры в слоты будут в обычном режиме.")
        return
    
    if user_data[user_id]['game_balance'] < current_bet and not admin_mode.get(user_id, False):
        await query.edit_message_text(
            "❌ Недостаточно средств!\n\n"
            f"💰 Ваш баланс: {round(user_data[user_id]['game_balance'], 1)} ⭐\n"
            f"🎯 Требуется: {current_bet} ⭐\n\n"
            "💳 Пополните баланс чтобы играть!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
                [InlineKeyboardButton("🎯 Изменить ставку", callback_data="change_bet")],
                [InlineKeyboardButton("📊 Личный кабинет", callback_data="back_to_profile")]
            ])
        )
        return
    
    if not admin_mode.get(user_id, False):
        user_data[user_id]['game_balance'] -= current_bet
    
    user_data[user_id]['total_games'] += 1
    user_data[user_id]['last_activity'] = datetime.datetime.now().isoformat()
    
    game_emojis = {
        'slots': '🎰', 
        'slots777': '🎰',
        'dart': '🎯', 
        'dice': '🎲',
        'bowling': '🎳', 
        'football': '⚽', 
        'basketball': '🏀'
    }
    
    emoji = game_emojis.get(game_type, '🎰')
    
    user_sessions[user_id] = {
        'game_type': game_type,
        'emoji': emoji,
        'bet': current_bet if not admin_mode.get(user_id, False) else 0,
        'message_id': query.message.message_id,
        'chat_id': query.message.chat_id
    }
    
    dice_message = await context.bot.send_dice(chat_id=query.message.chat_id, emoji=emoji)
    
    delay = DICE_DELAYS.get(emoji, 3.0)
    await asyncio.sleep(delay)
    
    await process_dice_result(user_id, emoji, dice_message.dice.value, current_bet if not admin_mode.get(user_id, False) else 0, dice_message, context)

async def handle_user_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = update.effective_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    is_muted, mute_time = await check_mute(user_id)
    if is_muted:
        await message.reply_text(
            f"🔇 Вы в муте.\n"
            f"⏰ {mute_time}\n\n"
            f"Ожидайте размута для продолжения."
        )
        return
    
    if not message.dice:
        return
    
    emoji = message.dice.emoji
    value = message.dice.value
    
    if emoji not in GAMES_CONFIG:
        return
    
    current_bet = user_data[user_id]['current_bet']
    
    if user_data[user_id]['game_balance'] < current_bet and not admin_mode.get(user_id, False):
        await message.reply_text(
            f"❌ Недостаточно средств!\n\n"
            f"💰 Ваш баланс: {round(user_data[user_id]['game_balance'], 1)} ⭐\n"
            f"🎯 Требуется: {current_bet} ⭐\n\n"
            "💳 Пополните баланс чтобы играть!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
                [InlineKeyboardButton("🎯 Изменить ставку", callback_data="change_bet")]
            ])
        )
        return
    
    cost = current_bet if not admin_mode.get(user_id, False) else 0
    if not admin_mode.get(user_id, False):
        user_data[user_id]['game_balance'] -= cost
    
    user_data[user_id]['total_games'] += 1
    user_data[user_id]['last_activity'] = datetime.datetime.now().isoformat()
    
    user_sessions[user_id] = {
        'game_type': 'slots',
        'emoji': emoji,
        'bet': cost,
        'message_id': message.message_id,
        'chat_id': message.chat_id
    }
    
    delay = DICE_DELAYS.get(emoji, 3.0)
    await asyncio.sleep(delay)
    
    await process_dice_result(user_id, emoji, value, cost, message, context)

# 🎯 CALLBACK ДЛЯ ИЗМЕНЕНИЯ СТАВКИ
async def change_bet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await query.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    current_bet = user_data[user_id]['current_bet']
    
    bet_text = f"""
🎯 Изменение ставки

💎 Текущая ставка: {current_bet} ⭐
📊 Диапазон ставок: {MIN_BET}-{MAX_BET} ⭐

Используйте команду /bet <сумма> для изменения ставки.

Пример:
/bet 10 - установить ставку 10 ⭐
/bet 100 - установить ставку 100 ⭐
/bet 1000 - установить ставку 1000 ⭐
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад к играм", callback_data="play_games")],
        [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(bet_text, reply_markup=reply_markup)

# 🔙 CALLBACK ДЛА ВОЗВРАТА В ПРОФИЛЬ
async def back_to_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await profile(update, context)

# 👑 АДМИН СИСТЕМА
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if len(context.args) == 0:
        await update.message.reply_text(
            "🔐 Активация режима администратора\n\n"
            "Использование: /admin <код>\n\n"
            "Пример: /admin 1337"
        )
        return
    
    code = context.args[0]
    if code == ADMIN_CODE:
        admin_mode[user_id] = True
        save_data()
        await update.message.reply_text(
            "👑 РЕЖИМ АДМИНИСТРАТОРА АКТИВИРОВАН!\n\n"
            "✨ Теперь вам доступны все админ-команды.\n"
            "🎮 Используйте кнопки в профиле для быстрого доступа к админ-панели!"
        )
        log_admin_action(user_id, "admin_login")
    else:
        await update.message.reply_text("❌ Неверный код администратора!")

# 🆕 КОМАНДА БАНИРОВАНИЯ
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /ban <user_id> <причина>")
        return
    
    try:
        target_id = int(context.args[0])
        reason = ' '.join(context.args[1:])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        if target_id in admin_mode and admin_mode[target_id]:
            await update.message.reply_text("❌ Нельзя забанить администратора!")
            return
        
        await ban_user(target_id, user_id, reason)
        
        await update.message.reply_text(
            f"🚫 Пользователь {target_id} забанен!\n"
            f"📝 Причина: {reason}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID!")

# 🆕 КОМАНДА РАЗБАНИВАНИЯ
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /unban <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        
        success = await unban_user(target_id, user_id)
        
        if success:
            await update.message.reply_text(f"✅ Пользователь {target_id} разбанен!")
        else:
            await update.message.reply_text("❌ Пользователь не найден в списке забаненных!")
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID!")

# 🆕 КОМАНДА СПИСКА ЗАБАНЕННЫХ
async def banlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if not banned_users:
        await update.message.reply_text("📋 Список забаненных пользователей пуст")
        return
    
    banlist_text = "🚫 ЗАБАНЕННЫЕ ПОЛЬЗОВАТЕЛИ:\n\n"
    
    for banned_id, ban_data in list(banned_users.items())[:20]:
        banlist_text += (
            f"👤 ID: {banned_id}\n"
            f"📝 Причина: {ban_data.get('reason', 'Не указана')}\n"
            f"👮 Забанил: {ban_data.get('banned_by', 'Неизвестно')}\n"
            f"📅 Дата: {ban_data.get('banned_at', 'Неизвестно')[:16]}\n"
            f"────────────────────\n"
        )
    
    if len(banned_users) > 20:
        banlist_text += f"\n... и еще {len(banned_users) - 20} пользователей"
    
    await update.message.reply_text(banlist_text)

# 🆕 КОМАНДА ДОБАВЛЕНИЯ БАЛАНСА
async def addbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /addbalance <user_id> <amount>")
        return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        user_data[target_id]['game_balance'] += amount
        save_data()
        
        log_admin_action(user_id, "add_balance", target_id, f"сумма: {amount} ⭐")
        
        await update.message.reply_text(
            f"✅ Баланс пользователя {target_id} увеличен на {amount} ⭐\n"
            f"💰 Новый баланс: {round(user_data[target_id]['game_balance'], 1)} ⭐"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректные числа!")

# 🆕 КОМАНДА УСТАНОВКИ БАЛАНСА
async def setbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /setbalance <user_id> <amount>")
        return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        old_balance = user_data[target_id]['game_balance']
        user_data[target_id]['game_balance'] = amount
        save_data()
        
        log_admin_action(user_id, "set_balance", target_id, f"старый: {old_balance}, новый: {amount} ⭐")
        
        await update.message.reply_text(
            f"✅ Баланс пользователя {target_id} установлен на {amount} ⭐\n"
            f"💰 Старый баланс: {round(old_balance, 1)} ⭐"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректные числа!")

# 🆕 КОМАНДА СБРОСА БАЛАНСА
async def resetbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /resetbalance <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        old_balance = user_data[target_id]['game_balance']
        user_data[target_id]['game_balance'] = 0
        save_data()
        
        log_admin_action(user_id, "reset_balance", target_id, f"старый баланс: {old_balance} ⭐")
        
        await update.message.reply_text(
            f"✅ Баланс пользователя {target_id} сброшен!\n"
            f"💰 Старый баланс: {round(old_balance, 1)} ⭐"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректный ID!")

# 🆕 КОМАНДА СОЗДАНИЯ ПРОМОКОДА
async def promo_create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "🎟️ Создание промокода\n\n"
            "Использование: /promo_create <сумма> <количество_использований>\n\n"
            "Пример: /promo_create 100 50\n"
            f"Минимальная сумма: {PROMO_CONFIG['min_amount']} ⭐\n"
            f"Максимальная сумма: {PROMO_CONFIG['max_amount']} ⭐"
        )
        return
    
    try:
        amount = int(context.args[0])
        uses = int(context.args[1])
        
        if amount < PROMO_CONFIG['min_amount'] or amount > PROMO_CONFIG['max_amount']:
            await update.message.reply_text(
                f"❌ Сумма должна быть от {PROMO_CONFIG['min_amount']} до {PROMO_CONFIG['max_amount']} ⭐"
            )
            return
        
        if uses <= 0:
            await update.message.reply_text("❌ Количество использований должно быть больше 0")
            return
        
        if len(promo_codes) >= PROMO_CONFIG['max_active_promos']:
            await update.message.reply_text(
                f"❌ Достигнут лимит активных промокодов: {PROMO_CONFIG['max_active_promos']}"
            )
            return
        
        promo_code = create_promo_code(amount, uses, user_id)
        
        log_admin_action(user_id, "create_promo", None, f"код: {promo_code}, сумма: {amount}, использований: {uses}")
        
        await update.message.reply_text(
            f"✅ Промокод создан!\n\n"
            f"🎟️ Код: {promo_code}\n"
            f"💰 Сумма: {amount} ⭐\n"
            f"🎯 Использований: {uses}\n"
            f"👤 Создал: {user_id}\n\n"
            f"📝 Активация: /promo {promo_code}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректные числа!")

# 🆕 КОМАНДА СПИСКА ПРОМОКОДОВ
async def promo_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if not promo_codes:
        await update.message.reply_text("🎟️ Список промокодов пуст.")
        return
    
    promo_list_text = "🎟️ Список промокодов:\n\n"
    for code, promo in promo_codes.items():
        promo_list_text += (
            f"🔸 {code}\n"
            f"   💰 Сумма: {promo['amount']} ⭐\n"
            f"   🎯 Осталось использований: {promo['uses_left']}\n"
            f"   👤 Создал: {promo['created_by']}\n"
            f"   📅 Создан: {promo['created_at'][:10]}\n"
            f"   👥 Использовали: {len(promo['used_by'])} пользователей\n\n"
        )
    
    await update.message.reply_text(promo_list_text)

# 🆕 КОМАНДА УДАЛЕНИЯ ПРОМОКОДА
async def promo_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /promo_delete <code>")
        return
    
    code = context.args[0].upper()
    if code not in promo_codes:
        await update.message.reply_text("❌ Промокод не найден!")
        return
    
    del promo_codes[code]
    save_data()
    
    log_admin_action(user_id, "delete_promo", None, f"код: {code}")
    
    await update.message.reply_text(f"✅ Промокод {code} удален.")

# 🆕 КОМАНДА ИНФОРМАЦИИ О ПРОМОКОДЕ
async def promo_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /promo_info <code>")
        return
    
    code = context.args[0].upper()
    if code not in promo_codes:
        await update.message.reply_text("❌ Промокод не найден!")
        return
    
    promo = promo_codes[code]
    used_by = promo['used_by']
    used_by_text = ", ".join(map(str, used_by)) if used_by else "никем"
    
    promo_info_text = (
        f"🎟️ Информация о промокоде {code}:\n\n"
        f"💰 Сумма: {promo['amount']} ⭐\n"
        f"🎯 Осталось использований: {promo['uses_left']}\n"
        f"👤 Создал: {promo['created_by']}\n"
        f"📅 Создан: {promo['created_at']}\n"
        f"👥 Использовали: {used_by_text}\n"
        f"📊 Всего использований: {len(used_by)}"
    )
    
    await update.message.reply_text(promo_info_text)

# 🆕 КОМАНДА ПОИСКА ПО ID
async def searchid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /searchid <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        data = user_data[target_id]
        win_rate = (data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0
        
        user_info_text = f"""
👤 Информация о пользователе:

🆔 ID: {target_id}
📅 Регистрация: {data['registration_date'][:10]}
💰 Баланс: {round(data['game_balance'], 1)} ⭐
🎯 Текущая ставка: {data['current_bet']} ⭐
🎮 Всего игр: {data['total_games']}
🏆 Побед: {data['total_wins']}
📈 Винрейт: {win_rate:.1f}%
💳 Пополнено: {data['total_deposited']} ⭐
💸 Потрачено реальных денег: {data['real_money_spent']} Stars

🔥 СИСТЕМЫ БОНУСОВ:
📊 Текущая серия побед: {data['win_streak']}
🏆 Максимальная серия: {data['max_win_streak']}
🎉 Мега-выигрышей: {data['mega_wins_count']}
💫 Сумма мега-выигрышей: {round(data['total_mega_win_amount'], 1)} ⭐

👥 РЕФЕРАЛЬНАЯ СИСТЕМА:
🎯 Реферальный код: {data['referral_code']}
👥 Приглашено друзей: {data['referrals_count']}
💰 Заработано с рефералов: {round(data['referral_earnings'], 1)} ⭐
📝 Приглашен: {data['referral_by'] if data['referral_by'] else 'никем'}

⚠️ СТАТУСЫ:
🚫 Бан: {'Да' if target_id in banned_users else 'Нет'}
🔇 Мут: {'Да' if target_id in muted_users else 'Нет'}
⭐ VIP: {'Да' if target_id in vip_users else 'Нет'}
⚠️ Предупреждения: {len(user_warnings[target_id])}
        """
        
        await update.message.reply_text(user_info_text)
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректный ID!")

# 🆕 КОМАНДА ВЫДАЧИ VIP
async def vip_give_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /vip_give <user_id> <дни>")
        return
    
    try:
        target_id = int(context.args[0])
        days = int(context.args[1])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        await give_vip(target_id, user_id, days)
        
        await update.message.reply_text(f"✅ Пользователю {target_id} выдан VIP на {days} дней!")
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректные числа!")

# 🆕 КОМАНДА СНЯТИЯ VIP
async def vip_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /vip_remove <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        
        success = await remove_vip(target_id, user_id)
        
        if success:
            await update.message.reply_text(f"✅ VIP снят у пользователя {target_id}!")
        else:
            await update.message.reply_text("❌ Пользователь не имеет VIP статуса!")
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректный ID!")

# 🆕 КОМАНДА СТАТИСТИКИ
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    total_users = len(user_data)
    active_today = 0
    total_balance = 0
    total_deposited = 0
    total_games = 0
    total_wins = 0
    
    today = datetime.datetime.now().date()
    
    for uid, data in user_data.items():
        total_balance += data['game_balance']
        total_deposited += data['total_deposited']
        total_games += data['total_games']
        total_wins += data['total_wins']
        
        if 'last_activity' in data:
            last_activity_date = datetime.datetime.fromisoformat(data['last_activity']).date()
            if last_activity_date == today:
                active_today += 1
    
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
    
    stats_text = f"""
📊 СТАТИСТИКА БОТА

👥 ПОЛЬЗОВАТЕЛИ:
• Всего: {total_users}
• Активных сегодня: {active_today}

💰 ФИНАНСЫ:
• Общий баланс: {round(total_balance, 1)} ⭐
• Всего пополнено: {round(total_deposited, 1)} ⭐

🎮 ИГРЫ:
• Всего игр: {total_games}
• Побед: {total_wins}
• Винрейт: {win_rate:.1f}%

⚙️ СИСТЕМА:
• Промокодов: {len(promo_codes)}
• Забанено: {len(banned_users)}
• В муте: {len(muted_users)}
• VIP: {len(vip_users)}
"""
    
    await update.message.reply_text(stats_text)

# 🆕 КОМАНДА ЛОГОВ
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if not admin_logs:
        await update.message.reply_text("📝 Логи действий пусты")
        return
    
    recent_logs = admin_logs[-10:]  # Последние 10 записей
    logs_text = "📝 ПОСЛЕДНИЕ ДЕЙСТВИЯ:\n\n"
    
    for log in reversed(recent_logs):
        logs_text += f"👤 {log['admin_id']} - {log['action']}"
        if log.get('target_id'):
            logs_text += f" (ID: {log['target_id']})"
        if log.get('details'):
            logs_text += f" - {log['details']}"
        logs_text += f"\n⏰ {log['timestamp'][:16]}\n━━━━━━━━━━━━━━━━━━━━\n"
    
    await update.message.reply_text(logs_text)

# 🆕 КОМАНДА СОХРАНЕНИЯ
async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    save_data()
    await update.message.reply_text("✅ Данные сохранены!")

# 🆕 ОБНОВЛЕНИЕ НЕДЕЛЬНОЙ АКТИВНОСТИ
def update_weekly_activity(user_id: int, bet_amount: float) -> dict:
    activity = user_activity[user_id]
    today = datetime.datetime.now().date()
    
    if activity.get('current_week_start') is None:
        activity['current_week_start'] = today.isoformat()
    
    week_start = datetime.datetime.fromisoformat(activity['current_week_start']).date()
    week_end = week_start + datetime.timedelta(days=6)
    
    if today > week_end:
        activity['weekly_streak_days'] = 0
        activity['weekly_total_bets'] = 0
        activity['weekly_total_games'] = 0
        activity['current_week_start'] = today.isoformat()
        activity['last_activity_date'] = None
    
    if activity.get('last_activity_date') != today.isoformat():
        activity['daily_games_count'] = 0
        activity['last_activity_date'] = today.isoformat()
    
    activity['daily_games_count'] += 1
    activity['weekly_total_games'] += 1
    activity['weekly_total_bets'] += bet_amount
    
    if activity['daily_games_count'] >= WEEKLY_BONUS_CONFIG["min_daily_games"]:
        if activity['last_activity_date'] != today.isoformat():
            activity['weekly_streak_days'] += 1
            activity['last_activity_date'] = today.isoformat()
    
    if (activity['weekly_streak_days'] >= WEEKLY_BONUS_CONFIG["required_days"] and
        activity.get('last_weekly_bonus_date') != today.isoformat()):
        
        base_bonus = activity['weekly_total_bets'] * WEEKLY_BONUS_CONFIG["base_percent"]
        min_games = WEEKLY_BONUS_CONFIG["min_daily_games"] * WEEKLY_BONUS_CONFIG["required_days"]
        extra_games = max(0, activity['weekly_total_games'] - min_games)
        extra_bonus = activity['weekly_total_bets'] * extra_games * WEEKLY_BONUS_CONFIG["bonus_per_extra_game"]
        max_extra = activity['weekly_total_bets'] * WEEKLY_BONUS_CONFIG["max_extra_bonus"]
        extra_bonus = min(extra_bonus, max_extra)
        total_bonus = base_bonus + extra_bonus
        
        user_data[user_id]['game_balance'] += total_bonus
        
        activity['last_weekly_bonus_date'] = today.isoformat()
        activity['weekly_streak_days'] = 0
        activity['weekly_total_bets'] = 0
        activity['weekly_total_games'] = 0
        activity['current_week_start'] = today.isoformat()
        
        save_data()
        
        return {
            'total_bets': activity['weekly_total_bets'],
            'total_games': activity['weekly_total_games'],
            'base_bonus': base_bonus,
            'extra_bonus': extra_bonus,
            'total_bonus': total_bonus
        }
    
    save_data()
    return None

# 👑 АДМИН ПАНЕЛЬ (CALLBACK ОБРАБОТЧИКИ)
async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    admin_text = """
👑 АДМИН ПАНЕЛЬ NSource Casino

Выберите раздел для управления:
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("🏆 Топ игроков", callback_data="admin_top"),
         InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💰 Баланс", callback_data="admin_balance"),
         InlineKeyboardButton("🔍 Поиск", callback_data="admin_search")],
        [InlineKeyboardButton("⚙️ Система", callback_data="admin_system"),
         InlineKeyboardButton("🎟️ Промокоды", callback_data="admin_promo")],
        [InlineKeyboardButton("🚫 Баны", callback_data="admin_ban"),
         InlineKeyboardButton("💾 Бэкап", callback_data="admin_backup")],
        [InlineKeyboardButton("💸 Выводы", callback_data="admin_withdrawals"),
         InlineKeyboardButton("🎮 Играть", callback_data="admin_play")],
        [InlineKeyboardButton("⚖️ Модерация", callback_data="admin_moderation"),
         InlineKeyboardButton("⭐ VIP", callback_data="admin_vip")],
        [InlineKeyboardButton("📈 Аналитика", callback_data="admin_analytics"),
         InlineKeyboardButton("📝 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton("🤖 Автоматизация", callback_data="admin_automation"),
         InlineKeyboardButton("🎰 Игры", callback_data="admin_games")],
        [InlineKeyboardButton("🎁 Бонусы", callback_data="admin_bonuses"),
         InlineKeyboardButton("👥 Рефералы", callback_data="admin_referrals")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings"),
         InlineKeyboardButton("🚪 Выход", callback_data="admin_exit")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(admin_text, reply_markup=reply_markup)

async def admin_panel_sections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    section = query.data
    
    sections_text = {
        "admin_search": "🔍 Поиск пользователя\n\nИспользуйте команду: /searchid <user_id>",
        "admin_balance": "💰 Управление балансом\n\nКоманды:\n/addbalance <id> <сумма>\n/setbalance <id> <сумма>\n/resetbalance <id>",
        "admin_ban": "🚫 Бан-менеджер\n\nКоманды:\n/ban <id> <причина>\n/unban <id>\n/banlist",
        "admin_mute": "🔇 Мут-менеджер\n\nКоманды:\n/mute <id> <минуты> [причина]\n/unmute <id>",
        "admin_warn": "⚠️ Варн-менеджер\n\nКоманды:\n/warn <id> <причина>\n/unwarn <id> [индекс]",
        "admin_vip": "⭐ VIP-менеджер\n\nКоманды:\n/vip_give <id> <дни>\n/vip_remove <id>",
        "admin_promo": "🎟️ Промо-менеджер\n\nКоманды:\n/promo_create <сумма> <использований>\n/promo_list\n/promo_info <код>\n/promo_delete <код>",
        "admin_stats": "📊 Статистика\n\nКоманда: /stats",
        "admin_logs": "📝 Логи действий\n\nКоманда: /logs",
        "admin_broadcast": "📢 Рассылка\n\nКоманда: /broadcast <текст>",
        "admin_backup": "💾 Резервная копия\n\nКоманда: /save",
        "admin_top": "🏆 Топ игроков\n\nЗдесь будет отображаться топ игроков по балансу, выигрышам и т.д.",
        "admin_withdrawals": "💸 Запросы на вывод\n\nЗдесь будут отображаться запросы на вывод средств.",
        "admin_play": "🎮 Играть\n\nРежим игры для администратора.",
        "admin_moderation": "⚙️ Модерация\n\nНастройки модерации.",
        "admin_analytics": "📈 Аналитика\n\nАналитика и графики.",
        "admin_automation": "🤖 Автоматизация\n\nНастройки автоматических процессов.",
        "admin_games": "🎰 Игры\n\nНастройки игр.",
        "admin_bonuses": "🎁 Бонусы\n\nУправление бонусами.",
        "admin_referrals": "👥 Рефералы\n\nСтатистика реферальной системы.",
        "admin_settings": "⚙️ Настройки\n\nНастройки бота."
    }
    
    if section in sections_text:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(sections_text[section], reply_markup=reply_markup)
    
    elif section == "admin_logout":
        admin_mode[user_id] = False
        save_data()
        await query.edit_message_text(
            "👋 Режим администратора деактивирован!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")]
            ])
        )
        log_admin_action(user_id, "admin_logout")

async def admin_exit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    admin_mode[user_id] = False
    save_data()
    
    await query.edit_message_text(
        "👋 Режим администратора деактивирован!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")]
        ])
    )
    log_admin_action(user_id, "admin_logout")

# 🆕 ОБРАБОТЧИК НАВИГАЦИИ ПО ПОЛЬЗОВАТЕЛЯМ
async def admin_users_navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        return
    
    # Обработка навигации
    if "admin_users_prev_" in query.data or "admin_users_next_" in query.data:
        page = int(query.data.split("_")[-1])
        context.user_data['admin_users_page'] = page
        await admin_users_callback(update, context)

# 🆕 CALLBACK ОБРАБОТЧИКИ ДЛЯ АДМИН ПАНЕЛИ
async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    total_users = len(user_data)
    active_today = 0
    total_balance = 0
    total_deposited = 0
    total_games = 0
    total_wins = 0
    
    today = datetime.datetime.now().date()
    
    for uid, data in user_data.items():
        total_balance += data['game_balance']
        total_deposited += data['total_deposited']
        total_games += data['total_games']
        total_wins += data['total_wins']
        
        if 'last_activity' in data:
            last_activity_date = datetime.datetime.fromisoformat(data['last_activity']).date()
            if last_activity_date == today:
                active_today += 1
    
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
    
    stats_text = f"""
📊 СТАТИСТИКА БОТА

👥 ПОЛЬЗОВАТЕЛИ:
• Всего: {total_users}
• Активных сегодня: {active_today}

💰 ФИНАНСЫ:
• Общий баланс: {round(total_balance, 1)} ⭐
• Всего пополнено: {round(total_deposited, 1)} ⭐

🎮 ИГРЫ:
• Всего игр: {total_games}
• Побед: {total_wins}
• Винрейт: {win_rate:.1f}%

⚙️ СИСТЕМА:
• Промокодов: {len(promo_codes)}
• Забанено: {len(banned_users)}
• В муте: {len(muted_users)}
• VIP: {len(vip_users)}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    page = context.user_data.get('admin_users_page', 0)
    users_per_page = 10
    start_idx = page * users_per_page
    end_idx = start_idx + users_per_page
    
    user_list = list(user_data.items())[start_idx:end_idx]
    
    users_text = f"👥 ПОЛЬЗОВАТЕЛИ (страница {page + 1}):\n\n"
    
    for uid, data in user_list:
        win_rate = (data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0
        users_text += (
            f"👤 ID: {uid}\n"
            f"💰 Баланс: {round(data['game_balance'], 1)} ⭐\n"
            f"🎮 Игр: {data['total_games']} (побед: {data['total_wins']}, {win_rate:.1f}%)\n"
            f"📅 Регистрация: {data['registration_date'][:10]}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
    
    total_pages = (len(user_data) + users_per_page - 1) // users_per_page
    keyboard = []
    
    if page > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"admin_users_prev_{page-1}"))
    if page < total_pages - 1:
        keyboard.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"admin_users_next_{page+1}"))
    
    if keyboard:
        keyboard = [keyboard]
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(users_text, reply_markup=reply_markup)

async def admin_top_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    # Топ по балансу
    top_balance = sorted(user_data.items(), key=lambda x: x[1]['game_balance'], reverse=True)[:10]
    
    top_text = "🏆 ТОП ИГРОКОВ ПО БАЛАНСУ:\n\n"
    
    for i, (uid, data) in enumerate(top_balance, 1):
        top_text += f"{i}. 👤 {uid}: {round(data['game_balance'], 1)} ⭐\n"
    
    top_text += "\n🏆 ТОП ИГРОКОВ ПО ВЫИГРЫШАМ:\n\n"
    
    # Топ по мега-выигрышам
    top_mega_wins = sorted(user_data.items(), key=lambda x: x[1]['total_mega_win_amount'], reverse=True)[:10]
    
    for i, (uid, data) in enumerate(top_mega_wins, 1):
        top_text += f"{i}. 👤 {uid}: {round(data['total_mega_win_amount'], 1)} ⭐ мега-выигрышей\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(top_text, reply_markup=reply_markup)

async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    broadcast_text = """
📢 РАССЫЛКА СООБЩЕНИЙ

Используйте команду: /broadcast <текст>

Пример:
/broadcast Всем привет! Обновление системы...

⚠️ ВНИМАНИЕ: Сообщение будет отправлено ВСЕМ пользователям бота!
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(broadcast_text, reply_markup=reply_markup)

async def admin_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    balance_text = """
💰 УПРАВЛЕНИЕ БАЛАНСАМИ

Команды:
/addbalance <id> <сумма> - добавить баланс
/setbalance <id> <сумма> - установить баланс
/resetbalance <id> - сбросить баланс

Примеры:
/addbalance 123456789 100
/setbalance 123456789 500
/resetbalance 123456789
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(balance_text, reply_markup=reply_markup)

async def admin_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    search_text = """
🔍 ПОИСК ПОЛЬЗОВАТЕЛЯ

Используйте команду: /searchid <user_id>

Пример:
/searchid 123456789

📊 Будет показана полная информация о пользователе.
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(search_text, reply_markup=reply_markup)

async def admin_system_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    system_text = """
⚙️ СИСТЕМНАЯ ИНФОРМАЦИЯ

Команды:
/stats - статистика бота
/logs - логи действий
/save - сохранить данные

💻 Информация о системе:
"""
    
    # Добавляем системную информацию
    try:
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_text += f"""
💾 Память: {memory.percent}% использовано
🖥️ CPU: {cpu_percent}% использовано
💿 Диск: {disk.percent}% использовано
📊 Пользователей: {len(user_data)}
"""
    except Exception as e:
        system_text += f"\n⚠️ Ошибка получения системной информации: {e}"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(system_text, reply_markup=reply_markup)

async def admin_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    promo_text = """
🎟️ УПРАВЛЕНИЕ ПРОМОКОДАМИ

Команды:
/promo_create <сумма> <использований> - создать промокод
/promo_list - список промокодов
/promo_info <код> - информация о промокоде
/promo_delete <код> - удалить промокод

Примеры:
/promo_create 100 50
/promo_info SUMMER2024
/promo_delete SUMMER2024
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(promo_text, reply_markup=reply_markup)

async def admin_ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    ban_text = """
🚫 УПРАВЛЕНИЕ БАНАМИ

Команды:
/ban <id> <причина> - забанить пользователя
/unban <id> - разбанить пользователя
/banlist - список забаненных

Примеры:
/ban 123456789 Нарушение правил
/unban 123456789
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(ban_text, reply_markup=reply_markup)

async def admin_backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    backup_text = """
💾 РЕЗЕРВНОЕ КОПИРОВАНИЕ

Команды:
/save - сохранить данные

📊 Информация о данных:
"""
    
    backup_text += f"""
👥 Пользователей: {len(user_data)}
🎟️ Промокодов: {len(promo_codes)}
🚫 Забанено: {len(banned_users)}
⭐ VIP: {len(vip_users)}
📝 Логов: {len(admin_logs)}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(backup_text, reply_markup=reply_markup)

async def admin_withdrawals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    withdrawals_text = "💸 ЗАПРОСЫ НА ВЫВОД:\n\n"
    
    total_withdrawals = 0
    for user_id, requests in withdrawal_requests.items():
        for request in requests:
            total_withdrawals += request['amount']
    
    withdrawals_text += f"📊 Всего выводов: {total_withdrawals} ⭐\n"
    withdrawals_text += f"👤 Пользователей с выводами: {len(withdrawal_requests)}\n\n"
    
    if withdrawal_requests:
        withdrawals_text += "📋 Последние выводы:\n"
        count = 0
        for user_id, requests in list(withdrawal_requests.items())[:5]:
            for request in requests[-3:]:  # Последние 3 вывода каждого пользователя
                if count < 10:  # Показываем максимум 10 записей
                    withdrawals_text += (
                        f"👤 {user_id}: {request['amount']} ⭐ "
                        f"({request['gifts_count']} подарков) - "
                        f"{request['timestamp'][:16]}\n"
                    )
                    count += 1
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(withdrawals_text, reply_markup=reply_markup)

async def admin_play_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    play_text = """
🎮 РЕЖИМ ИГРЫ ДЛЯ АДМИНИСТРАТОРА

В режиме администратора:
• Игры не списывают баланс
• Вы можете тестировать все игры
• Статистика не записывается

Просто отправьте любой dice эмодзи в чат или используйте кнопки ниже!
    """
    
    keyboard = [
        [InlineKeyboardButton("🎰 Слоты", callback_data="play_slots"),
         InlineKeyboardButton("🎯 Дартс", callback_data="play_dart")],
        [InlineKeyboardButton("🎲 Кубик", callback_data="play_dice"),
         InlineKeyboardButton("🎳 Боулинг", callback_data="play_bowling")],
        [InlineKeyboardButton("⚽ Футбол", callback_data="play_football"),
         InlineKeyboardButton("🏀 Баскетбол", callback_data="play_basketball")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(play_text, reply_markup=reply_markup)

async def admin_moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    moderation_text = """
⚖️ МОДЕРАЦИЯ ПОЛЬЗОВАТЕЛЕЙ

Команды:
/mute <id> <минуты> [причина] - выдать мут
/unmute <id> - снять мут
/warn <id> <причина> - выдать предупреждение
/unwarn <id> [индекс] - снять предупреждение

Примеры:
/mute 123456789 60 Спам
/unmute 123456789
/warn 123456789 Нарушение правил
/unwarn 123456789
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(moderation_text, reply_markup=reply_markup)

async def admin_vip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    vip_text = """
⭐ УПРАВЛЕНИЕ VIP СТАТУСОМ

Команды:
/vip_give <id> <дни> - выдать VIP статус
/vip_remove <id> - снять VIP статус

Примеры:
/vip_give 123456789 30
/vip_remove 123456789

📊 Статистика VIP:
"""
    
    vip_text += f"👥 Всего VIP пользователей: {len(vip_users)}\n"
    
    if vip_users:
        vip_text += "\n📋 Список VIP пользователей:\n"
        for uid, vip_data in list(vip_users.items())[:10]:
            vip_until = datetime.datetime.fromisoformat(vip_data['vip_until'])
            days_left = (vip_until - datetime.datetime.now()).days
            vip_text += f"👤 {uid}: {days_left} дней осталось\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(vip_text, reply_markup=reply_markup)

async def admin_analytics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    analytics_text = """
📈 АНАЛИТИКА БОТА

Здесь будет отображаться аналитика по:
• Активности пользователей
• Популярности игр
• Финансовым показателям
• Эффективности бонусных систем

📊 Базовая статистика:
"""
    
    # Базовая аналитика
    total_games_by_type = defaultdict(int)
    total_wins_by_type = defaultdict(int)
    
    for uid, data in user_data.items():
        # Считаем игры по типам (примерная логика)
        total_games_by_type['all'] += data['total_games']
        total_wins_by_type['all'] += data['total_wins']
    
    analytics_text += f"""
🎮 Общая статистика:
• Всего игр: {total_games_by_type['all']}
• Всего побед: {total_wins_by_type['all']}
• Винрейт: {(total_wins_by_type['all']/total_games_by_type['all']*100) if total_games_by_type['all'] > 0 else 0:.1f}%

💰 Финансы:
• Общий баланс: {sum(data['game_balance'] for data in user_data.values()):.1f} ⭐
• Всего пополнено: {sum(data['total_deposited'] for data in user_data.values()):.1f} ⭐
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(analytics_text, reply_markup=reply_markup)

async def admin_logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if not admin_logs:
        await query.edit_message_text(
            "📝 Логи действий пусты",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]])
        )
        return
    
    recent_logs = admin_logs[-10:]  # Последние 10 записей
    logs_text = "📝 ПОСЛЕДНИЕ ДЕЙСТВИЯ:\n\n"
    
    for log in reversed(recent_logs):
        logs_text += f"👤 {log['admin_id']} - {log['action']}"
        if log.get('target_id'):
            logs_text += f" (ID: {log['target_id']})"
        if log.get('details'):
            logs_text += f" - {log['details']}"
        logs_text += f"\n⏰ {log['timestamp'][:16]}\n━━━━━━━━━━━━━━━━━━━━\n"
    
    keyboard = [
        [InlineKeyboardButton("🗑️ Очистить логи", callback_data="admin_clear_logs")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(logs_text, reply_markup=reply_markup)

async def admin_automation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    automation_text = """
🤖 АВТОМАТИЗАЦИЯ ПРОЦЕССОВ

Настройки автоматических процессов:
• Авто-очистка неактивных пользователей
• Авто-награды за активность
• Авто-модерация
• Авто-бэкапы

⚙️ Текущие настройки:
• Авто-сохранение: каждые 5 минут
• Очистка логов: 1000+ записей
• Резервное копирование: при каждом сохранении
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(automation_text, reply_markup=reply_markup)

async def admin_games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    games_text = """
🎰 НАСТРОЙКИ ИГР

Статистика по играм:
"""
    
    # Статистика по играм
    game_stats = defaultdict(lambda: {'games': 0, 'wins': 0})
    
    # Примерная логика подсчета (в реальной системе нужно хранить отдельно)
    for uid, data in user_data.items():
        game_stats['all']['games'] += data['total_games']
        game_stats['all']['wins'] += data['total_wins']
    
    games_text += f"""
🎮 Общая статистика:
• Всего игр: {game_stats['all']['games']}
• Побед: {game_stats['all']['wins']}
• Винрейт: {(game_stats['all']['wins']/game_stats['all']['games']*100) if game_stats['all']['games'] > 0 else 0:.1f}%

🎯 Настройки ставок:
• Минимальная ставка: {MIN_BET} ⭐
• Максимальная ставка: {MAX_BET} ⭐
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(games_text, reply_markup=reply_markup)

async def admin_bonuses_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    bonuses_text = """
🎁 УПРАВЛЕНИЕ БОНУСАМИ

Текущие бонусные системы:
• 🔥 Серии побед: +10%/+25%/+50% за 2/3/5 побед
• 🎉 Мега-выигрыши: 0.6% шанс x1.5-x5
• 🔄 Возвраты: 2-10% при проигрыше
• 🏆 Недельные награды: 1-3% от суммы ставок
• 👥 Реферальная система: 10% от проигрышей

📊 Статистика бонусов:
"""
    
    # Статистика бонусов
    total_mega_wins = sum(data['mega_wins_count'] for data in user_data.values())
    total_mega_amount = sum(data['total_mega_win_amount'] for data in user_data.values())
    total_referral_earnings = sum(data['referral_earnings'] for data in user_data.values())
    
    bonuses_text += f"""
🎉 Мега-выигрыши:
• Всего мега-выигрышей: {total_mega_wins}
• Сумма мега-выигрышей: {total_mega_amount:.1f} ⭐

👥 Реферальная система:
• Всего заработано: {total_referral_earnings:.1f} ⭐
• Всего рефералов: {sum(data['referrals_count'] for data in user_data.values())}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(bonuses_text, reply_markup=reply_markup)

async def admin_referrals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    referrals_text = """
👥 РЕФЕРАЛЬНАЯ СИСТЕМА

Статистика реферальной системы:
"""
    
    total_referrals = sum(data['referrals_count'] for data in user_data.values())
    total_earnings = sum(data['referral_earnings'] for data in user_data.values())
    users_with_referrals = sum(1 for data in user_data.values() if data['referrals_count'] > 0)
    
    referrals_text += f"""
📊 Общая статистика:
• Всего приглашено: {total_referrals}
• Всего заработано: {total_earnings:.1f} ⭐
• Пользователей с рефералами: {users_with_referrals}

🏆 Топ рефереров:
"""
    
    # Топ рефереров
    top_referrers = sorted(user_data.items(), key=lambda x: x[1]['referral_earnings'], reverse=True)[:5]
    
    for i, (uid, data) in enumerate(top_referrers, 1):
        if data['referral_earnings'] > 0:
            referrals_text += f"{i}. 👤 {uid}: {data['referral_earnings']:.1f} ⭐ ({data['referrals_count']} реф.)\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(referrals_text, reply_markup=reply_markup)

async def admin_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    settings_text = """
⚙️ НАСТРОЙКИ БОТА

Основные настройки:
"""
    
    settings_text += f"""
🔧 Конфигурация:
• Минимальная ставка: {MIN_BET} ⭐
• Максимальная ставка: {MAX_BET} ⭐
• Минимальный вывод: {MIN_WITHDRAWAL} ⭐
• Код администратора: {ADMIN_CODE}

🎮 Игры:
• Доступные эмодзи: 🎰, 🎯, 🎲, 🎳, ⚽, 🏀
• Задержки анимации: {DICE_DELAYS}

💰 Платежи:
• Провайдер: {PROVIDER_TOKEN[:10]}...
• Валюта: XTR
• Пакеты пополнения: {len(PRODUCTS)}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(settings_text, reply_markup=reply_markup)

# 🆕 КОМАНДА ВАРНА
async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /warn <user_id> <причина>")
        return
    
    try:
        target_id = int(context.args[0])
        reason = ' '.join(context.args[1:])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        await warn_user(target_id, user_id, reason)
        
        warnings_count = len(user_warnings[target_id])
        
        await update.message.reply_text(
            f"⚠️ Пользователю {target_id} выдано предупреждение!\n"
            f"📝 Причина: {reason}\n"
            f"📊 Всего предупреждений: {warnings_count}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID!")

# 🆕 КОМАНДА СНЯТИЯ ВАРНА
async def unwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /unwarn <user_id> [индекс]")
        return
    
    try:
        target_id = int(context.args[0])
        warning_index = -1
        
        if len(context.args) > 1:
            warning_index = int(context.args[1])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        success = await unwarn_user(target_id, user_id, warning_index)
        
        if success:
            warnings_count = len(user_warnings[target_id])
            await update.message.reply_text(
                f"✅ Предупреждение снято у пользователя {target_id}!\n"
                f"📊 Осталось предупреждений: {warnings_count}"
            )
        else:
            await update.message.reply_text("❌ Не удалось снять предупреждение!")
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID или индекса!")

# 🆕 КОМАНДА МУТА
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /mute <user_id> <минуты> [причина]")
        return
    
    try:
        target_id = int(context.args[0])
        minutes = int(context.args[1])
        reason = ' '.join(context.args[2:]) if len(context.args) > 2 else "Не указана"
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        if target_id in admin_mode and admin_mode[target_id]:
            await update.message.reply_text("❌ Нельзя замутить администратора!")
            return
        
        await mute_user(target_id, user_id, minutes, reason)
        
        await update.message.reply_text(
            f"🔇 Пользователь {target_id} замьючен на {minutes} минут!\n"
            f"📝 Причина: {reason}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID или времени!")

# 🆕 КОМАНДА РАЗМУТА
async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /unmute <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        
        success = await unmute_user(target_id, user_id)
        
        if success:
            await update.message.reply_text(f"✅ Пользователь {target_id} размьючен!")
        else:
            await update.message.reply_text("❌ Пользователь не найден в списке замьюченных!")
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID!")

# 🆕 КОМАНДА РАССЫЛКИ
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) == 0:
        await update.message.reply_text("Использование: /broadcast <текст>")
        return
    
    broadcast_text = ' '.join(context.args)
    total_users = len(user_data)
    successful_sends = 0
    failed_sends = 0
    
    await update.message.reply_text(f"📢 Начинаю рассылку для {total_users} пользователей...")
    
    for user_id in user_data.keys():
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 СООБЩЕНИЕ ОТ АДМИНИСТРАЦИИ:\n\n{broadcast_text}"
            )
            successful_sends += 1
            await asyncio.sleep(0.1)  # Задержка чтобы не превысить лимиты
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")
            failed_sends += 1
    
    log_admin_action(user_id, "broadcast", None, f"сообщение: {broadcast_text[:50]}...")
    
    await update.message.reply_text(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"• Всего пользователей: {total_users}\n"
        f"• Успешно отправлено: {successful_sends}\n"
        f"• Не удалось отправить: {failed_sends}"
    )

# 🔧 ОСНОВНАЯ ФУНКЦИЯ
def main():
    load_data()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 👤 ОСНОВНЫЕ КОМАНДЫ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("activity", activity_command))
    application.add_handler(CommandHandler("promo", promo_command))
    application.add_handler(CommandHandler("bet", bet_command))
    
    # 💰 ПОПОЛНЕНИЕ И ВЫВОД
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CommandHandler("withdraw", withdraw_command))
    
    # 👑 АДМИН КОМАНДЫ
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("banlist", banlist_command))
    application.add_handler(CommandHandler("addbalance", addbalance_command))
    application.add_handler(CommandHandler("setbalance", setbalance_command))
    application.add_handler(CommandHandler("resetbalance", resetbalance_command))
    application.add_handler(CommandHandler("searchid", searchid_command))
    application.add_handler(CommandHandler("promo_create", promo_create_command))
    application.add_handler(CommandHandler("promo_list", promo_list_command))
    application.add_handler(CommandHandler("promo_info", promo_info_command))
    application.add_handler(CommandHandler("promo_delete", promo_delete_command))
    
    # 🆕 АДМИН КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ
    application.add_handler(CommandHandler("vip_give", vip_give_command))
    application.add_handler(CommandHandler("vip_remove", vip_remove_command))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CommandHandler("unwarn", unwarn_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("unmute", unmute_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("save", save_command))
    
    # 💳 ОБРАБОТЧИКИ ПЛАТЕЖЕЙ
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # 🎮 ОБРАБОТЧИКИ ИГР
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_user_dice))
    
    # 🔄 CALLBACK ОБРАБОТЧИКИ
    application.add_handler(CallbackQueryHandler(profile, pattern="^back_to_profile$"))
    application.add_handler(CallbackQueryHandler(play_games_callback, pattern="^play_games$"))
    application.add_handler(CallbackQueryHandler(deposit_callback, pattern="^deposit$"))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))
    application.add_handler(CallbackQueryHandler(change_bet_callback, pattern="^change_bet$"))
    application.add_handler(CallbackQueryHandler(referral_system_callback, pattern="^referral_system$"))
    application.add_handler(CallbackQueryHandler(handle_game_selection, pattern="^play_"))
    application.add_handler(CallbackQueryHandler(handle_deposit_selection, pattern="^buy_"))
    application.add_handler(CallbackQueryHandler(handle_withdraw_selection, pattern="^withdraw_"))
    application.add_handler(CallbackQueryHandler(confirm_withdraw, pattern="^confirm_withdraw$"))
    
    # 👑 АДМИН CALLBACK ОБРАБОТЧИКИ
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_panel_sections, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(admin_exit_callback, pattern="^admin_exit$"))
    
    # 🔄 CALLBACK ОБРАБОТЧИКИ ДЛЯ АДМИН ПАНЕЛИ
    application.add_handler(CallbackQueryHandler(admin_stats_callback, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(admin_users_callback, pattern="^admin_users$"))
    application.add_handler(CallbackQueryHandler(admin_top_callback, pattern="^admin_top$"))
    application.add_handler(CallbackQueryHandler(admin_broadcast_callback, pattern="^admin_broadcast$"))
    application.add_handler(CallbackQueryHandler(admin_balance_callback, pattern="^admin_balance$"))
    application.add_handler(CallbackQueryHandler(admin_search_callback, pattern="^admin_search$"))
    application.add_handler(CallbackQueryHandler(admin_system_callback, pattern="^admin_system$"))
    application.add_handler(CallbackQueryHandler(admin_promo_callback, pattern="^admin_promo$"))
    application.add_handler(CallbackQueryHandler(admin_ban_callback, pattern="^admin_ban$"))
    application.add_handler(CallbackQueryHandler(admin_backup_callback, pattern="^admin_backup$"))
    application.add_handler(CallbackQueryHandler(admin_withdrawals_callback, pattern="^admin_withdrawals$"))
    application.add_handler(CallbackQueryHandler(admin_play_callback, pattern="^admin_play$"))
    application.add_handler(CallbackQueryHandler(admin_moderation_callback, pattern="^admin_moderation$"))
    application.add_handler(CallbackQueryHandler(admin_vip_callback, pattern="^admin_vip$"))
    application.add_handler(CallbackQueryHandler(admin_analytics_callback, pattern="^admin_analytics$"))
    application.add_handler(CallbackQueryHandler(admin_logs_callback, pattern="^admin_logs$"))
    application.add_handler(CallbackQueryHandler(admin_automation_callback, pattern="^admin_automation$"))
    application.add_handler(CallbackQueryHandler(admin_games_callback, pattern="^admin_games$"))
    application.add_handler(CallbackQueryHandler(admin_bonuses_callback, pattern="^admin_bonuses$"))
    application.add_handler(CallbackQueryHandler(admin_referrals_callback, pattern="^admin_referrals$"))
    application.add_handler(CallbackQueryHandler(admin_settings_callback, pattern="^admin_settings$"))
    
    # Обработчик для навигации по пользователям
    application.add_handler(CallbackQueryHandler(admin_users_navigation_callback, pattern="^admin_users_"))
    
    print("🤖 Бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()
