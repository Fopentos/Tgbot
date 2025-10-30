import os
import json
import random
import datetime
import asyncio
import psutil
from collections import defaultdict
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, PreCheckoutQueryHandler, ConversationHandler
from telegram.error import BadRequest

# 🔧 КОНФИГУРАЦИЯ
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8378526693:AAFOwAb6pVp1GOE0tXZN4PDLFnD_TTT1djg")
PROVIDER_TOKEN = os.environ.get("PROVIDER_TOKEN", "TEST_PROVIDER_TOKEN")
ADMIN_CODE = os.environ.get("ADMIN_CODE", "1337")

# 🎯 МИНИМАЛЬНАЯ И МАКСИМАЛЬНАЯ СТАВКА
MIN_BET = 1
MAX_BET = 100000

# 💰 КОНФИГУРАЦИЯ КАСТОМНОГО ПОПОЛНЕНИЯ
CUSTOM_DEPOSIT_CONFIG = {
    "min_amount": 1,        # Минимальная сумма
    "max_amount": 1000000,  # Максимальная сумма  
    "step": 1              # Шаг суммы
}

# Состояния для FSM кастомного пополнения
WAITING_CUSTOM_AMOUNT, CONFIRM_CUSTOM_AMOUNT = range(2)

# ⏱️ ВРЕМЯ АНИМАЦИИ ДЛЯ КАЖДОЙ ИГРЫ (в секундах)
DICE_DELAYS = {
    "🎰": 1.2,  # Слоты - самая долгая анимация
    "🎯": 2.2,  # Дартс
    "🎲": 2.2,  # Кубик
    "🎳": 3.3,  # Боулинг
    "⚽": 3.3,  # Футбол
    "🏀": 3.3   # Баскетбол
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
MIN_WITHDRAWAL = 15  # Изменено с 100 на 15 для системы подарков

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
        "СЛАБЫЙ УДАР": 0.0,
        "УДАР МИМО": 0.0,
        "БЛИЗКИЙ УДАР": 0.33,
        "ХОРОШИЙ ГОЛ": 1.66,
        "СУПЕРГОЛ": 1.66
    },
    "🏀": {
        "ПРОМАХ": 0.0,
        "КАСАТЕЛЬНО": 0.0,
        "ОТСКОК": 0.0,
        "ТРЕХОЧКОВЫЙ": 2.0,
        "СЛЭМ-ДАНК": 2.0
    }
}

# 🎰 СИСТЕМА СЕРИЙ ПОБЕД (ОБНОВЛЕННАЯ)
WIN_STREAK_BONUSES = {
    2: {"multiplier": 1.1, "message": "🔥 Серия из 2 побед! Бонус +10% к выигрышу!"},
    3: {"multiplier": 1.25, "message": "🔥🔥 Серия из 3 побед! Бонус +25% к выигрышу!"},
    4: {"multiplier": 1.45, "message": "🔥🔥🔥 Серия из 4 побед! Бонус +45% к выигрышу!"},
    5: {"multiplier": 1.6, "message": "🔥🔥🔥🔥 Серия из 5 побед! Бонус +60% к выигрышу!"},
    6: {"multiplier": 1.85, "message": "🔥🔥🔥🔥🔥 СЕРИЯ ИЗ 6 ПОБЕД! МЕГА БОНУС +85% к выигрышу!"}
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
            43: {"win": True, "base_prize": BASE_PRIZES["🎰"]["ТРИ ЛИМОНЫ"], "message": "🎰 ТРИ ЛИМОНА! Выигрыш: {prize} ⭐"},
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

# 🎁 СИСТЕМА ВЫВОДА ЧЕРЕЗ ПОДАРКИ
class GiftCalculator:
    def __init__(self):
        self.available_gifts = [100, 50, 25, 15]
        self.available_gifts.sort(reverse=True)
    
    def can_withdraw_amount(self, amount: int) -> bool:
        """Проверяет, можно ли разложить сумму на доступные номиналы"""
        return self._find_combination(amount) is not None
    
    def find_best_combination(self, amount: int) -> dict:
        """Находит оптимальную комбинацию подарков"""
        combination = self._find_combination(amount)
        if combination is None:
            # Если точной комбинации нет, найдем ближайшую большую
            for diff in range(1, 100):
                test_amount = amount + diff
                combination = self._find_combination(test_amount)
                if combination is not None:
                    return combination
        return combination or {}
    
    def _find_combination(self, amount: int) -> dict:
        """Рекурсивно ищет комбинацию подарков"""
        if amount == 0:
            return {}
        if amount < 0:
            return None
        
        for gift in self.available_gifts:
            if amount >= gift:
                remaining = amount - gift
                result = self._find_combination(remaining)
                if result is not None:
                    result = result.copy()
                    result[gift] = result.get(gift, 0) + 1
                    return result
        return None
    
    def get_suggested_amounts(self, desired_amount: int, count: int = 3) -> list:
        """Возвращает ближайшие доступные суммы"""
        suggestions = []
        for diff in range(0, 100):
            for direction in [1, -1]:
                test_amount = desired_amount + diff * direction
                if test_amount >= 15 and self.can_withdraw_amount(test_amount):
                    if test_amount not in suggestions:
                        suggestions.append(test_amount)
                    if len(suggestions) >= count:
                        return sorted(suggestions)
        return sorted(suggestions)

# Инициализация калькулятора подарков
gift_calculator = GiftCalculator()

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

# 🎰 СИСТЕМА СЕРИЙ ПОБЕД, МЕГА-ВЫИГРЫШЕЙ И ВОЗВРАТОВ (ИСПРАВЛЕННАЯ)
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
    
    # 🔥 СИСТЕМА СЕРИЙ ПОБЕД (ОБНОВЛЕННАЯ)
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
🎰 MetaSlots Casino

Добро пожаловать в казино!

Доступные игры (ставка от 1 до 100000 ⭐):
🎰 Слоты - 64 комбинации, 4 выигрышных (5-20x ставки)
🎰 Слоты 777 - только джекпот 777 (50x ставки)
🎯 Дартс - победа на 6 (3x ставки)
🎲 Кубик - победа на 6 (3x ставки)
🎳 Боулинг - победа на 6 (3x ставки)
⚽ Футбол
🏀 Баскетбол

💰 Пополнение: 1:1
1 реальная звезда = 1 ⭐

🎁 Вывод: от 15⭐ через систему подарков (15, 25, 50, 100⭐)

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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🎰 MetaSlots Casino - Помощь

Основные команды:
/start - начать работу с ботом
/profile - посмотреть свой профиль
/help - показать это сообщение
/activity - посмотреть активность и недельные награды
/promo <код> - активировать промокод
/bet <сумма> - изменить ставку
/deposit - пополнить баланс
/withdraw - вывести средства

🎮 Игры:
Просто отправьте любой из этих эмодзи в чат:
🎰 - Слоты (4 выигрышных комбинации)
🎯 - Дартс (победа на 6)
🎲 - Кубик (победа на 6) 
🎳 - Боулинг (победа на 6)
⚽ - Футбол
🏀 - Баскетбол

💰 Вывод средств:
Минимальная сумма: 15⭐
Вывод через систему подарков (15, 25, 50, 100⭐)
Сумма должна раскладываться на доступные номиналы

Для начала игры просто отправьте эмодзи игры в чат!
    """
    await update.message.reply_text(help_text)

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
    
    # Кнопка админ панели только для администраторов
    if admin_mode.get(user_id, False):
        keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(profile_text, reply_markup=reply_markup)
        except BadRequest as e:
            if "Message is not modified" in str(e):
                # Игнорируем ошибку, если сообщение не изменилось
                pass
            else:
                raise e
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
    try:
        await query.edit_message_text(referral_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

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

# 🎮 ОБРАБОТКА РЕЗУЛЬТАТОВ ИГР (ИСПРАВЛЕННАЯ)
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
    
    # Форматируем сообщение с призом
    formatted_message = result_config["message"].format(prize=final_prize)
    
    # ИСПРАВЛЕНИЕ: ВОЗВРАТ ПРИ ПРОИГРЫШЕ ДОЛЖЕН НАЧИСЛЯТЬСЯ НА БАЛАНС
    if is_win or base_prize_amount > 0 or final_prize > 0:
        user_data[user_id]['game_balance'] += final_prize
        if is_win:
            user_data[user_id]['total_wins'] += 1
        
        result_text = (
            f"{formatted_message}\n\n"
            f"💎 Текущий баланс: {round(user_data[user_id]['game_balance'], 1)} ⭐\n"
            f"📊 (Списано: {cost} ⭐ + Выигрыш: {final_prize} ⭐)"
        )
        
        if bonus_messages:
            result_text += "\n\n" + "\n".join(bonus_messages)
    else:
        # Для проигрышных исходов с возвратом
        if final_prize > 0:
            user_data[user_id]['game_balance'] += final_prize
            result_text = (
                f"{formatted_message}\n\n"
                f"💎 Текущий баланс: {round(user_data[user_id]['game_balance'], 1)} ⭐\n"
                f"📊 Списано: {cost} ⭐ + Возврат: {final_prize} ⭐"
            )
        else:
            result_text = (
                f"{formatted_message}\n\n"
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

# 💸 СИСТЕМА ВЫВОДА СРЕДСТВ (ОБНОВЛЕННАЯ С ПОДАРКАМИ)
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

🎁 Система вывода через подарки:
• Доступные номиналы: 15, 25, 50, 100 ⭐
• Сумма должна раскладываться на эти номиналы
• Вы получаете подарки соответствующего номинала

💡 Примеры доступных сумм:
• 15⭐ = 1×15⭐
• 25⭐ = 1×25⭐  
• 30⭐ = 2×15⭐
• 40⭐ = 1×25⭐ + 1×15⭐
• 50⭐ = 1×50⭐
• 65⭐ = 1×50⭐ + 1×15⭐
• 75⭐ = 1×50⭐ + 1×25⭐
• 100⭐ = 1×100⭐

Введите сумму для вывода:
    """
    
    await update.message.reply_text(withdraw_text)
    
    # Устанавливаем состояние для ожидания ввода суммы
    context.user_data['awaiting_withdrawal'] = True
    return WAITING_WITHDRAW_AMOUNT

async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.user_data.get('awaiting_withdrawal'):
        return ConversationHandler.END
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await update.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return ConversationHandler.END
    
    try:
        amount = int(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректное число!")
        return WAITING_WITHDRAW_AMOUNT
    
    balance = round(user_data[user_id]['game_balance'], 1)
    
    if amount < MIN_WITHDRAWAL:
        await update.message.reply_text(
            f"❌ Минимальная сумма вывода: {MIN_WITHDRAWAL} ⭐\n\n"
            f"Пожалуйста, введите сумму от {MIN_WITHDRAWAL} ⭐:"
        )
        return WAITING_WITHDRAW_AMOUNT
        
    if amount > balance:
        await update.message.reply_text(
            f"❌ Недостаточно средств!\n\n"
            f"💰 Ваш баланс: {balance} ⭐\n"
            f"💸 Запрошено: {amount} ⭐\n\n"
            f"Введите меньшую сумму:"
        )
        return WAITING_WITHDRAW_AMOUNT
    
    # Проверяем, можно ли разложить сумму на подарки
    if not gift_calculator.can_withdraw_amount(amount):
        suggestions = gift_calculator.get_suggested_amounts(amount, 3)
        suggestions_text = "\n".join([f"• {s}⭐" for s in suggestions])
        
        await update.message.reply_text(
            f"❌ Сумма {amount}⭐ не доступна для вывода!\n\n"
            f"💡 Ближайшие доступные суммы:\n{suggestions_text}\n\n"
            f"Пожалуйста, введите одну из доступных сумм:"
        )
        return WAITING_WITHDRAW_AMOUNT
    
    # Находим комбинацию подарков
    combination = gift_calculator.find_best_combination(amount)
    combination_text = " + ".join([f"{count}×{value}⭐" for value, count in combination.items()])
    gift_count = sum(combination.values())
    
    context.user_data['withdraw_amount'] = amount
    context.user_data['withdraw_combination'] = combination
    
    confirm_text = f"""
✅ Подтверждение вывода

💸 Сумма вывода: {amount} ⭐
🎁 Количество подарков: {gift_count}
📦 Комбинация: {combination_text}

💰 Баланс до списания: {balance} ⭐
💰 Баланс после списания: {round(balance - amount, 1)} ⭐

После подтверждения с вашего счета будет списано {amount} ⭐ и вы получите {gift_count} подарков!
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить вывод", callback_data="confirm_withdraw")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_withdraw")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(confirm_text, reply_markup=reply_markup)
    
    return CONFIRM_WITHDRAW

async def confirm_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    amount = context.user_data.get('withdraw_amount')
    combination = context.user_data.get('withdraw_combination')
    
    if not user_id or not amount or not combination:
        await query.edit_message_text("❌ Ошибка: данные сессии устарели")
        return ConversationHandler.END
    
    if user_data[user_id]['game_balance'] < amount:
        await query.edit_message_text("❌ Недостаточно средств!")
        return ConversationHandler.END
    
    # Списываем средства
    user_data[user_id]['game_balance'] -= amount
    
    combination_text = " + ".join([f"{count}×{value}⭐" for value, count in combination.items()])
    gift_count = sum(combination.values())
    
    withdrawal_request = {
        'user_id': user_id,
        'amount': amount,
        'gifts_combination': combination,
        'gift_count': gift_count,
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
🎁 Отправлено подарков: {gift_count}
📦 Комбинация: {combination_text}
💰 Текущий баланс: {round(user_data[user_id]['game_balance'], 1)} ⭐

💫 Ваши подарки уже отправлены! Проверьте раздел "Подарки" в Telegram.

Благодарим за игру! 🎰
    """
    
    keyboard = [
        [InlineKeyboardButton("🎮 Продолжить играть", callback_data="play_games")],
        [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(success_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e
    
    print(f"💰 ВЫВОД: Пользователь {user_id} вывел {amount} ⭐, отправлено {gift_count} подарков: {combination}")
    
    # Сбрасываем состояние
    context.user_data.pop('awaiting_withdrawal', None)
    context.user_data.pop('withdraw_amount', None)
    context.user_data.pop('withdraw_combination', None)
    
    return ConversationHandler.END

async def cancel_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text(
            "❌ Вывод отменен.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 Попробовать снова", callback_data="withdraw")],
                [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")]
            ])
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e
    
    # Сбрасываем состояние
    context.user_data.pop('awaiting_withdrawal', None)
    context.user_data.pop('withdraw_amount', None)
    context.user_data.pop('withdraw_combination', None)
    
    return ConversationHandler.END

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
        try:
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
        except BadRequest as e:
            if "Message is not modified" in str(e):
                pass
            else:
                raise e
        return
    
    withdraw_text = f"""
💸 Вывод средств

💰 Ваш баланс: {balance} ⭐
💸 Минимальная сумма вывода: {MIN_WITHDRAWAL} ⭐

🎁 Система вывода через подарки:
• Доступные номиналы: 15, 25, 50, 100 ⭐
• Сумма должна раскладываться на эти номиналы
• Вы получаете подарки соответствующего номинала

💡 Примеры доступных сумм:
• 15⭐ = 1×15⭐
• 25⭐ = 1×25⭐  
• 30⭐ = 2×15⭐
• 40⭐ = 1×25⭐ + 1×15⭐
• 50⭐ = 1×50⭐
• 65⭐ = 1×50⭐ + 1×15⭐
• 75⭐ = 1×50⭐ + 1×25⭐
• 100⭐ = 1×100⭐

Введите сумму для вывода:
    """
    
    await query.edit_message_text(withdraw_text)
    
    # Устанавливаем состояние для ожидания ввода суммы
    context.user_data['awaiting_withdrawal'] = True
    
    return WAITING_WITHDRAW_AMOUNT

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

# 💰 СИСТЕМА ПОПОЛНЕНИЯ С КАСТОМНЫМИ СУММАМИ (ОБНОВЛЕННАЯ)
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
    
    # Добавляем кнопку для кастомного пополнения
    keyboard.append([InlineKeyboardButton("💎 Ввести свою сумму", callback_data="custom_deposit")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(deposit_text, reply_markup=reply_markup)
        except BadRequest as e:
            if "Message is not modified" in str(e):
                pass
            else:
                raise e
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
    
    # Добавляем кнопку для кастомного пополнения
    keyboard.append([InlineKeyboardButton("💎 Ввести свою сумму", callback_data="custom_deposit")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(deposit_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

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
        start_parameter="metaslots_casino"
    )

# 🆕 ФУНКЦИИ ДЛЯ КАСТОМНОГО ПОПОЛНЕНИЯ
async def custom_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    deposit_text = f"""
💎 ПОПОЛНЕНИЕ ПРОИЗВОЛЬНОЙ СУММЫ

💰 Диапазон пополнения: {CUSTOM_DEPOSIT_CONFIG['min_amount']} - {CUSTOM_DEPOSIT_CONFIG['max_amount']} ⭐
💫 Курс: 1 реальная звезда = 1 ⭐

📝 Введите сумму, на которую хотите пополнить баланс:
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data="deposit")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(deposit_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e
    
    return WAITING_CUSTOM_AMOUNT

async def handle_custom_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await update.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return ConversationHandler.END
    
    try:
        amount = int(update.message.text)
        
        if amount < CUSTOM_DEPOSIT_CONFIG['min_amount']:
            await update.message.reply_text(
                f"❌ Минимальная сумма пополнения: {CUSTOM_DEPOSIT_CONFIG['min_amount']} ⭐\n\n"
                f"Пожалуйста, введите сумму от {CUSTOM_DEPOSIT_CONFIG['min_amount']} до {CUSTOM_DEPOSIT_CONFIG['max_amount']} ⭐:"
            )
            return WAITING_CUSTOM_AMOUNT
            
        if amount > CUSTOM_DEPOSIT_CONFIG['max_amount']:
            await update.message.reply_text(
                f"❌ Максимальная сумма пополнения: {CUSTOM_DEPOSIT_CONFIG['max_amount']} ⭐\n\n"
                f"Пожалуйста, введите сумму от {CUSTOM_DEPOSIT_CONFIG['min_amount']} до {CUSTOM_DEPOSIT_CONFIG['max_amount']} ⭐:"
            )
            return WAITING_CUSTOM_AMOUNT
        
        current_balance = user_data[user_id]['game_balance']
        new_balance = current_balance + amount
        
        confirm_text = f"""
✅ ПОДТВЕРЖДЕНИЕ ПОПОЛНЕНИЯ

💰 Сумма пополнения: {amount} ⭐
💎 Текущий баланс: {round(current_balance, 1)} ⭐
💫 Баланс после пополнения: {round(new_balance, 1)} ⭐

💳 Стоимость: {amount} Telegram Stars
        """
        
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить", callback_data=f"confirm_custom_{amount}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_custom_deposit")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(confirm_text, reply_markup=reply_markup)
        
        context.user_data['custom_amount'] = amount
        return CONFIRM_CUSTOM_AMOUNT
        
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите корректное число!\n\n"
            f"Диапазон: {CUSTOM_DEPOSIT_CONFIG['min_amount']} - {CUSTOM_DEPOSIT_CONFIG['max_amount']} ⭐"
        )
        return WAITING_CUSTOM_AMOUNT

async def confirm_custom_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    amount = int(query.data.replace("confirm_custom_", ""))
    
    # Создаем динамический продукт для кастомной суммы
    product_key = f"pack_custom_{amount}"
    product_title = f"{amount} ⭐"
    product_description = f"Пополнение баланса на {amount} ⭐"
    
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title=product_title,
        description=product_description,
        payload=product_key,
        provider_token=PROVIDER_TOKEN,
        currency="XTR",
        prices=[LabeledPrice(product_title, amount)],
        start_parameter="metaslots_casino_custom"
    )
    
    return ConversationHandler.END

async def cancel_custom_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text(
            "❌ Пополнение отменено.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 К выбору суммы", callback_data="deposit")]
            ])
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e
    
    return ConversationHandler.END

async def cancel_custom_deposit_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Пополнение отменено.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 К выбору суммы", callback_data="deposit")]
        ])
    )
    
    return ConversationHandler.END

# 💳 ОБРАБОТЧИКИ ПЛАТЕЖЕЙ (ОБНОВЛЕННЫЕ)
async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    product_key = payment.invoice_payload
    
    # Обработка кастомных платежей
    if product_key.startswith("pack_custom_"):
        amount = int(product_key.replace("pack_custom_", ""))
        credits = amount
        product_title = f"{amount} ⭐"
    else:
        # Обработка стандартных продуктов
        product = PRODUCTS[product_key]
        amount = product["price"]
        credits = product["credits"]
        product_title = product["title"]
    
    user_data[user_id]['game_balance'] += credits
    user_data[user_id]['total_deposited'] += credits
    user_data[user_id]['real_money_spent'] += amount
    
    save_data()
    
    await update.message.reply_text(
        f"✅ Платеж успешен!\n\n"
        f"💳 Оплачено: {amount} Stars\n"
        f"💎 Зачислено: {credits} ⭐\n"
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

Выберите игру или просто отправь любой dice эмодзи в чат!
    """
    
    keyboard = [
        [InlineKeyboardButton("🎰 Слоты", callback_data="play_slots")],
        [InlineKeyboardButton("🎰 Слоты 777 (только джекпот)", callback_data="play_slots777")],
        [InlineKeyboardButton("🎯 Дартс", callback_data="play_dart")],
        [InlineKeyboardButton("🎲 Кубик", callback_data="play_dice")],
        [InlineKeyboardButton("🎳 Боулинг", callback_data="play_bowling")],
        [InlineKeyboardButton("⚽ Футбол", callback_data="play_football")],
        [InlineKeyboardButton("🏀 Баскетбол", callback_data="play_basketball")],
        [InlineKeyboardButton("🎯 Изменить ставку", callback_data="change_bet")],
        [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton("📊 Личный кабинет", callback_data="back_to_profile")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(games_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

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
        try:
            await query.edit_message_text("✅ Режим изменен на Слоты 777! Теперь все ваши игры в слоты будут в режиме 777 (только джекпот 777).")
        except BadRequest as e:
            if "Message is not modified" in str(e):
                pass
            else:
                raise e
        return
    elif game_type == 'slots':
        user_data[user_id]['slots_mode'] = 'normal'
        try:
            await query.edit_message_text("✅ Режим изменен на обычные Слоты! Теперь все ваши игры в слоты будут в обычном режиме.")
        except BadRequest as e:
            if "Message is not modified" in str(e):
                pass
            else:
                raise e
        return
    
    # СПИСАНИЕ БАЛАНСА ПЕРЕД ИГРОЙ
    if user_data[user_id]['game_balance'] < current_bet and not admin_mode.get(user_id, False):
        try:
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
        except BadRequest as e:
            if "Message is not modified" in str(e):
                pass
            else:
                raise e
        return
    
    # СПИСАНИЕ БАЛАНСА (исправлено)
    if not admin_mode.get(user_id, False):
        user_data[user_id]['game_balance'] -= current_bet
        save_data()  # Сохраняем сразу после списания
    
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
    
    # СПИСАНИЕ БАЛАНСА ПЕРЕД ИГРОЙ
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
    
    # СПИСАНИЕ БАЛАНСА (исправлено)
    if not admin_mode.get(user_id, False):
        user_data[user_id]['game_balance'] -= cost
        save_data()  # Сохраняем сразу после списания
    
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
    try:
        await query.edit_message_text(bet_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# 🔙 CALLBACK ДЛА ВОЗВРАТА В ПРОФИЛЬ
async def back_to_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await profile(update, context)

# 👑 АДМИН СИСТЕМА (РАСШИРЕННАЯ)
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

# 🆕 РАСШИРЕННАЯ АДМИН ПАНЕЛЬ
async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    admin_text = """
👑 АДМИН ПАНЕЛЬ MetaSlots

📊 Статистика - просмотр общей статистики бота
👥 Пользователи - управление пользователями
🛡️ Модерация - баны, муты, предупреждения
💰 Финансы - управление платежами и выводами
🎮 Игры - настройка игрового процесса
🎁 Промо - управление промокодами
⚙️ Система - системные настройки и мониторинг
📋 Логи - просмотр действий администраторов
📚 Справка - список всех админ-команд
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("🛡️ Модерация", callback_data="admin_moderation"),
         InlineKeyboardButton("💰 Финансы", callback_data="admin_finance")],
        [InlineKeyboardButton("🎮 Игры", callback_data="admin_games"),
         InlineKeyboardButton("🎁 Промо", callback_data="admin_promo")],
        [InlineKeyboardButton("⚙️ Система", callback_data="admin_system"),
         InlineKeyboardButton("📋 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton("📚 Справка", callback_data="admin_help"),
         InlineKeyboardButton("🔙 Назад", callback_data="back_to_profile")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(admin_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# 🆕 АДМИН СТАТИСТИКА
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
• Всего пользователей: {total_users}
• Активных сегодня: {active_today}
• Новых за сегодня: {sum(1 for data in user_data.values() if datetime.datetime.fromisoformat(data['registration_date']).date() == today)}

💰 ФИНАНСЫ:
• Общий баланс: {round(total_balance, 1)} ⭐
• Всего пополнено: {round(total_deposited, 1)} ⭐
• Средний депозит: {round(total_deposited/total_users, 1) if total_users > 0 else 0} ⭐

🎮 ИГРОВАЯ АКТИВНОСТЬ:
• Всего игр: {total_games}
• Побед: {total_wins}
• Винрейт: {win_rate:.1f}%
• Средняя ставка: {round(sum(data['current_bet'] for data in user_data.values())/total_users, 1) if total_users > 0 else 0} ⭐

⚙️ СИСТЕМНЫЕ ПОКАЗАТЕЛИ:
• Промокодов: {len(promo_codes)}
• Забанено: {len(banned_users)}
• В муте: {len(muted_users)}
• VIP пользователей: {len(vip_users)}
• Реферальных связей: {sum(1 for data in user_data.values() if data['referral_by'])}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 В админ панель", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(stats_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# 🆕 АДМИН УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    users_text = """
👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ

🔍 Поиск и управление пользователями

Используйте команды:
/addbalance <user_id> <amount> - добавить баланс
/setbalance <user_id> <amount> - установить баланс
/ban <user_id> <причина> - забанить пользователя
/unban <user_id> - разбанить пользователя
/mute <user_id> <минуты> <причина> - замутить
/unmute <user_id> - размутить
/warn <user_id> <причина> - выдать предупреждение
/unwarn <user_id> [индекс] - снять предупреждение
/vip <user_id> <дни> - выдать VIP
/unvip <user_id> - снять VIP
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 В админ панель", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(users_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# 🆕 АДМИН МОДЕРАЦИЯ
async def admin_moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    moderation_text = """
🛡️ СИСТЕМА МОДЕРАЦИИ

Основные команды модерации:

🚫 Бан система:
/ban <user_id> <причина> - забанить пользователя
/unban <user_id> - разбанить пользователя
/banlist - список забаненных

🔇 Мут система:
/mute <user_id> <минуты> <причина> - замутить
/unmute <user_id> - размутить

⚠️ Предупреждения:
/warn <user_id> <причина> - выдать предупреждение
/unwarn <user_id> [индекс] - снять предупреждение

⭐ VIP система:
/vip <user_id> <дни> - выдать VIP статус
/unvip <user_id> - снять VIP статус
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 В админ панель", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(moderation_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# 🆕 АДМИН ФИНАНСЫ
async def admin_finance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    total_deposits = sum(data['total_deposited'] for data in user_data.values())
    total_withdrawals = sum(sum(req['amount'] for req in requests) for requests in withdrawal_requests.values())
    total_balance = sum(data['game_balance'] for data in user_data.values())
    
    finance_text = f"""
💰 ФИНАНСОВАЯ СИСТЕМА

📊 Финансовая статистика:

• Общие депозиты: {round(total_deposits, 1)} ⭐
• Общие выводы: {round(total_withdrawals, 1)} ⭐
• Текущий баланс системы: {round(total_balance, 1)} ⭐
• Чистая прибыль: {round(total_deposits - total_withdrawals, 1)} ⭐

💸 Управление балансами:

/addbalance <user_id> <amount> - добавить баланс
/setbalance <user_id> <amount> - установить баланс
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 В админ панель", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(finance_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# 🆕 АДМИН ИГРЫ
async def admin_games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    games_text = """
🎮 УПРАВЛЕНИЕ ИГРАМИ

Настройки игр находятся в конфигурации.

Текущие настройки:
• Минимальная ставка: 1 ⭐
• Максимальная ставка: 100000 ⭐
• Минимальный вывод: 15 ⭐

Для изменения настроек требуется редактирование кода.
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 В админ панель", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(games_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# 🆕 АДМИН ПРОМО СИСТЕМА
async def admin_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    promo_text = f"""
🎁 ПРОМО СИСТЕМА

🎟️ Управление промо-акциями:

Основные команды:
/promo_create <amount> <uses> [name] - создать промокод
/promo_list - список промокодов
/promo_delete <код> - удалить промокод

📊 Статистика:
• Активных промокодов: {len(promo_codes)}
• Всего использований: {sum(len(promo['used_by']) for promo in promo_codes.values())}
• Общая сумма: {sum(promo['amount'] * len(promo['used_by']) for promo in promo_codes.values())} ⭐
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 В админ панель", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(promo_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# 🆕 АДМИН СИСТЕМНЫЕ НАСТРОЙКИ
async def admin_system_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    system_text = """
⚙️ СИСТЕМНЫЕ НАСТРОЙКИ

🛠️ Управление системой:

Основные команды:
/stats - общая статистика
/system_info - информация о системе
/backup - создать резервную копию
/restart - перезагрузить бота
/clear_logs - очистить логи
/reset_weekly - сбросить недельные данные
    """
    
    # Информация о системе
    process = psutil.Process()
    memory_info = process.memory_info()
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    
    system_text += f"""

📊 Состояние системы:
• Память процесса: {memory_info.rss // 1024 // 1024} MB
• CPU: {cpu_percent}%
• Память системы: {memory_percent}%
• Время работы: {datetime.datetime.now() - datetime.datetime.fromtimestamp(process.create_time())}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 В админ панель", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(system_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# 🆕 АДМИН ЛОГИ
async def admin_logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if not admin_logs:
        logs_text = "📝 Логи действий пусты"
    else:
        recent_logs = admin_logs[-10:]
        logs_text = "📝 ПОСЛЕДНИЕ ДЕЙСТВИЯ:\n\n"
        
        for log in reversed(recent_logs):
            logs_text += f"👤 {log['admin_id']} - {log['action']}"
            if log.get('target_id'):
                logs_text += f" (ID: {log['target_id']})"
            if log.get('details'):
                logs_text += f" - {log['details']}"
            logs_text += f"\n⏰ {log['timestamp'][:16]}\n━━━━━━━━━━━━━━━━━━━━\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_logs"),
         InlineKeyboardButton("🗑️ Очистить логи", callback_data="admin_clear_logs")],
        [InlineKeyboardButton("🔙 В админ панель", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(logs_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# 🆕 АДМИН СПРАВКА
async def admin_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    help_text = """
📚 СПРАВКА ПО АДМИН КОМАНДАМ

👥 Управление пользователями:
/addbalance <user_id> <amount> - добавить баланс
/setbalance <user_id> <amount> - установить баланс

🛡️ Модерация:
/ban <user_id> <причина> - забанить
/unban <user_id> - разбанить
/banlist - список забаненных
/mute <user_id> <минуты> <причина> - замутить
/unmute <user_id> - размутить
/warn <user_id> <причина> - предупреждение
/unwarn <user_id> [индекс] - снять предупреждение
/vip <user_id> <дни> - выдать VIP
/unvip <user_id> - снять VIP

🎁 Промо система:
/promo_create <amount> <uses> [name] - создать промокод
/promo_list - список промокодов
/promo_delete <код> - удалить промокод

⚙️ Система:
/stats - статистика
/system_info - информация о системе
/backup - резервная копия
/restart - перезагрузка
/clear_logs - очистить логи
/reset_weekly - сбросить недельные данные
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 В админ панель", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await query.edit_message_text(help_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

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
            f"✅ Пользователь {target_id} забанен!\n"
            f"📝 Причина: {reason}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя!")

# 🆕 КОМАНДА РАЗБАНИВАНИЯ
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /unban <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        
        success = await unban_user(target_id, user_id)
        
        if success:
            await update.message.reply_text(f"✅ Пользователь {target_id} разбанен!")
        else:
            await update.message.reply_text("❌ Пользователь не забанен!")
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя!")

# 🆕 КОМАНДА СПИСКА БАНОВ
async def banlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if not banned_users:
        await update.message.reply_text("📋 Список забаненных пуст")
        return
    
    banlist_text = "📋 ЗАБАНЕННЫЕ ПОЛЬЗОВАТЕЛИ:\n\n"
    
    for banned_id, ban_data in list(banned_users.items())[:20]:
        banlist_text += f"👤 ID: {banned_id}\n"
        banlist_text += f"📝 Причина: {ban_data['reason']}\n"
        banlist_text += f"🕒 Дата: {ban_data['banned_at'][:16]}\n"
        banlist_text += f"👮 Админ: {ban_data['banned_by']}\n"
        banlist_text += "━━━━━━━━━━━━━━━━━━━━\n"
    
    if len(banned_users) > 20:
        banlist_text += f"\n... и еще {len(banned_users) - 20} пользователей"
    
    await update.message.reply_text(banlist_text)

# 🆕 КОМАНДА МУТА
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text("Использование: /mute <user_id> <минуты> <причина>")
        return
    
    try:
        target_id = int(context.args[0])
        minutes = int(context.args[1])
        reason = ' '.join(context.args[2:])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        if target_id in admin_mode and admin_mode[target_id]:
            await update.message.reply_text("❌ Нельзя замутить администратора!")
            return
        
        await mute_user(target_id, user_id, minutes, reason)
        
        await update.message.reply_text(
            f"✅ Пользователь {target_id} замучен на {minutes} минут!\n"
            f"📝 Причина: {reason}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат данных!")

# 🆕 КОМАНДА РАЗМУТА
async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /unmute <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        
        success = await unmute_user(target_id, user_id)
        
        if success:
            await update.message.reply_text(f"✅ Пользователь {target_id} размучен!")
        else:
            await update.message.reply_text("❌ Пользователь не в муте!")
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя!")

# 🆕 КОМАНДА ПРЕДУПРЕЖДЕНИЯ
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
            f"⚠️ Пользователь {target_id} получил предупреждение!\n"
            f"📝 Причина: {reason}\n"
            f"📊 Всего предупреждений: {warnings_count}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя!")

# 🆕 КОМАНДА СНЯТИЯ ПРЕДУПРЕЖДЕНИЯ
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
        
        if not user_warnings[target_id]:
            await update.message.reply_text("❌ У пользователя нет предупреждений!")
            return
        
        success = await unwarn_user(target_id, user_id, warning_index)
        
        if success:
            remaining_warnings = len(user_warnings[target_id])
            await update.message.reply_text(
                f"✅ Предупреждение снято!\n"
                f"📊 Осталось предупреждений: {remaining_warnings}"
            )
        else:
            await update.message.reply_text("❌ Не удалось снять предупреждение!")
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат данных!")

# 🆕 КОМАНДА ВЫДАЧИ VIP
async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /vip <user_id> <дни>")
        return
    
    try:
        target_id = int(context.args[0])
        days = int(context.args[1])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        await give_vip(target_id, user_id, days)
        
        await update.message.reply_text(
            f"⭐ Пользователь {target_id} получил VIP статус на {days} дней!"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат данных!")

# 🆕 КОМАНДА СНЯТИЯ VIP
async def unvip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /unvip <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        
        success = await remove_vip(target_id, user_id)
        
        if success:
            await update.message.reply_text(f"✅ VIP статус снят у пользователя {target_id}!")
        else:
            await update.message.reply_text("❌ У пользователя нет VIP статуса!")
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя!")

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
            f"✅ Баланс пользователя {target_id} пополнен на {amount} ⭐!\n"
            f"💰 Новый баланс: {round(user_data[target_id]['game_balance'], 1)} ⭐"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат данных!")

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
            f"✅ Баланс пользователя {target_id} установлен на {amount} ⭐!\n"
            f"💰 Старый баланс: {round(old_balance, 1)} ⭐\n"
            f"💰 Новый баланс: {round(amount, 1)} ⭐"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат данных!")

# 🆕 КОМАНДА СОЗДАНИЯ ПРОМОКОДА
async def promo_create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /promo_create <amount> <uses> [name]")
        return
    
    try:
        amount = int(context.args[0])
        uses = int(context.args[1])
        name = context.args[2] if len(context.args) > 2 else ""
        
        if amount < PROMO_CONFIG["min_amount"] or amount > PROMO_CONFIG["max_amount"]:
            await update.message.reply_text(
                f"❌ Сумма промокода должна быть от {PROMO_CONFIG['min_amount']} до {PROMO_CONFIG['max_amount']} ⭐"
            )
            return
        
        if uses < 1:
            await update.message.reply_text("❌ Количество использований должно быть больше 0")
            return
        
        if len(promo_codes) >= PROMO_CONFIG["max_active_promos"]:
            await update.message.reply_text(
                f"❌ Достигнуто максимальное количество активных промокодов ({PROMO_CONFIG['max_active_promos']})"
            )
            return
        
        code = create_promo_code(amount, uses, user_id)
        
        log_admin_action(user_id, "create_promo", details=f"код: {code}, сумма: {amount}, использований: {uses}")
        
        await update.message.reply_text(
            f"✅ Промокод создан!\n\n"
            f"🎟️ Код: {code}\n"
            f"💰 Сумма: {amount} ⭐\n"
            f"🔄 Использований: {uses}\n"
            f"📝 Название: {name if name else 'Не указано'}\n\n"
            f"💡 Пользователи могут активировать его командой /promo {code}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат данных!")

# 🆕 КОМАНДА СПИСКА ПРОМОКОДОВ
async def promo_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if not promo_codes:
        await update.message.reply_text("📋 Список промокодов пуст")
        return
    
    promo_list_text = "📋 АКТИВНЫЕ ПРОМОКОДЫ:\n\n"
    
    for code, promo_data in list(promo_codes.items())[:10]:
        promo_list_text += f"🎟️ {code}\n"
        promo_list_text += f"💰 Сумма: {promo_data['amount']} ⭐\n"
        promo_list_text += f"🔄 Использований: {len(promo_data['used_by'])}/{promo_data['uses_left'] + len(promo_data['used_by'])}\n"
        promo_list_text += f"👤 Создал: {promo_data['created_by']}\n"
        promo_list_text += f"📅 Дата: {promo_data['created_at'][:16]}\n"
        promo_list_text += "━━━━━━━━━━━━━━━━━━━━\n"
    
    if len(promo_codes) > 10:
        promo_list_text += f"\n... и еще {len(promo_codes) - 10} промокодов"
    
    await update.message.reply_text(promo_list_text)

# 🆕 КОМАНДА УДАЛЕНИЯ ПРОМОКОДА
async def promo_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /promo_delete <код>")
        return
    
    code = context.args[0].upper()
    
    if code not in promo_codes:
        await update.message.reply_text("❌ Промокод не найден!")
        return
    
    deleted_promo = promo_codes.pop(code)
    save_data()
    
    log_admin_action(user_id, "delete_promo", details=f"код: {code}, сумма: {deleted_promo['amount']}")
    
    await update.message.reply_text(
        f"✅ Промокод {code} удален!\n"
        f"💰 Сумма: {deleted_promo['amount']} ⭐\n"
        f"👤 Создал: {deleted_promo['created_by']}\n"
        f"🔄 Использован: {len(deleted_promo['used_by'])} раз"
    )

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
📊 ОБЩАЯ СТАТИСТИКА БОТА

👥 ПОЛЬЗОВАТЕЛИ:
• Всего: {total_users}
• Активных сегодня: {active_today}
• Новых за сегодня: {sum(1 for data in user_data.values() if datetime.datetime.fromisoformat(data['registration_date']).date() == today)}

💰 ФИНАНСЫ:
• Общий баланс: {round(total_balance, 1)} ⭐
• Всего пополнено: {round(total_deposited, 1)} ⭐
• Средний депозит: {round(total_deposited/total_users, 1) if total_users > 0 else 0} ⭐

🎮 ИГРОВАЯ АКТИВНОСТЬ:
• Всего игр: {total_games}
• Побед: {total_wins}
• Винрейт: {win_rate:.1f}%

⚙️ СИСТЕМНЫЕ ПОКАЗАТЕЛИ:
• Промокодов: {len(promo_codes)}
• Забанено: {len(banned_users)}
• В муте: {len(muted_users)}
• VIP пользователей: {len(vip_users)}
"""
    
    await update.message.reply_text(stats_text)

# 🆕 КОМАНДА ИНФОРМАЦИИ О СИСТЕМЕ
async def system_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    process = psutil.Process()
    memory_info = process.memory_info()
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/')
    
    system_text = f"""
⚙️ ИНФОРМАЦИЯ О СИСТЕМЕ

🖥️ ПРОЦЕСС:
• PID: {process.pid}
• Время запуска: {datetime.datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')}
• Время работы: {datetime.datetime.now() - datetime.datetime.fromtimestamp(process.create_time())}

💾 ПАМЯТЬ:
• Использовано процессом: {memory_info.rss // 1024 // 1024} MB
• Использование CPU: {cpu_percent}%
• Использование памяти системы: {memory_percent}%
• Свободно на диске: {disk_usage.free // 1024 // 1024} MB ({disk_usage.percent}% занято)

📊 ДАННЫЕ:
• Пользователей: {len(user_data)}
• Сессий: {len(user_sessions)}
• Промокодов: {len(promo_codes)}
• Логов действий: {len(admin_logs)}
"""
    
    await update.message.reply_text(system_text)

# 🆕 КОМАНДА ОЧИСТКИ ЛОГОВ
async def clear_logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    logs_count = len(admin_logs)
    admin_logs.clear()
    save_data()
    
    log_admin_action(user_id, "clear_logs", details=f"удалено записей: {logs_count}")
    
    await update.message.reply_text(f"✅ Логи очищены! Удалено записей: {logs_count}")

# 🆕 КОМАНДА СБРОСА НЕДЕЛЬНЫХ ДАННЫХ
async def reset_weekly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    reset_count = 0
    for uid, activity in user_activity.items():
        if activity['weekly_total_games'] > 0 or activity['weekly_total_bets'] > 0:
            activity.update({
                'weekly_streak_days': 0,
                'weekly_total_bets': 0,
                'weekly_total_games': 0,
                'daily_games_count': 0,
                'current_week_start': datetime.datetime.now().isoformat()
            })
            reset_count += 1
    
    save_data()
    
    log_admin_action(user_id, "reset_weekly", details=f"сброшено пользователей: {reset_count}")
    
    await update.message.reply_text(f"✅ Недельные данные сброшены! Обработано пользователей: {reset_count}")

# 🆕 ОБНОВЛЕНИЕ НЕДЕЛЬНОЙ АКТИВНОСТИ
def update_weekly_activity(user_id: int, bet_amount: float) -> dict:
    activity = user_activity[user_id]
    today = datetime.datetime.now().date()
    
    # Инициализация недели
    if activity.get('current_week_start') is None:
        activity['current_week_start'] = today.isoformat()
    
    week_start = datetime.datetime.fromisoformat(activity['current_week_start']).date()
    
    # Проверка смены недели
    if (today - week_start).days >= 7:
        # Начисляем недельную награду
        if activity['weekly_streak_days'] >= WEEKLY_BONUS_CONFIG["required_days"]:
            base_bonus = activity['weekly_total_bets'] * WEEKLY_BONUS_CONFIG["base_percent"]
            min_games = WEEKLY_BONUS_CONFIG["min_daily_games"] * WEEKLY_BONUS_CONFIG["required_days"]
            extra_games = max(0, activity['weekly_total_games'] - min_games)
            extra_bonus = activity['weekly_total_bets'] * extra_games * WEEKLY_BONUS_CONFIG["bonus_per_extra_game"]
            max_extra = activity['weekly_total_bets'] * WEEKLY_BONUS_CONFIG["max_extra_bonus"]
            extra_bonus = min(extra_bonus, max_extra)
            total_bonus = base_bonus + extra_bonus
            
            if total_bonus > 0:
                user_data[user_id]['game_balance'] += total_bonus
                save_data()
                
                bonus_data = {
                    'total_games': activity['weekly_total_games'],
                    'total_bets': activity['weekly_total_bets'],
                    'base_bonus': base_bonus,
                    'extra_bonus': extra_bonus,
                    'total_bonus': total_bonus
                }
        
        # Сброс данных недели
        activity.update({
            'weekly_streak_days': 0,
            'weekly_total_bets': 0,
            'weekly_total_games': 0,
            'current_week_start': today.isoformat()
        })
    
    # Обновление ежедневной активности
    if activity.get('last_activity_date') != today.isoformat():
        # Проверка серии дней
        if activity['last_activity_date']:
            last_date = datetime.datetime.fromisoformat(activity['last_activity_date']).date()
            if (today - last_date).days == 1:
                activity['weekly_streak_days'] += 1
            elif (today - last_date).days > 1:
                activity['weekly_streak_days'] = 1
        else:
            activity['weekly_streak_days'] = 1
        
        activity['last_activity_date'] = today.isoformat()
        activity['daily_games_count'] = 1
    else:
        activity['daily_games_count'] += 1
    
    # Обновление недельной статистики
    activity['weekly_total_games'] += 1
    activity['weekly_total_bets'] += bet_amount
    
    save_data()
    
    return None

# 🆕 ОБРАБОТЧИК ОЧИСТКИ ЛОГОВ
async def admin_clear_logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    logs_count = len(admin_logs)
    admin_logs.clear()
    save_data()
    
    log_admin_action(user_id, "clear_logs", details=f"удалено записей: {logs_count}")
    
    try:
        await query.edit_message_text(
            f"✅ Логи очищены! Удалено записей: {logs_count}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 В админ панель", callback_data="admin_panel")]
            ])
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise e

# 🚀 ЗАПУСК БОТА
def main():
    load_data()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 👤 ОСНОВНЫЕ КОМАНДЫ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("activity", activity_command))
    application.add_handler(CommandHandler("promo", promo_command))
    application.add_handler(CommandHandler("bet", bet_command))
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CommandHandler("withdraw", withdraw_command))
    
    # 👑 АДМИН КОМАНДЫ
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("banlist", banlist_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("unmute", unmute_command))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CommandHandler("unwarn", unwarn_command))
    application.add_handler(CommandHandler("vip", vip_command))
    application.add_handler(CommandHandler("unvip", unvip_command))
    application.add_handler(CommandHandler("addbalance", addbalance_command))
    application.add_handler(CommandHandler("setbalance", setbalance_command))
    application.add_handler(CommandHandler("promo_create", promo_create_command))
    application.add_handler(CommandHandler("promo_list", promo_list_command))
    application.add_handler(CommandHandler("promo_delete", promo_delete_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("system_info", system_info_command))
    application.add_handler(CommandHandler("clear_logs", clear_logs_command))
    application.add_handler(CommandHandler("reset_weekly", reset_weekly_command))
    
    # 💳 ОБРАБОТЧИКИ ПЛАТЕЖЕЙ
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # 🎮 ОБРАБОТЧИКИ ИГР
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_user_dice))
    
    # 🔄 CONVERSATION HANDLER ДЛЯ КАСТОМНОГО ПОПОЛНЕНИЯ
    deposit_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(custom_deposit_callback, pattern="^custom_deposit$")],
        states={
            WAITING_CUSTOM_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_amount_input)
            ],
            CONFIRM_CUSTOM_AMOUNT: [
                CallbackQueryHandler(confirm_custom_payment_callback, pattern="^confirm_custom_"),
                CallbackQueryHandler(cancel_custom_deposit, pattern="^cancel_custom_deposit$")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_custom_deposit_message),
            CallbackQueryHandler(cancel_custom_deposit, pattern="^cancel_custom_deposit$")
        ],
        map_to_parent={
            ConversationHandler.END: "END"
        }
    )
    application.add_handler(deposit_conv_handler)
    
    # 🔄 CONVERSATION HANDLER ДЛЯ ВЫВОДА СРЕДСТВ
    withdraw_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"),
            CommandHandler("withdraw", withdraw_command)
        ],
        states={
            WAITING_WITHDRAW_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_amount)
            ],
            CONFIRM_WITHDRAW: [
                CallbackQueryHandler(confirm_withdraw, pattern="^confirm_withdraw$"),
                CallbackQueryHandler(cancel_withdraw, pattern="^cancel_withdraw$")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_withdraw),
            CallbackQueryHandler(cancel_withdraw, pattern="^cancel_withdraw$")
        ],
        map_to_parent={
            ConversationHandler.END: "END"
        }
    )
    application.add_handler(withdraw_conv_handler)
    
    # 🎯 CALLBACK ОБРАБОТЧИКИ
    application.add_handler(CallbackQueryHandler(back_to_profile_callback, pattern="^back_to_profile$"))
    application.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
    application.add_handler(CallbackQueryHandler(deposit_callback, pattern="^deposit$"))
    application.add_handler(CallbackQueryHandler(play_games_callback, pattern="^play_games$"))
    application.add_handler(CallbackQueryHandler(handle_game_selection, pattern="^play_"))
    application.add_handler(CallbackQueryHandler(change_bet_callback, pattern="^change_bet$"))
    application.add_handler(CallbackQueryHandler(referral_system_callback, pattern="^referral_system$"))
    application.add_handler(CallbackQueryHandler(handle_deposit_selection, pattern="^buy_"))
    
    # 👑 АДМИН CALLBACK ОБРАБОТЧИКИ
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_stats_callback, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(admin_users_callback, pattern="^admin_users$"))
    application.add_handler(CallbackQueryHandler(admin_moderation_callback, pattern="^admin_moderation$"))
    application.add_handler(CallbackQueryHandler(admin_finance_callback, pattern="^admin_finance$"))
    application.add_handler(CallbackQueryHandler(admin_games_callback, pattern="^admin_games$"))
    application.add_handler(CallbackQueryHandler(admin_promo_callback, pattern="^admin_promo$"))
    application.add_handler(CallbackQueryHandler(admin_system_callback, pattern="^admin_system$"))
    application.add_handler(CallbackQueryHandler(admin_logs_callback, pattern="^admin_logs$"))
    application.add_handler(CallbackQueryHandler(admin_help_callback, pattern="^admin_help$"))
    application.add_handler(CallbackQueryHandler(admin_clear_logs_callback, pattern="^admin_clear_logs$"))
    
    print("🎰 MetaSlots Casino Bot запущен!")
    print("⚙️ Конфигурация загружена:")
    print(f"   • Пользователей: {len(user_data)}")
    print(f"   • Промокодов: {len(promo_codes)}")
    print(f"   • Забанено: {len(banned_users)}")
    print(f"   • Администраторов: {sum(1 for mode in admin_mode.values() if mode)}")
    
    application.run_polling()

if __name__ == "__main__":
    main()
