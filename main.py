import os
import json
import random
import datetime
import asyncio
from collections import defaultdict
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, PreCheckoutQueryHandler
from threading import Thread
from flask import Flask

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

# 🎮 ПОЛНАЯ КОНФИГУРАЦИЯ ИГР (ОБНОВЛЕННАЯ С ВОЗВРАТАМИ ДЛЯ ВСЕХ ИГР)
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

# 🎰 КОНФИГУРАЦИЯ ДЛЯ СЛОТОВ 777 (ТОЛЬКО ДЖЕКПОТ)
SLOTS_777_CONFIG = {
    "🎰": {
        "values": {
            # СЛОТЫ 777 - 64 значения, ТОЛЬКО 1 выигрышное (64) с увеличенным призом
            1: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш. Возврат: {prize} ⭐"},
            2: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш. Возврат: {prize} ⭐"},
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
    'used_promo_codes': []
})

# 🆕 ОБНОВЛЕННАЯ СИСТЕМА АКТИВНОСТИ С НЕДЕЛЬНЫМИ НАГРАДАМИ
user_activity = defaultdict(lambda: {
    'weekly_streak_days': 0,           # текущая серия дней
    'weekly_total_bets': 0,            # общая сумма ставок за неделю
    'weekly_total_games': 0,           # общее количество игр за неделю
    'last_weekly_bonus_date': None,    # дата последнего получения бонуса
    'daily_games_count': 0,            # игры за текущий день
    'last_activity_date': None,        # дата последней активности
    'current_week_start': None         # начало текущей недели
})

# 🆕 РЕФЕРАЛЬНЫЕ КОДЫ
referral_codes = {}  # code -> user_id

# 🆕 ПРОМОКОДЫ
promo_codes = {}  # code -> {amount, uses_left, created_by, created_at, used_by}

# 🆕 СИСТЕМА БАНОВ
banned_users = {}  # user_id -> {'reason': str, 'banned_by': int, 'banned_at': str}

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
            'banned_users': banned_users
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

# 🆕 ОПТИМИЗИРОВАННАЯ СИСТЕМА НЕДЕЛЬНЫХ НАГРАД
def get_week_start():
    today = datetime.datetime.now().date()
    return today - datetime.timedelta(days=today.weekday())

def update_weekly_activity(user_id: int, bet_amount: float):
    try:
        today = datetime.datetime.now().date()
        activity = user_activity[user_id]
        
        if activity['current_week_start'] is None:
            activity['current_week_start'] = get_week_start().isoformat()
        
        current_week_start = datetime.date.fromisoformat(activity['current_week_start'])
        today_week_start = get_week_start()
        
        if today_week_start > current_week_start:
            activity['weekly_streak_days'] = 0
            activity['weekly_total_bets'] = 0
            activity['weekly_total_games'] = 0
            activity['daily_games_count'] = 0
            activity['current_week_start'] = today_week_start.isoformat()
        
        last_activity_date = activity['last_activity_date']
        if last_activity_date:
            last_date = datetime.date.fromisoformat(last_activity_date)
            days_diff = (today - last_date).days
            
            if days_diff == 1:
                if activity['daily_games_count'] >= WEEKLY_BONUS_CONFIG["min_daily_games"]:
                    activity['weekly_streak_days'] += 1
                else:
                    activity['weekly_streak_days'] = 0
            elif days_diff > 1:
                activity['weekly_streak_days'] = 0
        else:
            activity['weekly_streak_days'] = 1
        
        activity['daily_games_count'] += 1
        activity['weekly_total_games'] += 1
        activity['weekly_total_bets'] += bet_amount
        activity['last_activity_date'] = today.isoformat()
        
        if (activity['weekly_streak_days'] >= WEEKLY_BONUS_CONFIG["required_days"] and
            activity['last_weekly_bonus_date'] != today.isoformat()):
            
            return calculate_weekly_bonus(user_id)
        
        return None
        
    except Exception as e:
        print(f"Ошибка в update_weekly_activity для пользователя {user_id}: {e}")
        return None

def calculate_weekly_bonus(user_id: int):
    try:
        activity = user_activity[user_id]
        
        base_bonus = activity['weekly_total_bets'] * WEEKLY_BONUS_CONFIG["base_percent"]
        
        min_games = WEEKLY_BONUS_CONFIG["min_daily_games"] * WEEKLY_BONUS_CONFIG["required_days"]
        extra_games = max(0, activity['weekly_total_games'] - min_games)
        extra_bonus = activity['weekly_total_bets'] * extra_games * WEEKLY_BONUS_CONFIG["bonus_per_extra_game"]
        
        max_extra = activity['weekly_total_bets'] * WEEKLY_BONUS_CONFIG["max_extra_bonus"]
        extra_bonus = min(extra_bonus, max_extra)
        
        total_bonus = base_bonus + extra_bonus
        
        user_data[user_id]['game_balance'] += total_bonus
        activity['last_weekly_bonus_date'] = datetime.datetime.now().date().isoformat()
        
        activity['weekly_streak_days'] = 0
        activity['weekly_total_bets'] = 0
        activity['weekly_total_games'] = 0
        activity['daily_games_count'] = 0
        
        save_data()
        
        return {
            'base_bonus': base_bonus,
            'extra_bonus': extra_bonus,
            'total_bonus': total_bonus,
            'total_games': activity['weekly_total_games'],
            'total_bets': activity['weekly_total_bets']
        }
        
    except Exception as e:
        print(f"Ошибка в calculate_weekly_bonus для пользователя {user_id}: {e}")
        return None

# 🎰 СИСТЕМА СЕРИЙ ПОБЕД, МЕГА-ВЫИГРЫШЕЙ И ВОЗВРАТОВ (ОБНОВЛЕННАЯ С ВОЗВРАТАМИ ДЛЯ ВСЕХ ИГР)
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

def use_promo_code(user_id: int, code: str) -> bool:
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

async def unban_user(user_id: int):
    if user_id in banned_users:
        del banned_users[user_id]
        save_data()
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
    
    profile_text = f"""
📊 Личный кабинет

👤 Имя: {user.first_name}
🆔 ID: {user_id}
📅 Регистрация: {data['registration_date'][:10]}
🎮 Режим слотов: {slots_mode_text}

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
        
        success = await unban_user(target_id)
        
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

# 👑 АДМИН ПАНЕЛЬ
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    total_users = len(user_data)
    total_games = sum(data['total_games'] for data in user_data.values())
    total_balance = sum(round(data['game_balance'], 1) for data in user_data.values())
    total_deposited = sum(data['total_deposited'] for data in user_data.values())
    
    total_win_streaks = sum(data['max_win_streak'] for data in user_data.values())
    total_mega_wins = sum(data['mega_wins_count'] for data in user_data.values())
    total_mega_amount = sum(round(data['total_mega_win_amount'], 1) for data in user_data.values())
    
    admin_text = f"""
👑 АДМИН ПАНЕЛЬ - ПАНЕЛЬ УПРАВЛЕНИЯ

📊 ОСНОВНАЯ СТАТИСТИКА:
👤 Пользователей: {total_users}
🎮 Всего игр: {total_games}
💎 Общий баланс: {total_balance} ⭐
💳 Пополнено всего: {total_deposited} ⭐

🎰 СИСТЕМЫ БОНУСОВ:
🔥 Макс. серии побед: {total_win_streaks}
🎉 Мега-выигрышей: {total_mega_wins}
💫 Сумма мега-выигрышей: {total_mega_amount} ⭐

🎟️ ПРОМОКОДЫ:
Активных: {len(promo_codes)}/{PROMO_CONFIG['max_active_promos']}

⚡ БЫСТРЫЙ ДОСТУП:
    """
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("🏆 Топ игроки", callback_data="admin_top"),
            InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton("💰 Управление балансами", callback_data="admin_balance"),
            InlineKeyboardButton("🔍 Поиск", callback_data="admin_search")
        ],
        [
            InlineKeyboardButton("🛠️ Система", callback_data="admin_system"),
            InlineKeyboardButton("🎁 Промокоды", callback_data="admin_promo")
        ],
        [
            InlineKeyboardButton("🚫 Бан-менеджер", callback_data="admin_ban"),
            InlineKeyboardButton("💾 Резервная копия", callback_data="admin_backup")
        ],
        [
            InlineKeyboardButton("💸 Заявки на вывод", callback_data="admin_withdrawals"),
            InlineKeyboardButton("🎮 Тест игр", callback_data="admin_play")
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings"),
            InlineKeyboardButton("❌ Выйти из админки", callback_data="admin_exit")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(admin_text, reply_markup=reply_markup)

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    await admin_panel(update, context)

# 📊 АДМИН СТАТИСТИКА
async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    total_users = len(user_data)
    total_games = sum(data['total_games'] for data in user_data.values())
    total_wins = sum(data['total_wins'] for data in user_data.values())
    total_balance = sum(round(data['game_balance'], 1) for data in user_data.values())
    total_deposited = sum(data['total_deposited'] for data in user_data.values())
    total_real_money = sum(data['real_money_spent'] for data in user_data.values())
    
    total_win_streaks = sum(data['max_win_streak'] for data in user_data.values())
    total_mega_wins = sum(data['mega_wins_count'] for data in user_data.values())
    total_mega_amount = sum(round(data['total_mega_win_amount'], 1) for data in user_data.values())
    
    total_referrals = sum(data['referrals_count'] for data in user_data.values())
    total_referral_earnings = sum(round(data['referral_earnings'], 1) for data in user_data.values())
    
    active_users_24h = 0
    active_users_7d = 0
    now = datetime.datetime.now()
    
    for data in user_data.values():
        if 'last_activity' in data:
            last_activity = datetime.datetime.fromisoformat(data['last_activity'])
            hours_diff = (now - last_activity).total_seconds() / 3600
            
            if hours_diff <= 24:
                active_users_24h += 1
            if hours_diff <= 168:
                active_users_7d += 1
    
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
    
    stats_text = f"""
📊 ПОДРОБНАЯ СТАТИСТИКА СИСТЕМЫ

👤 ПОЛЬЗОВАТЕЛИ:
• Всего пользователей: {total_users}
• Активных за 24ч: {active_users_24h}
• Активных за 7д: {active_users_7d}

🎮 ИГРОВАЯ СТАТИСТИКА:
• Всего игр: {total_games}
• Всего побед: {total_wins}
• Винрейт: {win_rate:.1f}%

💰 ФИНАНСЫ:
• Общий баланс: {total_balance} ⭐
• Пополнено всего: {total_deposited} ⭐
• Потрачено реальных денег: {total_real_money} Stars

🎰 СИСТЕМЫ БОНУСОВ:
• Макс. серии побед: {total_win_streaks}
• Мега-выигрышей: {total_mega_wins}
• Сумма мега-выигрышей: {total_mega_amount} ⭐

👥 РЕФЕРАЛЬНАЯ СИСТЕМА:
• Всего рефералов: {total_referrals}
• Заработано на рефералах: {total_referral_earnings} ⭐

🎟️ ПРОМОКОДЫ:
• Активных: {len(promo_codes)}/{PROMO_CONFIG['max_active_promos']}
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 В админку", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

# 🆕 АДМИН КОМАНДА ДЛЯ ПОИСКА ПОЛЬЗОВАТЕЛЯ
async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) == 0:
        await update.message.reply_text(
            "🔍 Поиск пользователя\n\n"
            "Использование: /find <user_id> или /find <username>\n\n"
            "Примеры:\n"
            "/find 123456789\n"
            "/find @username"
        )
        return
    
    search_query = context.args[0]
    
    found_users = []
    
    for uid, data in user_data.items():
        if str(uid) == search_query:
            found_users = [(uid, data)]
            break
    
    if not found_users:
        await update.message.reply_text("❌ Пользователь не найден!")
        return
    
    user_id_found, user_data_found = found_users[0]
    
    win_rate = (user_data_found['total_wins'] / user_data_found['total_games'] * 100) if user_data_found['total_games'] > 0 else 0
    
    user_info = f"""
👤 ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ

🆔 ID: {user_id_found}
📅 Регистрация: {user_data_found['registration_date'][:10]}
💰 Баланс: {round(user_data_found['game_balance'], 1)} ⭐
🎯 Текущая ставка: {user_data_found['current_bet']} ⭐
🎮 Всего игр: {user_data_found['total_games']}
🏆 Побед: {user_data_found['total_wins']}
📈 Винрейт: {win_rate:.1f}%
💳 Пополнено: {user_data_found['total_deposited']} ⭐
💸 Потрачено реальных денег: {user_data_found['real_money_spent']} Stars

🔥 СИСТЕМЫ БОНУСОВ:
📊 Текущая серия побед: {user_data_found['win_streak']}
🏆 Максимальная серия: {user_data_found['max_win_streak']}
🎉 Мега-выигрышей: {user_data_found['mega_wins_count']}
💫 Сумма мега-выигрышей: {round(user_data_found['total_mega_win_amount'], 1)} ⭐

👥 РЕФЕРАЛЬНАЯ СИСТЕМА:
🎯 Реферальный код: {user_data_found['referral_code']}
👥 Приглашено друзей: {user_data_found['referrals_count']}
💰 Заработано с рефералов: {round(user_data_found['referral_earnings'], 1)} ⭐
    """
    
    keyboard = [
        [
            InlineKeyboardButton("💰 Изменить баланс", callback_data=f"admin_edit_balance_{user_id_found}"),
            InlineKeyboardButton("🎯 Изменить ставку", callback_data=f"admin_edit_bet_{user_id_found}")
        ],
        [
            InlineKeyboardButton("🚫 Забанить", callback_data=f"admin_ban_user_{user_id_found}"),
            InlineKeyboardButton("✅ Разбанить", callback_data=f"admin_unban_user_{user_id_found}")
        ],
        [
            InlineKeyboardButton("🔙 В админку", callback_data="admin_panel")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(user_info, reply_markup=reply_markup)

# 🆕 АДМИН КОМАНДА ДЛЯ СОЗДАНИЯ ПРОМОКОДА
async def create_promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "🎟️ Создание промокода\n\n"
            "Использование: /create_promo <сумма> <количество_использований>\n\n"
            "Пример: /create_promo 100 50\n"
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

# 🆕 АДМИН КОМАНДА ДЛЯ УПРАВЛЕНИЯ БАЛАНСОМ
async def set_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "💰 Установка баланса\n\n"
            "Использование: /set_balance <user_id> <сумма>\n\n"
            "Пример: /set_balance 123456789 1000"
        )
        return
    
    try:
        target_id = int(context.args[0])
        amount = float(context.args[1])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        user_data[target_id]['game_balance'] = amount
        save_data()
        
        await update.message.reply_text(
            f"✅ Баланс пользователя {target_id} установлен на {amount} ⭐"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите корректные числа!")

# 🆕 АДМИН КОМАНДА ДЛЯ РАССЫЛКИ
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) == 0:
        await update.message.reply_text(
            "📢 Рассылка сообщения\n\n"
            "Использование: /broadcast <текст_сообщения>\n\n"
            "Пример: /broadcast Важное обновление системы!"
        )
        return
    
    message_text = ' '.join(context.args)
    total_users = len(user_data)
    successful_sends = 0
    failed_sends = 0
    
    progress_message = await update.message.reply_text(
        f"📢 Начинаю рассылку...\n"
        f"👤 Всего пользователей: {total_users}\n"
        f"✅ Успешно: 0\n"
        f"❌ Ошибок: 0"
    )
    
    for uid in user_data.keys():
        try:
            await context.bot.send_message(uid, message_text)
            successful_sends += 1
        except Exception:
            failed_sends += 1
        
        if (successful_sends + failed_sends) % 10 == 0:
            await progress_message.edit_text(
                f"📢 Рассылка...\n"
                f"👤 Всего пользователей: {total_users}\n"
                f"✅ Успешно: {successful_sends}\n"
                f"❌ Ошибок: {failed_sends}\n"
                f"📊 Прогресс: {((successful_sends + failed_sends) / total_users * 100):.1f}%"
            )
    
    await progress_message.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"👤 Всего пользователей: {total_users}\n"
        f"✅ Успешно: {successful_sends}\n"
        f"❌ Ошибок: {failed_sends}"
    )

# 🆕 АДМИН КОМАНДА ДЛЯ ТОП ИГРОКОВ
async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    top_balance = sorted(user_data.items(), key=lambda x: x[1]['game_balance'], reverse=True)[:10]
    top_games = sorted(user_data.items(), key=lambda x: x[1]['total_games'], reverse=True)[:10]
    top_wins = sorted(user_data.items(), key=lambda x: x[1]['total_wins'], reverse=True)[:10]
    top_deposited = sorted(user_data.items(), key=lambda x: x[1]['total_deposited'], reverse=True)[:10]
    
    top_text = "🏆 ТОП ПОЛЬЗОВАТЕЛЕЙ\n\n"
    
    top_text += "💰 ПО БАЛАНСУ:\n"
    for i, (uid, data) in enumerate(top_balance, 1):
        top_text += f"{i}. ID {uid}: {round(data['game_balance'], 1)} ⭐\n"
    
    top_text += "\n🎮 ПО КОЛИЧЕСТВУ ИГР:\n"
    for i, (uid, data) in enumerate(top_games, 1):
        top_text += f"{i}. ID {uid}: {data['total_games']} игр\n"
    
    top_text += "\n🏆 ПО КОЛИЧЕСТВУ ПОБЕД:\n"
    for i, (uid, data) in enumerate(top_wins, 1):
        top_text += f"{i}. ID {uid}: {data['total_wins']} побед\n"
    
    top_text += "\n💳 ПО СУММЕ ПОПОЛНЕНИЙ:\n"
    for i, (uid, data) in enumerate(top_deposited, 1):
        top_text += f"{i}. ID {uid}: {data['total_deposited']} ⭐\n"
    
    await update.message.reply_text(top_text)

# 🆕 АДМИН КОМАНДА ДЛЯ СИСТЕМНОЙ ИНФОРМАЦИИ
async def system_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    import psutil
    import platform
    
    process = psutil.Process()
    memory_usage = process.memory_info().rss / 1024 / 1024
    
    system_info = f"""
💻 СИСТЕМНАЯ ИНФОРМАЦИЯ

🖥️ Система: {platform.system()} {platform.release()}
🐍 Python: {platform.python_version()}
💾 Память: {memory_usage:.1f} MB

📊 ДАННЫЕ:
👤 Пользователей: {len(user_data)}
🎮 Сессий: {len(user_sessions)}
🎟️ Промокодов: {len(promo_codes)}
🚫 Забаненных: {len(banned_users)}

⚙️ КОНФИГУРАЦИЯ:
🎰 Игр: {len(GAMES_CONFIG)}
💰 Продуктов: {len(PRODUCTS)}
🎁 Пакетов вывода: {len(WITHDRAWAL_AMOUNTS)}
    """
    
    await update.message.reply_text(system_info)

# 🆕 АДМИН КОМАНДА ДЛЯ СБРОСА СЕРИЙ ПОБЕД
async def reset_streaks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    reset_count = 0
    for data in user_data.values():
        if data['win_streak'] > 0:
            data['win_streak'] = 0
            reset_count += 1
    
    save_data()
    
    await update.message.reply_text(f"✅ Сброшено серий побед у {reset_count} пользователей")

# 🆕 АДМИН КОМАНДА ДЛЯ ЭКСПОРТА ДАННЫХ
async def export_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['User ID', 'Balance', 'Total Games', 'Total Wins', 'Total Deposited', 'Registration Date'])
    
    for uid, data in user_data.items():
        writer.writerow([
            uid,
            round(data['game_balance'], 1),
            data['total_games'],
            data['total_wins'],
            data['total_deposited'],
            data['registration_date'][:10]
        ])
    
    output.seek(0)
    
    await update.message.reply_document(
        document=io.BytesIO(output.getvalue().encode()),
        filename=f"user_data_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        caption="📊 Экспорт данных пользователей"
    )

# 🆕 ОБРАБОТЧИКИ CALLBACK ДЛЯ АДМИН ПАНЕЛИ
async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = query.from_user.id
    
    if not admin_mode.get(user_id, False):
        await query.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if callback_data == "admin_stats":
        await admin_stats_callback(update, context)
    elif callback_data == "admin_panel":
        await admin_panel(update, context)
    elif callback_data == "admin_exit":
        admin_mode[user_id] = False
        save_data()
        await query.edit_message_text(
            "✅ Режим администратора деактивирован!\n\n"
            "Возвращаюсь в обычный режим...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")]
            ])
        )
    else:
        await query.edit_message_text(
            "⚙️ Этот раздел находится в разработке...\n\n"
            "Используйте админ-команды напрямую для полного функционала.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 В админку", callback_data="admin_panel")]
            ])
        )

# 🚀 ЗАПУСК БОТА
def setup_handlers(application):
    # Основные команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("bet", bet_command))
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CommandHandler("withdraw", withdraw_command))
    application.add_handler(CommandHandler("activity", activity_command))
    application.add_handler(CommandHandler("promo", promo_command))
    
    # Админ команды
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("banlist", banlist_command))
    application.add_handler(CommandHandler("find", find_command))
    application.add_handler(CommandHandler("create_promo", create_promo_command))
    application.add_handler(CommandHandler("set_balance", set_balance_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("system", system_info_command))
    application.add_handler(CommandHandler("reset_streaks", reset_streaks_command))
    application.add_handler(CommandHandler("export", export_data_command))
    
    # Обработчики платежей
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # Обработчики callback запросов
    application.add_handler(CallbackQueryHandler(profile, pattern="^back_to_profile$"))
    application.add_handler(CallbackQueryHandler(play_games_callback, pattern="^play_games$"))
    application.add_handler(CallbackQueryHandler(handle_game_selection, pattern="^play_"))
    application.add_handler(CallbackQueryHandler(change_bet_callback, pattern="^change_bet$"))
    application.add_handler(CallbackQueryHandler(deposit_callback, pattern="^deposit$"))
    application.add_handler(CallbackQueryHandler(handle_deposit_selection, pattern="^buy_"))
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))
    application.add_handler(CallbackQueryHandler(handle_withdraw_selection, pattern="^withdraw_"))
    application.add_handler(CallbackQueryHandler(confirm_withdraw, pattern="^confirm_withdraw$"))
    application.add_handler(CallbackQueryHandler(referral_system_callback, pattern="^referral_system$"))
    
    # Админ callback обработчики
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))
    
    # Обработчики dice сообщений
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_user_dice))

def main():
    load_data()
    
    application = Application.builder().token(BOT_TOKEN).build()
    setup_handlers(application)
    
    print("🤖 Бот запущен!")
    
    # Запуск Flask сервера для Render
    def run_flask():
        app = Flask(__name__)
        
        @app.route('/')
        def home():
            return "🤖 NSource Casino Bot is running!"
        
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port)
    
    # Запуск Flask в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
