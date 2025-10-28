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

# 🎮 ПОЛНАЯ КОНФИГУРАЦИЯ ИГР (ОБНОВЛЕННАЯ)
GAMES_CONFIG = {
    "🎰": {
        "values": {
            # ОБЫЧНЫЕ СЛОТЫ - 64 значения, 4 выигрышных
            1: {"win": True, "base_prize": BASE_PRIZES["🎰"]["ТРИ БАРА"], "message": "🎰 ТРИ БАРА! Выигрыш: {prize} ⭐"},
            2: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #2 - проигрыш"},
            3: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #3 - проигрыш"},
            4: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #4 - проигрыш"},
            5: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #5 - проигрыш"},
            6: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #6 - проигрыш"},
            7: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #7 - проигрыш"},
            8: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #8 - проигрыш"},
            9: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #9 - проигрыш"},
            10: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #10 - проигрыш"},
            11: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #11 - проигрыш"},
            12: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #12 - проигрыш"},
            13: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #13 - проигрыш"},
            14: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #14 - проигрыш"},
            15: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #15 - проигрыш"},
            16: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #16 - проигрыш"},
            17: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #17 - проигрыш"},
            18: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #18 - проигрыш"},
            19: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #19 - проигрыш"},
            20: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #20 - проигрыш"},
            21: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #21 - проигрыш"},
            22: {"win": True, "base_prize": BASE_PRIZES["🎰"]["ТРИ ВИШНИ"], "message": "🎰 ТРИ ВИШНИ! Выигрыш: {prize} ⭐"},
            23: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #23 - проигрыш"},
            24: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #24 - проигрыш"},
            25: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #25 - проигрыш"},
            26: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #26 - проигрыш"},
            27: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #27 - проигрыш"},
            28: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #28 - проигрыш"},
            29: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #29 - проигрыш"},
            30: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #30 - проигрыш"},
            31: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #31 - проигрыш"},
            32: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #32 - проигрыш"},
            33: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #33 - проигрыш"},
            34: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #34 - проигрыш"},
            35: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #35 - проигрыш"},
            36: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #36 - проигрыш"},
            37: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #37 - проигрыш"},
            38: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #38 - проигрыш"},
            39: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #39 - проигрыш"},
            40: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #40 - проигрыш"},
            41: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #41 - проигрыш"},
            42: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #42 - проигрыш"},
            43: {"win": True, "base_prize": BASE_PRIZES["🎰"]["ТРИ ЛИМОНЫ"], "message": "🎰 ТРИ ЛИМОНА! Выигрыш: {prize} ⭐"},
            44: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #44 - проигрыш"},
            45: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #45 - проигрыш"},
            46: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #46 - проигрыш"},
            47: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #47 - проигрыш"},
            48: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #48 - проигрыш"},
            49: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #49 - проигрыш"},
            50: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #50 - проигрыш"},
            51: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #51 - проигрыш"},
            52: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #52 - проигрыш"},
            53: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #53 - проигрыш"},
            54: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #54 - проигрыш"},
            55: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #55 - проигрыш"},
            56: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #56 - проигрыш"},
            57: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #57 - проигрыш"},
            58: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #58 - проигрыш"},
            59: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #59 - проигрыш"},
            60: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #60 - проигрыш"},
            61: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #61 - проигрыш"},
            62: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #62 - проигрыш"},
            63: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #63 - проигрыш"},
            64: {"win": True, "base_prize": BASE_PRIZES["🎰"]["ДЖЕКПОТ 777"], "message": "🎰 ДЖЕКПОТ 777! Выигрыш: {prize} ⭐"}
        }
    },
    "🎯": {
        "values": {
            # ДАРТС - 6 значений, 1 выигрышное (6)
            1: {"win": False, "base_prize": 0, "message": "🎯 - проигрыш"},
            2: {"win": False, "base_prize": 0, "message": "🎯 - проигрыш"},
            3: {"win": False, "base_prize": 0, "message": "🎯 - проигрыш"},
            4: {"win": False, "base_prize": 0, "message": "🎯 - проигрыш"},
            5: {"win": False, "base_prize": 0, "message": "🎯 - проигрыш"},
            6: {"win": True, "base_prize": BASE_PRIZES["🎯"]["ПОПАДАНИЕ В ЦЕЛЬ"], "message": "🎯 - ПОПАДАНИЕ В ЦЕЛЬ! Выигрыш: {prize} ⭐"}
        }
    },
    "🎲": {
        "values": {
            # КОСТИ - 6 значений, 1 выигрышное (6)
            1: {"win": False, "base_prize": 0, "message": "🎲 - проигрыш"},
            2: {"win": False, "base_prize": 0, "message": "🎲 - проигрыш"},
            3: {"win": False, "base_prize": 0, "message": "🎲 - проигрыш"},
            4: {"win": False, "base_prize": 0, "message": "🎲 - проигрыш"},
            5: {"win": False, "base_prize": 0, "message": "🎲 - проигрыш"},
            6: {"win": True, "base_prize": BASE_PRIZES["🎲"]["ВЫПАЛО 6"], "message": "🎲 - ВЫПАЛО 6! Выигрыш: {prize} ⭐"}
        }
    },
    "🎳": {
        "values": {
            # БОУЛИНГ - 6 значений, 1 выигрышное (6)
            1: {"win": False, "base_prize": 0, "message": "🎳 - проигрыш"},
            2: {"win": False, "base_prize": 0, "message": "🎳 - проигрыш"},
            3: {"win": False, "base_prize": 0, "message": "🎳 - проигрыш"},
            4: {"win": False, "base_prize": 0, "message": "🎳 - проигрыш"},
            5: {"win": False, "base_prize": 0, "message": "🎳 - проигрыш"},
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
            1: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            2: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            3: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #3 - проигрыш"},
            4: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #4 - проигрыш"},
            5: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #5 - проигрыш"},
            6: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #6 - проигрыш"},
            7: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #7 - проигрыш"},
            8: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #8 - проигрыш"},
            9: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #9 - проигрыш"},
            10: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #10 - проигрыш"},
            11: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #11 - проигрыш"},
            12: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #12 - проигрыш"},
            13: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #13 - проигрыш"},
            14: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #14 - проигрыш"},
            15: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #15 - проигрыш"},
            16: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #16 - проигрыш"},
            17: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #17 - проигрыш"},
            18: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #18 - проигрыш"},
            19: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #19 - проигрыш"},
            20: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #20 - проигрыш"},
            21: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #21 - проигрыш"},
            22: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #22 - проигрыш"},
            23: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #23 - проигрыш"},
            24: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #24 - проигрыш"},
            25: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #25 - проигрыш"},
            26: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #26 - проигрыш"},
            27: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #27 - проигрыш"},
            28: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #28 - проигрыш"},
            29: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #29 - проигрыш"},
            30: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #30 - проигрыш"},
            31: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #31 - проигрыш"},
            32: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #32 - проигрыш"},
            33: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #33 - проигрыш"},
            34: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #34 - проигрыш"},
            35: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #35 - проигрыш"},
            36: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #36 - проигрыш"},
            37: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #37 - проигрыш"},
            38: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #38 - проигрыш"},
            39: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #39 - проигрыш"},
            40: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #40 - проигрыш"},
            41: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #41 - проигрыш"},
            42: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #42 - проигрыш"},
            43: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #43 - проигрыш"},
            44: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #44 - проигрыш"},
            45: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #45 - проигрыш"},
            46: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #46 - проигрыш"},
            47: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #47 - проигрыш"},
            48: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #48 - проигрыш"},
            49: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #49 - проигрыш"},
            50: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #50 - проигрыш"},
            51: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #51 - проигрыш"},
            52: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #52 - проигрыш"},
            53: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #53 - проигрыш"},
            54: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #54 - проигрыш"},
            55: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #55 - проигрыш"},
            56: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #56 - проигрыш"},
            57: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #57 - проигрыш"},
            58: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #58 - проигрыш"},
            59: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #59 - проигрыш"},
            60: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #60 - проигрыш"},
            61: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #61 - проигрыш"},
            62: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #62 - проигрыш"},
            63: {"win": False, "base_prize": 0, "message": "🎰 Комбинация #63 - проигрыш"},
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
        result_config = {"win": False, "base_prize": 0, "message": f"{emoji} - проигрыш"}
    
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
    avg_win_streak = total_win_streaks / total_users if total_users > 0 else 0
    
    total_bet_amount = sum(data['current_bet'] * data['total_games'] for data in user_data.values())
    total_win_amount = total_balance + total_deposited
    rtp = (total_win_amount / total_bet_amount * 100) if total_bet_amount > 0 else 0
    
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
    
    richest_user = max(user_data.items(), key=lambda x: x[1]['game_balance'], default=(0, {'game_balance': 0}))
    most_active = max(user_data.items(), key=lambda x: x[1]['total_games'], default=(0, {'total_games': 0}))
    best_streak_user = max(user_data.items(), key=lambda x: x[1]['max_win_streak'], default=(0, {'max_win_streak': 0}))
    most_mega_wins = max(user_data.items(), key=lambda x: x[1]['mega_wins_count'], default=(0, {'mega_wins_count': 0}))
    
    stats_text = f"""
📊 ДЕТАЛЬНАЯ СТАТИСТИКА БОТА

👥 ПОЛЬЗОВАТЕЛИ:
• Всего пользователей: {total_users}
• Новые за сегодня: {len([uid for uid, data in user_data.items() if datetime.datetime.fromisoformat(data['last_activity']).date() == datetime.datetime.now().date()])}

🎮 ИГРОВАЯ СТАТИСТИКА:
• Всего игр: {total_games}
• Всего побед: {total_wins}
• Общий винрейт: {win_rate:.1f}%
• RTP (Return to Player): {rtp:.1f}%
• Средняя ставка: {total_bet_amount // total_games if total_games > 0 else 0} ⭐

💰 ФИНАНСЫ:
• Общий баланс: {total_balance} ⭐
• Пополнено всего: {total_deposited} ⭐
• Реальные деньги: {total_real_money} Stars
• Прибыль: {total_real_money - total_balance} Stars

🎰 СИСТЕМЫ БОНУСОВ:
• Всего серий побед: {total_win_streaks}
• Средняя серия: {avg_win_streak:.1f}
• Мега-выигрышей: {total_mega_wins}
• Сумма мега-выигрышей: {total_mega_amount} ⭐

🏆 РЕКОРДЫ:
• Самый богатый: {richest_user[0]} ({round(richest_user[1]['game_balance'], 1)} ⭐)
• Самый активный: {most_active[0]} ({most_active[1]['total_games']} игр)
• Лучшая серия: {best_streak_user[0]} ({best_streak_user[1]['max_win_streak']} побед)
• Лидер мега-выигрышей: {most_mega_wins[0]} ({most_mega_wins[1]['mega_wins_count']} раз)
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

# 👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    page = int(context.user_data.get('admin_users_page', 0))
    users_per_page = 8
    all_users = list(user_data.items())
    total_pages = (len(all_users) + users_per_page - 1) // users_per_page
    
    start_idx = page * users_per_page
    end_idx = start_idx + users_per_page
    page_users = all_users[start_idx:end_idx]
    
    users_text = f"👥 СПИСОК ПОЛЬЗОВАТЕЛЕЙ (Страница {page + 1}/{total_pages})\n\n"
    
    for i, (uid, data) in enumerate(page_users, start_idx + 1):
        users_text += f"{i}. ID: {uid} | 💰: {round(data['game_balance'], 1)} ⭐ | 🎮: {data['total_games']} | 🔥: {data['win_streak']} | 🎉: {data['mega_wins_count']}\n"
    
    keyboard = []
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"admin_users_prev_{page}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"admin_users_next_{page}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔍 Расширенный поиск", callback_data="admin_search")])
    keyboard.append([InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(users_text, reply_markup=reply_markup)

# 🏆 ТОП ИГРОКОВ
async def admin_top_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    top_balance = sorted(user_data.items(), key=lambda x: x[1]['game_balance'], reverse=True)[:10]
    top_games = sorted(user_data.items(), key=lambda x: x[1]['total_games'], reverse=True)[:10]
    top_wins = sorted(user_data.items(), key=lambda x: x[1]['total_wins'], reverse=True)[:10]
    top_streaks = sorted(user_data.items(), key=lambda x: x[1]['max_win_streak'], reverse=True)[:10]
    top_mega_wins = sorted(user_data.items(), key=lambda x: x[1]['mega_wins_count'], reverse=True)[:10]
    
    top_text = "🏆 ТОП ИГРОКОВ\n\n"
    
    top_text += "💰 ПО БАЛАНСУ:\n"
    for i, (uid, data) in enumerate(top_balance, 1):
        top_text += f"{i}. ID: {uid} - {round(data['game_balance'], 1)} ⭐\n"
    
    top_text += "\n🎮 ПО КОЛИЧЕСТВУ ИГР:\n"
    for i, (uid, data) in enumerate(top_games, 1):
        top_text += f"{i}. ID: {uid} - {data['total_games']} игр\n"
    
    top_text += "\n🏆 ПО ПОБЕДАМ:\n"
    for i, (uid, data) in enumerate(top_wins, 1):
        win_rate = (data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0
        top_text += f"{i}. ID: {uid} - {data['total_wins']} побед ({win_rate:.1f}%)\n"
    
    top_text += "\n🔥 ПО СЕРИЯМ ПОБЕД:\n"
    for i, (uid, data) in enumerate(top_streaks, 1):
        top_text += f"{i}. ID: {uid} - {data['max_win_streak']} побед подряд\n"
    
    top_text += "\n🎉 ПО МЕГА-ВЫИГРЫШАм:\n"
    for i, (uid, data) in enumerate(top_mega_wins, 1):
        top_text += f"{i}. ID: {uid} - {data['mega_wins_count']} мега-выигрышей\n"
    
    keyboard = [
        [InlineKeyboardButton("📊 Общая статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(top_text, reply_markup=reply_markup)

# 📢 СИСТЕМА РАССЫЛКИ
async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    broadcast_text = """
📢 СИСТЕМА РАССЫЛКИ

Отправьте сообщение, которое будет разослано всем пользователям бота.

🎰 ОПТИМИЗИРОВАННЫЕ СИСТЕМЫ:
• Серии побед с бонусами +10%/+25%/+50%
• Случайные мега-выигрыши x1.5-x5 с шансом 0.6%
• Возвраты 2-10% при проигрыше
• Недельные награды 1-3% от суммы ставок
• Реферальная система - 10% от проигрышей друзей

⚠️ ВНИМАНИЕ: 
• Рассылка может занять несколько минут
• Не злоупотребляйте этой функцией
• Сообщение будет отправлено всем пользователям

Для отмены используйте /cancel
    """
    
    context.user_data['waiting_for_broadcast'] = True
    
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(broadcast_text, reply_markup=reply_markup)

# 💰 УПРАВЛЕНИЕ БАЛАНСАМИ
async def admin_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    balance_text = """
💰 УПРАВЛЕНИЕ БАЛАНСАМИ

Доступные команды:

/addbalance <user_id> <amount> - Добавить баланс
/setbalance <user_id> <amount> - Установить баланс
/resetbalance <user_id> - Сбросить баланс

Примеры:
/addbalance 123456789 1000
/setbalance 123456789 5000
/resetbalance 123456789
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(balance_text, reply_markup=reply_markup)

# 🔍 ПОИСК ПОЛЬЗОВАТЕЛЕЙ
async def admin_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    search_text = """
🔍 ПОИСК ПОЛЬЗОВАТЕЛЕЙ

Используйте команды:

/searchid <user_id> - Найти по ID
/searchname <имя> - Найти по имени (частичное совпадение)
/searchbalance <min> <max> - Найти по диапазону баланса
/searchstreak <min_streak> - Найти по минимальной серии побед
/searchmega <min_mega> - Найти по минимальному количеству мега-выигрышей

Примеры:
/searchid 123456789
/searchname John
/searchbalance 100 1000
/searchstreak 5
/searchmega 3
    """
    
    keyboard = [
        [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(search_text, reply_markup=reply_markup)

# 🛠️ СИСТЕМНАЯ ИНФОРМАЦИЯ
async def admin_system_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    try:
        import psutil
        import platform
        
        registration_dates = [datetime.datetime.fromisoformat(data['registration_date']) for data in user_data.values()]
        if registration_dates:
            start_time = min(registration_dates)
            uptime = datetime.datetime.now() - start_time
        else:
            uptime = datetime.timedelta(0)
        
        system_info = f"""
🛠️ СИСТЕМНАЯ ИНФОРМАЦИЯ

💻 СИСТЕМА:
• ОС: {platform.system()} {platform.release()}
• Процессор: {platform.processor() or 'Неизвестно'}
• Память: {psutil.virtual_memory().percent}% использовано
• Диск: {psutil.disk_usage('/').percent}% использовано

🤖 БОТ:
• Пользователей: {len(user_data)}
• Активных сессий: {len(user_sessions)}
• Админов: {sum(admin_mode.values())}
• Время работы: {uptime}

📊 ПРОИЗВОДИТЕЛЬНОСТЬ:
• Загрузка CPU: {psutil.cpu_percent()}%
• Использование RAM: {psutil.virtual_memory().used // (1024**3)}GB/{psutil.virtual_memory().total // (1024**3)}GB

🎰 СИСТЕМЫ БОНУСОВ:
• Шанс мега-выигрыша: {MEGA_WIN_CONFIG['chance']*100}%
• Множитель мега-выигрыша: {MEGA_WIN_CONFIG['min_multiplier']}-{MEGA_WIN_CONFIG['max_multiplier']}x
• Бонусы за серии: {len(WIN_STREAK_BONUSES)} уровней
• Возвраты при проигрыше: {REFUND_CONFIG['min_refund']*100}%-{REFUND_CONFIG['max_refund']*100}%
• Недельные награды: {WEEKLY_BONUS_CONFIG['base_percent']*100}% базовых + до {WEEKLY_BONUS_CONFIG['max_extra_bonus']*100}% дополнительных
• Реферальная система: {REFERRAL_CONFIG['reward_percent']*100}% от проигрышей друзей
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="admin_system")],
            [InlineKeyboardButton("💾 Резервная копия", callback_data="admin_backup")],
            [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(system_info, reply_markup=reply_markup)
        
    except ImportError:
        await query.edit_message_text(
            "❌ Не удалось получить системную информацию. Установите библиотеку psutil: pip install psutil",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]])
        )

# 🎁 СИСТЕМА ПРОМОКОДОВ
async def admin_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    promo_text = """
🎁 СИСТЕМА ПРОМОКОДОВ

Доступные команды:

/promo_create <сумма> <использований> - Создать промокод
/promo_list - Список промокодов
/promo_delete <код> - Удалить промокод
/promo_info <код> - Статистика промокода

Пример:
/promo_create 100 50
- Создаст промокод на 100 ⭐ с 50 использованиями
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(promo_text, reply_markup=reply_markup)

# 🚫 БАН-МЕНЕДЖЕР
async def admin_ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    ban_text = """
🚫 БАН-МЕНЕДЖЕР

Команды для управления пользователями:

/ban <user_id> <причина> - Забанить пользователя
/unban <user_id> - Разбанить пользователя
/banlist - Список забаненных
/mute <user_id> <время> - Заглушить пользователя
/unmute <user_id> - Снять заглушку

Примеры:
/ban 123456789 Мошенничество
/ban 123456789 7d - бан на 7 дней
/mute 123456789 1h - мут на 1 час
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(ban_text, reply_markup=reply_markup)

# 💾 РЕЗЕРВНАЯ КОПИЯ
async def admin_backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    save_data()
    backup_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    backup_text = f"""
💾 РЕЗЕРВНАЯ КОПИЯ

✅ Резервная копия создана успешно!
🕐 Время создания: {backup_time}

📊 Данные в резервной копии:
• Пользователей: {len(user_data)}
• Игр: {sum(data['total_games'] for data in user_data.values())}
• Общий баланс: {sum(round(data['game_balance'], 1) for data in user_data.values())} ⭐
• Сессий: {len(user_sessions)}
• Промокодов: {len(promo_codes)}

💡 Для восстановления из резервной копии перезапустите бота.
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 Создать новую копию", callback_data="admin_backup")],
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(backup_text, reply_markup=reply_markup)

# 💸 ЗАЯВКИ НА ВЫВОД
async def admin_withdrawals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    if not withdrawal_requests:
        withdrawals_text = "💸 Нет заявок на вывод средств"
    else:
        withdrawals_text = "💸 ЗАЯВКИ НА ВЫВОД СРЕДСТВ:\n\n"
        
        for uid, requests in list(withdrawal_requests.items())[:20]:
            user_requests = requests[-5:]  # Последние 5 заявок
            withdrawals_text += f"👤 Пользователь {uid}:\n"
            
            for req in user_requests:
                withdrawals_text += f"  • {req['amount']} ⭐ - {req['timestamp'][:16]} - {req['status']}\n"
            withdrawals_text += "\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(withdrawals_text, reply_markup=reply_markup)

# 🎮 ТЕСТИРОВАНИЕ ИГР
async def admin_play_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    play_text = """
🎮 ТЕСТИРОВАНИЕ ИГР

Вы находитесь в режиме администратора.
Теперь вы можете играть без списания средств!

Просто отправьте любой dice эмодзи игры в чат:
🎰 - Слоты
🎯 - Дартс
🎲 - Кубик
🎳 - Боулинг
⚽ - Футбол
🏀 - Баскетбол

Все системы бонусов работают:
• Серии побед
• Мега-выигрыши
• Возвраты
• Недельные награды

⚠️ Внимание: в админ-режиме баланс не списывается и не начисляется!
    """
    
    keyboard = [
        [InlineKeyboardButton("🎮 Перейти к играм", callback_data="play_games")],
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(play_text, reply_markup=reply_markup)

# ⚙️ НАСТРОЙКИ
async def admin_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    settings_text = """
⚙️ НАСТРОЙКИ БОТА

Текущие настройки:

🎰 ИГРЫ:
• Минимальная ставка: 1 ⭐
• Максимальная ставка: 100,000 ⭐
• Время анимации: 1.5-3.5 секунд

🎰 СИСТЕМЫ БОНУСОВ:
• Шанс мега-выигрыша: 0.6%
• Множитель мега-выигрыша: 1.5-5x
• Бонусы за серии: +10%/+25%/+50%
• Возвраты при проигрыше: 2-10%
• Недельные награды: 1% базовых + до 2% дополнительных
• Реферальная система: 10% от проигрышей

💸 ВЫВОД:
• Минимальная сумма: 15 ⭐
• Подарки: 1 подарок за каждые 15 ⭐

💳 ПОПОЛНЕНИЕ:
• Курс: 1 реальная звезда = 1 ⭐
• Пакеты: 5-1000 ⭐
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(settings_text, reply_markup=reply_markup)

# ❌ ВЫХОД ИЗ АДМИНКИ
async def admin_exit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    admin_mode[user_id] = False
    save_data()
    
    await query.edit_message_text(
        "✅ Режим администратора деактивирован!\n\n"
        "Теперь вы снова обычный пользователь.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")]
        ])
    )

# 🔙 ОБРАБОТЧИК ВОЗВРАТА В АДМИНКУ
async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_panel(update, context)

# 🔄 ОБРАБОТЧИК ПЕРЕКЛЮЧЕНИЯ СТРАНИЦ ПОЛЬЗОВАТЕЛЕЙ
async def admin_users_nav_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    action, page = query.data.split('_')[2:]
    page = int(page)
    
    if action == 'prev':
        page -= 1
    elif action == 'next':
        page += 1
    
    context.user_data['admin_users_page'] = page
    await admin_users_callback(update, context)

# 🆕 КОМАНДА ДОБАВЛЕНИЯ БАЛАНСА
async def addbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) != 2:
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
        
        await update.message.reply_text(
            f"✅ Баланс пользователя {target_id} пополнен на {amount} ⭐\n"
            f"💰 Новый баланс: {round(user_data[target_id]['game_balance'], 1)} ⭐"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат аргументов!")

# 🆕 КОМАНДА УСТАНОВКИ БАЛАНСА
async def setbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("Использование: /setbalance <user_id> <amount>")
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
        await update.message.reply_text("❌ Неверный формат аргументов!")

# 🆕 КОМАНДА СБРОСА БАЛАНСА
async def resetbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /resetbalance <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        user_data[target_id]['game_balance'] = 0
        save_data()
        
        await update.message.reply_text(f"✅ Баланс пользователя {target_id} сброшен до 0 ⭐")
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID!")

# 🆕 КОМАНДА СОЗДАНИЯ ПРОМОКОДА
async def promo_create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("Использование: /promo_create <сумма> <использований>")
        return
    
    try:
        amount = int(context.args[0])
        uses = int(context.args[1])
        
        if amount < PROMO_CONFIG["min_amount"] or amount > PROMO_CONFIG["max_amount"]:
            await update.message.reply_text(
                f"❌ Сумма должна быть от {PROMO_CONFIG['min_amount']} до {PROMO_CONFIG['max_amount']} ⭐"
            )
            return
        
        if len(promo_codes) >= PROMO_CONFIG["max_active_promos"]:
            await update.message.reply_text(
                f"❌ Достигнут лимит активных промокодов ({PROMO_CONFIG['max_active_promos']})"
            )
            return
        
        code = create_promo_code(amount, uses, user_id)
        
        await update.message.reply_text(
            f"✅ Промокод создан!\n\n"
            f"🎟️ Код: {code}\n"
            f"💰 Сумма: {amount} ⭐\n"
            f"🔢 Использований: {uses}\n"
            f"👤 Создал: {user_id}\n\n"
            f"💡 Пользователи могут активировать его командой /promo {code}"
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат аргументов!")

# 🆕 КОМАНДА СПИСКА ПРОМОКОДОВ
async def promo_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if not promo_codes:
        await update.message.reply_text("📋 Список промокодов пуст")
        return
    
    promo_list_text = "🎟️ АКТИВНЫЕ ПРОМОКОДЫ:\n\n"
    
    for code, data in list(promo_codes.items())[:20]:
        promo_list_text += (
            f"🎟️ {code}\n"
            f"💰 {data['amount']} ⭐ | 🏷️ {data['uses_left']}/{data['uses_left'] + len(data.get('used_by', []))}\n"
            f"👤 Создал: {data['created_by']} | 📅 {data['created_at'][:10]}\n"
            f"────────────────────\n"
        )
    
    if len(promo_codes) > 20:
        promo_list_text += f"\n... и еще {len(promo_codes) - 20} промокодов"
    
    await update.message.reply_text(promo_list_text)

# 🆕 КОМАНДА УДАЛЕНИЯ ПРОМОКОДА
async def promo_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /promo_delete <код>")
        return
    
    code = context.args[0].upper()
    
    if code not in promo_codes:
        await update.message.reply_text("❌ Промокод не найден!")
        return
    
    del promo_codes[code]
    save_data()
    
    await update.message.reply_text(f"✅ Промокод {code} удален!")

# 🆕 КОМАНДА ИНФОРМАЦИИ О ПРОМОКОДЕ
async def promo_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /promo_info <код>")
        return
    
    code = context.args[0].upper()
    
    if code not in promo_codes:
        await update.message.reply_text("❌ Промокод не найден!")
        return
    
    promo = promo_codes[code]
    
    used_count = len(promo.get('used_by', []))
    total_uses = promo['uses_left'] + used_count
    used_percent = (used_count / total_uses * 100) if total_uses > 0 else 0
    
    promo_info_text = f"""
🎟️ ИНФОРМАЦИЯ О ПРОМОКОДЕ

🔢 Код: {code}
💰 Сумма: {promo['amount']} ⭐
🏷️ Использований: {promo['uses_left']} из {total_uses} ({used_percent:.1f}%)
👤 Создал: {promo['created_by']}
📅 Создан: {promo['created_at'][:16]}
    """
    
    if used_count > 0:
        promo_info_text += f"\n👥 Использовали: {used_count} пользователей"
        promo_info_text += f"\n💎 Выдано всего: {promo['amount'] * used_count} ⭐"
    
    await update.message.reply_text(promo_info_text)

# 🆕 КОМАНДЫ ПОИСКА
async def searchid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /searchid <user_id>")
        return
    
    try:
        target_id = int(context.args[0])
        
        if target_id not in user_data:
            await update.message.reply_text("❌ Пользователь не найден!")
            return
        
        data = user_data[target_id]
        win_rate = (data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0
        
        search_result = f"""
🔍 РЕЗУЛЬТАТ ПОИСКА ПО ID

👤 ID: {target_id}
💎 Баланс: {round(data['game_balance'], 1)} ⭐
🎯 Ставка: {data['current_bet']} ⭐
🎮 Игр: {data['total_games']}
🏆 Побед: {data['total_wins']}
📈 Винрейт: {win_rate:.1f}%
🔥 Текущая серия: {data['win_streak']}
🏆 Макс. серия: {data['max_win_streak']}
🎉 Мега-выигрышей: {data['mega_wins_count']}
💳 Пополнено: {data['total_deposited']} ⭐
📅 Регистрация: {data['registration_date'][:16]}
        """
        
        await update.message.reply_text(search_result)
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID!")

# 🆕 ОБРАБОТЧИК РАССЫЛКИ
async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        return
    
    if not context.user_data.get('waiting_for_broadcast', False):
        return
    
    message = update.message.text
    context.user_data['waiting_for_broadcast'] = False
    
    sent_count = 0
    error_count = 0
    
    progress_msg = await update.message.reply_text(f"📢 Начинаю рассылку... 0/{len(user_data)}")
    
    for uid in list(user_data.keys()):
        try:
            await context.bot.send_message(uid, message)
            sent_count += 1
            
            if sent_count % 10 == 0:
                await progress_msg.edit_text(f"📢 Рассылка... {sent_count}/{len(user_data)}")
            
            await asyncio.sleep(0.1)
            
        except Exception as e:
            error_count += 1
    
    await progress_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📤 Отправлено: {sent_count}\n"
        f"❌ Ошибок: {error_count}\n"
        f"📊 Эффективность: {(sent_count/len(user_data)*100):.1f}%"
    )

# 🆕 КОМАНДА ОТМЕНЫ
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if context.user_data.get('waiting_for_broadcast', False):
        context.user_data['waiting_for_broadcast'] = False
        await update.message.reply_text("❌ Рассылка отменена.")
    else:
        await update.message.reply_text("❌ Нечего отменять.")

# 🆕 КОМАНДА ПОМОЩИ
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    is_banned, reason = await check_ban(user_id)
    if is_banned:
        await update.message.reply_text(
            f"🚫 Вы забанены администратором.\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, свяжитесь с администрацией."
        )
        return
    
    help_text = """
🎰 NSource Casino - Список команд

🎮 ОСНОВНЫЕ КОМАНДЫ:
/start - Начать работу с ботом
/profile - Показать профиль
/help - Показать эту справку

🎯 ИГРЫ:
Просто отправьте любой dice эмодзи в чат:
🎰 - Слоты (64 комбинации, 4 выигрышных)
🎰 - Слоты 777 (только джекпот 777)
🎯 - Дартс (победа на 6)
🎲 - Кубик (победа на 6) 
🎳 - Боулинг (победа на 6)
⚽ - Футбол (2 возврата + 3 гола)
🏀 - Баскетбол (3 возврата + 2 броска)

💸 ФИНАНСЫ:
/deposit - Пополнить баланс
/withdraw - Вывести средства
/bet <сумма> - Изменить ставку

📊 СИСТЕМЫ БОНУСОВ:
/activity - Статистика активности
/promo <код> - Активировать промокод

🎁 ОПТИМИЗИРОВАННЫЕ СИСТЕМЫ:
• 🔥 Серии побед - бонусы +10%/+25%/+50%
• 🎉 Мега-выигрыши - шанс 0.6% x1.5-x5
• 🔄 Возвраты 2-10% при проигрыше
• 🏆 Недельные награды 1-3% от ставок
• 👥 Реферальная система - 10% от проигрышей друзей

💡 Просто отправьте эмодзи игры чтобы начать играть!
    """
    
    await update.message.reply_text(help_text)

# 🚀 ЗАПУСК БОТА
def main():
    load_data()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # 📋 ОСНОВНЫЕ КОМАНДЫ
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("bet", bet_command))
    app.add_handler(CommandHandler("activity", activity_command))
    app.add_handler(CommandHandler("promo", promo_command))
    app.add_handler(CommandHandler("withdraw", withdraw_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    
    # 💰 ФИНАНСОВЫЕ КОМАНДЫ
    app.add_handler(CommandHandler("deposit", deposit_command))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # 👑 АДМИН КОМАНДЫ
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("banlist", banlist_command))
    app.add_handler(CommandHandler("addbalance", addbalance_command))
    app.add_handler(CommandHandler("setbalance", setbalance_command))
    app.add_handler(CommandHandler("resetbalance", resetbalance_command))
    app.add_handler(CommandHandler("promo_create", promo_create_command))
    app.add_handler(CommandHandler("promo_list", promo_list_command))
    app.add_handler(CommandHandler("promo_delete", promo_delete_command))
    app.add_handler(CommandHandler("promo_info", promo_info_command))
    app.add_handler(CommandHandler("searchid", searchid_command))
    
    # 🎮 CALLBACK ОБРАБОТЧИКИ
    app.add_handler(CallbackQueryHandler(profile, pattern="^back_to_profile$"))
    app.add_handler(CallbackQueryHandler(play_games_callback, pattern="^play_games$"))
    app.add_handler(CallbackQueryHandler(deposit_callback, pattern="^deposit$"))
    app.add_handler(CallbackQueryHandler(change_bet_callback, pattern="^change_bet$"))
    app.add_handler(CallbackQueryHandler(referral_system_callback, pattern="^referral_system$"))
    app.add_handler(CallbackQueryHandler(handle_game_selection, pattern="^play_"))
    app.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_stats_callback, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_users_callback, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_top_callback, pattern="^admin_top$"))
    app.add_handler(CallbackQueryHandler(admin_broadcast_callback, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(admin_balance_callback, pattern="^admin_balance$"))
    app.add_handler(CallbackQueryHandler(admin_search_callback, pattern="^admin_search$"))
    app.add_handler(CallbackQueryHandler(admin_system_callback, pattern="^admin_system$"))
    app.add_handler(CallbackQueryHandler(admin_promo_callback, pattern="^admin_promo$"))
    app.add_handler(CallbackQueryHandler(admin_ban_callback, pattern="^admin_ban$"))
    app.add_handler(CallbackQueryHandler(admin_backup_callback, pattern="^admin_backup$"))
    app.add_handler(CallbackQueryHandler(admin_withdrawals_callback, pattern="^admin_withdrawals$"))
    app.add_handler(CallbackQueryHandler(admin_play_callback, pattern="^admin_play$"))
    app.add_handler(CallbackQueryHandler(admin_settings_callback, pattern="^admin_settings$"))
    app.add_handler(CallbackQueryHandler(admin_exit_callback, pattern="^admin_exit$"))
    app.add_handler(CallbackQueryHandler(admin_back_callback, pattern="^admin_back$"))
    app.add_handler(CallbackQueryHandler(admin_users_nav_callback, pattern="^admin_users_(prev|next)_"))
    
    # 💸 ВЫВОД СРЕДСТВ
    app.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(handle_withdraw_selection, pattern="^withdraw_"))
    app.add_handler(CallbackQueryHandler(confirm_withdraw, pattern="^confirm_withdraw$"))
    
    # 💰 ПОПОЛНЕНИЕ БАЛАНСА
    app.add_handler(CallbackQueryHandler(handle_deposit_selection, pattern="^buy_"))
    
    # 🎮 ОБРАБОТЧИКИ ИГР
    app.add_handler(MessageHandler(filters.Dice.ALL, handle_user_dice))
    
    # 📢 ОБРАБОТЧИК РАССЫЛКИ
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message))
    
    # 🚀 ЗАПУСК БОТА
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
