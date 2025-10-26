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
    "🎰": 2.2,  # Слоты - самая долгая анимация
    "🎯": 2.6,  # Дартс
    "🎲": 2.8,  # Кубик
    "🎳": 3.0,  # Боулинг
    "⚽": 2.8,  # Футбол
    "🏀": 2.8   # Баскетбол
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

# 🎮 БАЗОВЫЕ ВЫИГРЫШИ ДЛЯ СТАВКИ 1 ⭐ (ОБНОВЛЕННЫЕ ДЛЯ СЛОТОВ)
BASE_PRIZES = {
    "🎰": {
        "ТРИ БАРА": 5,
        "ТРИ ВИШНИ": 10, 
        "ТРИ ЛИМОНА": 15,
        "ДЖЕКПОТ 777": 20
    },
    "🎯": {"ПОПАДАНИЕ В ЦЕЛЬ": 3},
    "🎲": {"ВЫПАЛО 6": 3},
    "🎳": {"СТРАЙК": 3},
    "⚽": {"ГОООЛ": 3},
    "🏀": {"ПОПАДАНИЕ": 3}
}

# 🎮 ПОЛНАЯ КОНФИГУРАЦИЯ ИГР (ВСЕ 64 КОМБИНАЦИИ ДЛЯ СЛОТОВ) - ОБНОВЛЕННЫЕ ПРИЗЫ
GAMES_CONFIG = {
    "🎰": {
        "values": {
            # ОБЫЧНЫЕ СЛОТЫ - 64 значения, 4 выигрышных с ОБНОВЛЕННЫМИ ПРИЗАМИ
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
            43: {"win": True, "base_prize": BASE_PRIZES["🎰"]["ТРИ ЛИМОНА"], "message": "🎰 ТРИ ЛИМОНА! Выигрыш: {prize} ⭐"},
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
            # ФУТБОЛ - 5 значений, 1 выигрышное (5)
            1: {"win": False, "base_prize": 0, "message": "⚽ - проигрыш"},
            2: {"win": False, "base_prize": 0, "message": "⚽ - проигрыш"},
            3: {"win": False, "base_prize": 0, "message": "⚽ - проигрыш"},
            4: {"win": False, "base_prize": 0, "message": "⚽ - проигрыш"},
            5: {"win": True, "base_prize": BASE_PRIZES["⚽"]["ГОООЛ"], "message": "⚽ - ГОООЛ! Выигрыш: {prize} ⭐"}
        }
    },
    "🏀": {
        "values": {
            # БАСКЕТБОЛ - 5 значений, 1 выигрышное (5)
            1: {"win": False, "base_prize": 0, "message": "🏀 - проигрыш"},
            2: {"win": False, "base_prize": 0, "message": "🏀 - проигрыш"},
            3: {"win": False, "base_prize": 0, "message": "🏀 - проигрыш"},
            4: {"win": False, "base_prize": 0, "message": "🏀 - проигрыш"},
            5: {"win": True, "base_prize": BASE_PRIZES["🏀"]["ПОПАДАНИЕ"], "message": "🏀 - ПОПАДАНИЕ! Выигрыш: {prize} ⭐"}
        }
    }
}

# 🎮 КОНФИГУРАЦИЯ ДЛЯ СЛОТОВ 777 (ТОЛЬКО ДЖЕКПОТ)
SLOTS_777_CONFIG = {
    "🎰": {
        "values": {
            # СЛОТЫ 777 - 64 значения, ТОЛЬКО 1 выигрышное (64) с увеличенным призом
            1: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            2: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            3: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            4: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            5: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            6: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            7: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            8: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            9: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            10: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            11: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            12: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            13: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            14: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            15: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            16: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            17: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            18: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            19: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            20: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            21: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            22: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            23: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            24: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            25: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            26: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            27: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            28: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            29: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            30: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            31: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            32: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            33: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            34: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            35: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            36: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            37: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            38: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            39: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            40: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            41: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            42: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            43: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            44: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            45: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            46: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            47: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            48: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            49: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            50: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            51: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            52: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            53: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            54: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            55: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            56: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            57: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            58: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            59: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            60: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            61: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            62: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            63: {"win": False, "base_prize": 0, "message": "🎰 - проигрыш"},
            64: {"win": True, "base_prize": 50, "message": "🎰 ДЖЕКПОТ 777! МЕГА ВЫИГРЫШ: {prize} ⭐"}  # 50x ставки
        }
    }
}

# 🗃️ БАЗА ДАННЫХ
user_data = defaultdict(lambda: {
    'game_balance': 0,
    'total_games': 0,
    'total_wins': 0,
    'total_deposited': 0,
    'real_money_spent': 0,
    'current_bet': 5,
    'registration_date': datetime.datetime.now().isoformat(),
    'last_activity': datetime.datetime.now().isoformat()
})

user_activity = defaultdict(lambda: {
    'last_play_date': None,
    'consecutive_days': 0,
    'plays_today': 0,
    'weekly_reward_claimed': False
})

consecutive_wins = defaultdict(int)
admin_mode = defaultdict(bool)
user_sessions = defaultdict(dict)
withdrawal_requests = defaultdict(list)

# 💾 СОХРАНЕНИЕ ДАННЫХ
def save_data():
    try:
        data = {
            'user_data': dict(user_data),
            'user_activity': dict(user_activity),
            'consecutive_wins': dict(consecutive_wins),
            'admin_mode': dict(admin_mode),
            'withdrawal_requests': dict(withdrawal_requests)
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
            consecutive_wins.update(data.get('consecutive_wins', {}))
            admin_mode.update(data.get('admin_mode', {}))
            withdrawal_requests.update(data.get('withdrawal_requests', {}))
    except FileNotFoundError:
        pass

# 🎁 СИСТЕМА АКТИВНОСТИ
WEEKLY_REWARDS = [15, 25, 50]

def update_daily_activity(user_id: int):
    today = datetime.datetime.now().date()
    activity = user_activity[user_id]
    
    if activity['last_play_date'] != str(today):
        if activity['last_play_date']:
            last_play = datetime.datetime.fromisoformat(activity['last_play_date']).date()
            if (today - last_play).days == 1 and activity['plays_today'] >= 3:
                activity['consecutive_days'] += 1
            elif (today - last_play).days > 1:
                activity['consecutive_days'] = 0
        else:
            activity['consecutive_days'] = 0
        
        activity['plays_today'] = 0
        activity['last_play_date'] = str(today)
        activity['weekly_reward_claimed'] = False
    
    activity['plays_today'] += 1
    
    # Проверяем условие для недельной награды
    if (activity['consecutive_days'] >= 7 and 
        activity['plays_today'] >= 3 and 
        not activity['weekly_reward_claimed']):
        
        reward = random.choice(WEEKLY_REWARDS)
        user_data[user_id]['game_balance'] += reward
        activity['consecutive_days'] = 0
        activity['weekly_reward_claimed'] = True
        save_data()
        return reward
    
    return None

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🎰 NSource Casino

Добро пожаловать в казино!

Доступные игры (ставка от 1 до 100000 ⭐):
🎰 Слоты - 64 комбинации, 4 выигрышных (5-20x ставки)
🎰 Слоты 777 - только джекпот 777 (50x ставки)
🎯 Дартс - победа на 6 (3x ставки)
🎲 Кубик - победа на 6 (3x ставки)
🎳 Боулинг - победа на 6 (3x ставки)
⚽ Футбол - победа на 5 (3x ставки)
🏀 Баскетбол - победа на 5 (3x ставки)

💰 Пополнение: 1:1
1 реальная звезда = 1 ⭐

🎁 Система активности:
Играй 3+ раза в день 7 дней подряд = случайный подарок (15-50 ⭐)

Просто отправь любой dice эмодзи игры чтобы начать играть!
    """
    
    keyboard = [
        [InlineKeyboardButton("🎮 Играть", callback_data="play_games")],
        [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")],
        [InlineKeyboardButton("💰 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("🎯 Изменить ставку", callback_data="change_bet")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    data = user_data[user_id]
    
    win_rate = (data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0
    
    profile_text = f"""
📊 Личный кабинет

👤 Имя: {user.first_name}
🆔 ID: {user_id}
📅 Регистрация: {data['registration_date'][:10]}

💎 Статистика:
💰 Баланс: {data['game_balance']} ⭐
🎯 Текущая ставка: {data['current_bet']} ⭐
🎮 Всего игр: {data['total_games']}
🏆 Побед: {data['total_wins']}
📈 Винрейт: {win_rate:.1f}%
💳 Пополнено: {data['total_deposited']} ⭐
    """
    
    keyboard = [
        [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit"),
         InlineKeyboardButton("💸 Вывести ⭐", callback_data="withdraw")],
        [InlineKeyboardButton("🎮 Играть", callback_data="play_games")],
        [InlineKeyboardButton("🎯 Изменить ставку", callback_data="change_bet")]
    ]
    
    if admin_mode.get(user_id, False):
        keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(profile_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(profile_text, reply_markup=reply_markup)

# 💸 СИСТЕМА ВЫВОДА СРЕДСТВ
async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для вывода средств"""
    user_id = update.effective_user.id
    balance = user_data[user_id]['game_balance']
    
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
    balance = user_data[user_id]['game_balance']
    
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
    balance = user_data[user_id]['game_balance']
    
    if balance < amount:
        await query.edit_message_text(
            "❌ Недостаточно средств!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="withdraw")]
            ])
        )
        return
    
    # Сохраняем выбранную сумму в контексте
    context.user_data['withdraw_amount'] = amount
    context.user_data['withdraw_user_id'] = user_id
    
    # Рассчитываем количество подарков
    gifts_count = amount // 15  # 1 подарок за каждые 15 звезд
    gifts_count = max(1, gifts_count)  # минимум 1 подарок
    
    confirm_text = f"""
✅ Подтверждение вывода

💸 Сумма вывода: {amount} ⭐
🎁 Количество подарков: {gifts_count}

💰 Баланс до списания: {balance} ⭐
💰 Баланс после списания: {balance - amount} ⭐

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
    
    # Списываем средства
    user_data[user_id]['game_balance'] -= amount
    
    # Рассчитываем количество подарков
    gifts_count = amount // 15
    gifts_count = max(1, gifts_count)
    
    # Создаем заявку на вывод
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
    
    # Отправляем подтверждение
    success_text = f"""
🎉 Вывод успешно обработан!

💸 Списано: {amount} ⭐
🎁 Отправлено подарков: {gifts_count}
💰 Текущий баланс: {user_data[user_id]['game_balance']} ⭐

📦 Ваши подарки уже отправлены! Проверьте раздел "Подарки" в Telegram.

Благодарим за игру! 🎰
    """
    
    keyboard = [
        [InlineKeyboardButton("🎮 Продолжить играть", callback_data="play_games")],
        [InlineKeyboardButton("📊 Профиль", callback_data="back_to_profile")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(success_text, reply_markup=reply_markup)
    
    # Логируем вывод для админа
    print(f"💰 ВЫВОД: Пользователь {user_id} вывел {amount} ⭐, отправлено {gifts_count} подарков")

# 🎯 КОМАНДА ДЛЯ ИЗМЕНЕНИЯ СТАВКИ
async def bet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
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

# 📊 КОМАНДА АКТИВНОСТИ
async def activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    activity_data = user_activity[user_id]
    
    today = datetime.datetime.now().date()
    plays_remaining = max(0, 3 - activity_data['plays_today'])
    
    activity_text = f"""
📊 Ваша активность

🎮 Сыграно сегодня: {activity_data['plays_today']}/3
📅 Последовательных дней: {activity_data['consecutive_days']}/7
⏳ Осталось игр для зачета: {plays_remaining}

🎁 Играйте 3+ раза в день 7 дней подряд для получения бонуса!
    """
    
    if activity_data['weekly_reward_claimed']:
        activity_text += "\n✅ Еженедельная награда уже получена!"
    
    await update.message.reply_text(activity_text)

# 💰 СИСТЕМА ПОПОЛНЕНИЯ
async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    
    deposit_text = f"""
💰 Пополнение баланса

💎 Текущий баланс: {data['game_balance']} ⭐

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

# 💰 CALLBACK ДЛЯ ПОПОЛНЕНИЯ
async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    current_balance = user_data[user_id]['game_balance']
    
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

# 🛒 ОБРАБОТЧИК ВЫБОРА ПРОДУКТА
async def handle_deposit_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
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
        f"💰 Баланс: {user_data[user_id]['game_balance']} ⭐\n\n"
        f"🎮 Приятной игры!"
    )

# 🎮 СИСТЕМА ИГР С ЗАДЕРЖКОЙ РЕЗУЛЬТАТА
async def play_games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    balance = user_data[user_id]['game_balance']
    current_bet = user_data[user_id]['current_bet']
    
    games_text = f"""
🎮 Выбор игры

💎 Баланс: {balance} ⭐
🎯 Текущая ставка: {current_bet} ⭐
📊 Диапазон ставки: {MIN_BET}-{MAX_BET} ⭐

Выберите игру или просто отправь любой dice эмодзи в чат!
    """
    
    keyboard = [
        [InlineKeyboardButton("🎰 Слоты (4 выигрыша)", callback_data="play_slots")],
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
    await query.edit_message_text(games_text, reply_markup=reply_markup)

async def handle_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    game_type = query.data.replace("play_", "")
    current_bet = user_data[user_id]['current_bet']
    
    # ПРОВЕРКА БАЛАНСА
    if user_data[user_id]['game_balance'] < current_bet and not admin_mode.get(user_id, False):
        await query.edit_message_text(
            "❌ Недостаточно средств!\n\n"
            f"💰 Ваш баланс: {user_data[user_id]['game_balance']} ⭐\n"
            f"🎯 Требуется: {current_bet} ⭐\n\n"
            "💳 Пополните баланс чтобы играть!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
                [InlineKeyboardButton("🎯 Изменить ставку", callback_data="change_bet")],
                [InlineKeyboardButton("📊 Личный кабинет", callback_data="back_to_profile")]
            ])
        )
        return
    
    # СПИСАНИЕ СРЕДСТВ
    if not admin_mode.get(user_id, False):
        user_data[user_id]['game_balance'] -= current_bet
    
    user_data[user_id]['total_games'] += 1
    user_data[user_id]['last_activity'] = datetime.datetime.now().isoformat()
    
    game_emojis = {
        'slots': '🎰', 
        'slots777': '🎰',  # Тот же эмодзи слотов
        'dart': '🎯', 
        'dice': '🎲',
        'bowling': '🎳', 
        'football': '⚽', 
        'basketball': '🏀'
    }
    
    emoji = game_emojis.get(game_type, '🎰')
    
    # Сохраняем информацию о текущей игре
    user_sessions[user_id] = {
        'game_type': game_type,
        'emoji': emoji,
        'bet': current_bet if not admin_mode.get(user_id, False) else 0,
        'message_id': query.message.message_id,
        'chat_id': query.message.chat_id
    }
    
    # Отправляем dice от имени бота
    dice_message = await context.bot.send_dice(chat_id=query.message.chat_id, emoji=emoji)
    
    # Ждем соответствующее время перед показом результата
    delay = DICE_DELAYS.get(emoji, 3.0)
    await asyncio.sleep(delay)
    
    # Обрабатываем результат после задержки
    await process_dice_result(user_id, emoji, dice_message.dice.value, current_bet if not admin_mode.get(user_id, False) else 0, dice_message, context, game_type)
    
    save_data()

# 🎰 ОБРАБОТКА DICE ОТ ПОЛЬЗОВАТЕЛЯ С ЗАДЕРЖКОЙ
async def handle_user_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = update.effective_user.id
    
    if not message.dice:
        return
    
    emoji = message.dice.emoji
    value = message.dice.value
    
    # Проверяем, что это поддерживаемая игра
    if emoji not in GAMES_CONFIG:
        return
    
    current_bet = user_data[user_id]['current_bet']
    
    # ПРОВЕРКА БАЛАНСА
    if user_data[user_id]['game_balance'] < current_bet and not admin_mode.get(user_id, False):
        await message.reply_text(
            f"❌ Недостаточно средств!\n\n"
            f"💰 Ваш баланс: {user_data[user_id]['game_balance']} ⭐\n"
            f"🎯 Требуется: {current_bet} ⭐\n\n"
            "💳 Пополните баланс чтобы играть!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
                [InlineKeyboardButton("🎯 Изменить ставку", callback_data="change_bet")]
            ])
        )
        return
    
    # СПИСАНИЕ СРЕДСТВ
    cost = current_bet if not admin_mode.get(user_id, False) else 0
    if not admin_mode.get(user_id, False):
        user_data[user_id]['game_balance'] -= cost
    
    user_data[user_id]['total_games'] += 1
    user_data[user_id]['last_activity'] = datetime.datetime.now().isoformat()
    
    # Сохраняем информацию о текущей игре
    user_sessions[user_id] = {
        'game_type': 'slots',  # По умолчанию обычные слоты
        'emoji': emoji,
        'bet': cost,
        'message_id': message.message_id,
        'chat_id': message.chat_id
    }
    
    # Ждем соответствующее время перед показом результата
    delay = DICE_DELAYS.get(emoji, 3.0)
    await asyncio.sleep(delay)
    
    # Обрабатываем результат после задержки
    await process_dice_result(user_id, emoji, value, cost, message, context, 'slots')
    
    save_data()

# 🎯 ОБРАБОТКА РЕЗУЛЬТАТА DICE С ПРОПОРЦИОНАЛЬНЫМИ ВЫИГРЫШАМИ
async def process_dice_result(user_id: int, emoji: str, value: int, cost: int, message, context: ContextTypes.DEFAULT_TYPE, game_type='slots'):
    # Выбираем правильную конфигурацию в зависимости от типа игры
    if game_type == 'slots777':
        game_config = SLOTS_777_CONFIG.get(emoji)
    else:
        game_config = GAMES_CONFIG.get(emoji)
        
    if not game_config:
        return
    
    # Получаем результат для этого значения
    result_config = game_config["values"].get(value)
    if not result_config:
        result_config = {"win": False, "base_prize": 0, "message": f"{emoji} - проигрыш"}
    
    # ВЫЧИСЛЯЕМ РЕАЛЬНЫЙ ВЫИГРЫШ НА ОСНОВЕ СТАВКИ
    actual_prize = result_config["base_prize"] * (cost if not admin_mode.get(user_id, False) else user_data[user_id]['current_bet'])
    
    result_text = ""
    
    if result_config["win"]:
        # ВЫИГРЫШ
        user_data[user_id]['game_balance'] += actual_prize
        user_data[user_id]['total_wins'] += 1
        
        # Форматируем сообщение с реальным выигрышем
        win_message = result_config["message"].format(prize=actual_prize)
        
        result_text = (
            f"{win_message}\n\n"
            f"💎 Текущий баланс: {user_data[user_id]['game_balance']} ⭐\n"
            f"📊 (Списано: {cost} ⭐ + Выигрыш: {actual_prize} ⭐)"
        )
    else:
        # ПРОИГРЫШ
        result_text = (
            f"{result_config['message']}\n\n"
            f"💎 Текущий баланс: {user_data[user_id]['game_balance']} ⭐\n"
            f"📊 (Списано: {cost} ⭐)"
        )
    
    # Отправляем результат
    await message.reply_text(result_text)
    
    # 📊 ОБНОВЛЕНИЕ АКТИВНОСТИ
    weekly_reward = update_daily_activity(user_id)
    if weekly_reward:
        user_data[user_id]['game_balance'] += weekly_reward
        await message.reply_text(
            f"🎁 ЕЖЕНЕДЕЛЬНАЯ НАГРАДА!\n\n"
            f"💰 Награда: {weekly_reward} ⭐\n"
            f"💎 Баланс: {user_data[user_id]['game_balance']} ⭐"
        )

# 🎯 CALLBACK ДЛЯ ИЗМЕНЕНИЯ СТАВКИ
async def change_bet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
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

# 🔙 CALLBACK ДЛЯ ВОЗВРАТА В ПРОФИЛЬ
async def back_to_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await profile(update, context)

# 👑 АДМИН СИСТЕМА - СКРЫТАЯ
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if len(context.args) == 0:
        # Не показываем никакой информации если код не указан
        return
    
    code = context.args[0]
    if code == ADMIN_CODE:
        admin_mode[user_id] = True
        await update.message.reply_text(
            "👑 РЕЖИМ АДМИНИСТРАТОРА АКТИВИРОВАН!\n\n"
            "✨ Теперь вам доступны все админ-команды.\n"
            "🎮 Используйте кнопки в профиле для быстрого доступа к админ-панели!"
        )
    else:
        # Не показываем сообщение о неверном коде
        return

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    total_users = len(user_data)
    total_games = sum(data['total_games'] for data in user_data.values())
    total_balance = sum(data['game_balance'] for data in user_data.values())
    total_deposited = sum(data['total_deposited'] for data in user_data.values())
    
    admin_text = f"""
👑 АДМИН ПАНЕЛЬ - ПАНЕЛЬ УПРАВЛЕНИЯ

📊 ОСНОВНАЯ СТАТИСТИКА:
👤 Пользователей: {total_users}
🎮 Всего игр: {total_games}
💎 Общий баланс: {total_balance} ⭐
💳 Пополнено всего: {total_deposited} ⭐

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

# 📊 РАСШИРЕННАЯ СТАТИСТИКА
async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    total_users = len(user_data)
    total_games = sum(data['total_games'] for data in user_data.values())
    total_wins = sum(data['total_wins'] for data in user_data.values())
    total_balance = sum(data['game_balance'] for data in user_data.values())
    total_deposited = sum(data['total_deposited'] for data in user_data.values())
    total_real_money = sum(data['real_money_spent'] for data in user_data.values())
    
    # Статистика по играм
    game_stats = defaultdict(int)
    for data in user_data.values():
        game_stats['total_bet'] += data.get('current_bet', 0) * data.get('total_games', 0)
    
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
    
    # Самый богатый пользователь
    richest_user = max(user_data.items(), key=lambda x: x[1]['game_balance'], default=(0, {'game_balance': 0}))
    # Самый активный пользователь
    most_active = max(user_data.items(), key=lambda x: x[1]['total_games'], default=(0, {'total_games': 0}))
    
    stats_text = f"""
📊 ДЕТАЛЬНАЯ СТАТИСТИКА БОТА

👥 ПОЛЬЗОВАТЕЛИ:
• Всего пользователей: {total_users}
• Новые за сегодня: {len([uid for uid, data in user_data.items() if datetime.datetime.fromisoformat(data['last_activity']).date() == datetime.datetime.now().date()])}

🎮 ИГРОВАЯ СТАТИСТИКА:
• Всего игр: {total_games}
• Всего побед: {total_wins}
• Общий винрейт: {win_rate:.1f}%
• Средняя ставка: {game_stats['total_bet'] // total_games if total_games > 0 else 0} ⭐

💰 ФИНАНСЫ:
• Общий баланс: {total_balance} ⭐
• Пополнено всего: {total_deposited} ⭐
• Реальные деньги: {total_real_money} Stars
• Прибыль: {total_real_money - total_balance} Stars

🏆 РЕКОРДЫ:
• Самый богатый: {richest_user[0]} ({richest_user[1]['game_balance']} ⭐)
• Самый активный: {most_active[0]} ({most_active[1]['total_games']} игр)
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
    
    # Показываем пользователей с пагинацией
    page = int(context.user_data.get('admin_users_page', 0))
    users_per_page = 8
    all_users = list(user_data.items())
    total_pages = (len(all_users) + users_per_page - 1) // users_per_page
    
    start_idx = page * users_per_page
    end_idx = start_idx + users_per_page
    page_users = all_users[start_idx:end_idx]
    
    users_text = f"👥 СПИСОК ПОЛЬЗОВАТЕЛЕЙ (Страница {page + 1}/{total_pages})\n\n"
    
    for i, (uid, data) in enumerate(page_users, start_idx + 1):
        users_text += f"{i}. ID: {uid} | 💰: {data['game_balance']} ⭐ | 🎮: {data['total_games']}\n"
    
    keyboard = []
    # Кнопки пагинации
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
    
    # Топ по балансу
    top_balance = sorted(user_data.items(), key=lambda x: x[1]['game_balance'], reverse=True)[:10]
    # Топ по играм
    top_games = sorted(user_data.items(), key=lambda x: x[1]['total_games'], reverse=True)[:10]
    # Топ по выигрышам
    top_wins = sorted(user_data.items(), key=lambda x: x[1]['total_wins'], reverse=True)[:10]
    
    top_text = "🏆 ТОП ИГРОКОВ\n\n"
    
    top_text += "💰 ПО БАЛАНСУ:\n"
    for i, (uid, data) in enumerate(top_balance, 1):
        top_text += f"{i}. ID: {uid} - {data['game_balance']} ⭐\n"
    
    top_text += "\n🎮 ПО КОЛИЧЕСТВУ ИГР:\n"
    for i, (uid, data) in enumerate(top_games, 1):
        top_text += f"{i}. ID: {uid} - {data['total_games']} игр\n"
    
    top_text += "\n🏆 ПО ПОБЕДАМ:\n"
    for i, (uid, data) in enumerate(top_wins, 1):
        win_rate = (data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0
        top_text += f"{i}. ID: {uid} - {data['total_wins']} побед ({win_rate:.1f}%)\n"
    
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

Примеры:
/searchid 123456789
/searchname John
/searchbalance 100 1000
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
    
    import psutil
    import platform
    
    # Исправленное вычисление времени работы
    registration_dates = [datetime.datetime.fromisoformat(data['registration_date']) for data in user_data.values()]
    if registration_dates:
        start_time = min(registration_dates)
        uptime = datetime.datetime.now() - start_time
    else:
        uptime = datetime.timedelta(0)
    
    # Системная информация
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
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_system")],
        [InlineKeyboardButton("💾 Резервная копия", callback_data="admin_backup")],
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(system_info, reply_markup=reply_markup)

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

/promo create <код> <сумма> <использований> - Создать промокод
/promo delete <код> - Удалить промокод
/promo list - Список промокодов
/promo stats <код> - Статистика промокода

Пример:
/promo create SUMMER2024 100 50
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
    
    # Создаем резервную копию
    save_data()
    backup_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    backup_text = f"""
💾 РЕЗЕРВНАЯ КОПИЯ

✅ Резервная копия создана успешно!
🕐 Время создания: {backup_time}

📊 Данные в резервной копии:
• Пользователей: {len(user_data)}
• Игр: {sum(data['total_games'] for data in user_data.values())}
• Общий баланс: {sum(data['game_balance'] for data in user_data.values())} ⭐

Для восстановления из резервной копии используйте команду /restore
    """
    
    keyboard = [
        [InlineKeyboardButton("📥 Скачать backup", callback_data="admin_download_backup")],
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
        await query.edit_message_text("📭 Заявок на вывод нет")
        return
    
    total_withdrawals = 0
    withdrawals_text = "📋 Список заявок на вывод:\n\n"
    
    for uid, requests in withdrawal_requests.items():
        for req in requests:
            total_withdrawals += req['amount']
            withdrawals_text += f"👤 User: {uid}\n"
            withdrawals_text += f"💸 Сумма: {req['amount']} ⭐\n"
            withdrawals_text += f"🎁 Подарков: {req['gifts_count']}\n"
            withdrawals_text += f"⏰ Время: {req['timestamp'][:16]}\n"
            withdrawals_text += f"📊 Статус: {req['status']}\n"
            withdrawals_text += "─" * 30 + "\n"
    
    withdrawals_text += f"\n💰 Всего выведо: {total_withdrawals} ⭐"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(withdrawals_text, reply_markup=reply_markup)

# 📥 СКАЧИВАНИЕ БЭКАПА
async def admin_download_backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    # Создаем временную копию файла для отправки
    backup_filename = f"backup_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    
    with open('data.json', 'rb') as file:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=file,
            filename=backup_filename,
            caption=f"📊 Backup данных бота\n🕐 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    await query.message.reply_text("✅ Backup успешно отправлен!")

# 🎮 АДМИНСКИЕ ИГРЫ
async def admin_play_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    games_text = "👑 АДМИН - БЕСПЛАТНЫЕ ИГРЫ\n\n🎮 Выберите игру:"
    
    keyboard = [
        [InlineKeyboardButton("🎰 Слоты (БЕСПЛАТНО)", callback_data="admin_play_slots")],
        [InlineKeyboardButton("🎰 Слоты 777 (БЕСПЛАТНО)", callback_data="admin_play_slots777")],
        [InlineKeyboardButton("🎯 Дартс (БЕСПЛАТНО)", callback_data="admin_play_dart")],
        [InlineKeyboardButton("🎲 Кубик (БЕСПЛАТНО)", callback_data="admin_play_dice")],
        [InlineKeyboardButton("🎳 Боулинг (БЕСПЛАТНО)", callback_data="admin_play_bowling")],
        [InlineKeyboardButton("⚽ Футбол (БЕСПЛАТНО)", callback_data="admin_play_football")],
        [InlineKeyboardButton("🏀 Баскетбол (БЕСПЛАТНО)", callback_data="admin_play_basketball")],
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(games_text, reply_markup=reply_markup)

# ⚙️ АДМИНСКИЕ НАСТРОЙКИ
async def admin_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    settings_text = """
⚙️ НАСТРОЙКИ АДМИНИСТРАТОРА

Здесь можно настроить различные параметры бота.

Функционал в разработке...
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(settings_text, reply_markup=reply_markup)

# ❌ ВЫХОД ИЗ АДМИНКИ
async def admin_exit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    admin_mode[user_id] = False
    await query.edit_message_text("👑 Режим админа деактивирован")

# 🆕 НОВЫЕ АДМИН КОМАНДЫ
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats для быстрой статистики"""
    user_id = update.effective_user.id
    if not admin_mode.get(user_id, False):
        return
    
    await admin_stats_callback(update, context)

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /users для списка пользователей"""
    user_id = update.effective_user.id
    if not admin_mode.get(user_id, False):
        return
    
    await admin_users_callback(update, context)

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /top для топа игроков"""
    user_id = update.effective_user.id
    if not admin_mode.get(user_id, False):
        return
    
    await admin_top_callback(update, context)

# 👑 АДМИН КОМАНДА ДЛЯ ПОПОЛНЕНИЯ БАЛАНСА
async def add_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("""
💰 Пополнение баланса пользователя

Использование: /addbalance <user_id> <amount>

Примеры:
/addbalance 123456789 1000 - пополнить баланс на 1000 ⭐
/addbalance 123456789 500 - пополнить баланс на 500 ⭐
        """)
        return
    
    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Ошибка: user_id и amount должны быть числами")
        return
    
    if target_user_id not in user_data:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    user_data[target_user_id]['game_balance'] += amount
    user_data[target_user_id]['total_deposited'] += amount
    
    save_data()
    
    await update.message.reply_text(
        f"✅ Баланс пользователя {target_user_id} пополнен на {amount} ⭐\n"
        f"💰 Новый баланс: {user_data[target_user_id]['game_balance']} ⭐"
    )

async def set_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("""
💳 Установка баланса пользователя

Использование: /setbalance <user_id> <amount>

Примеры:
/setbalance 123456789 5000 - установить баланс 5000 ⭐
/setbalance 123456789 0 - обнулить баланс
        """)
        return
    
    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Ошибка: user_id и amount должны быть числами")
        return
    
    if target_user_id not in user_data:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    old_balance = user_data[target_user_id]['game_balance']
    user_data[target_user_id]['game_balance'] = amount
    
    save_data()
    
    await update.message.reply_text(
        f"✅ Баланс пользователя {target_user_id} изменен\n"
        f"💰 Было: {old_balance} ⭐\n"
        f"💰 Стало: {amount} ⭐"
    )

async def reset_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("""
🔄 Сброс баланса пользователя

Использование: /resetbalance <user_id>

Пример:
/resetbalance 123456789 - сбросить баланс пользователя до 0
        """)
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Ошибка: user_id должен быть числом")
        return
    
    if target_user_id not in user_data:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    old_balance = user_data[target_user_id]['game_balance']
    user_data[target_user_id]['game_balance'] = 0
    
    save_data()
    
    await update.message.reply_text(
        f"✅ Баланс пользователя {target_user_id} сброшен\n"
        f"💰 Было: {old_balance} ⭐\n"
        f"💰 Стало: 0 ⭐"
    )

async def search_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("""
🔍 Поиск пользователя по ID

Использование: /searchid <user_id>

Пример:
/searchid 123456789 - найти пользователя с ID 123456789
        """)
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Ошибка: user_id должен быть числом")
        return
    
    if target_user_id not in user_data:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    data = user_data[target_user_id]
    win_rate = (data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0
    
    user_info = f"""
📋 Информация о пользователе

🆔 ID: {target_user_id}
📅 Регистрация: {data['registration_date'][:10]}
⏰ Последняя активность: {data['last_activity'][:16]}

💎 Статистика:
💰 Баланс: {data['game_balance']} ⭐
🎯 Текущая ставка: {data['current_bet']} ⭐
🎮 Всего игр: {data['total_games']}
🏆 Побед: {data['total_wins']}
📈 Винрейт: {win_rate:.1f}%
💳 Пополнено: {data['total_deposited']} ⭐
💵 Потрачено реальных: {data['real_money_spent']} Stars
    """
    
    await update.message.reply_text(user_info)

async def reset_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("""
🔄 Полный сброс пользователя

Использование: /resetuser <user_id>

ВНИМАНИЕ: Эта команда полностью сбрасывает все данные пользователя!

Пример:
/resetuser 123456789 - полный сброс пользователя
        """)
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Ошибка: user_id должен быть числом")
        return
    
    if target_user_id not in user_data:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    # Сохраняем старые данные для лога
    old_data = user_data[target_user_id].copy()
    
    # Сбрасываем пользователя
    user_data[target_user_id] = {
        'game_balance': 0,
        'total_games': 0,
        'total_wins': 0,
        'total_deposited': 0,
        'real_money_spent': 0,
        'current_bet': 5,
        'registration_date': datetime.datetime.now().isoformat(),
        'last_activity': datetime.datetime.now().isoformat()
    }
    
    save_data()
    
    await update.message.reply_text(
        f"✅ Пользователь {target_user_id} полностью сброшен\n\n"
        f"📊 Было:\n"
        f"💰 Баланс: {old_data['game_balance']} ⭐\n"
        f"🎮 Игр: {old_data['total_games']}\n"
        f"🏆 Побед: {old_data['total_wins']}\n"
        f"💳 Пополнено: {old_data['total_deposited']} ⭐"
    )

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("""
🚫 Бан пользователя

Использование: /ban <user_id> <причина>

Примеры:
/ban 123456789 Мошенничество
/ban 123456789 Нарушение правил чата
/ban 123456789 Спам
        """)
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Ошибка: user_id должен быть числом")
        return
    
    reason = ' '.join(context.args[1:])
    
    if target_user_id not in user_data:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    # Здесь должна быть логика бана (добавление в список забаненных)
    # В демо-версии просто отправляем сообщение
    
    await update.message.reply_text(
        f"✅ Пользователь {target_user_id} забанен\n"
        f"📝 Причина: {reason}\n\n"
        f"💡 Для разбана используйте /unban {target_user_id}"
    )

async def withdrawals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        return
    
    if not withdrawal_requests:
        await update.message.reply_text("📭 Заявок на вывод нет")
        return
    
    total_withdrawals = 0
    withdrawals_text = "📋 Список заявок на вывод:\n\n"
    
    for uid, requests in withdrawal_requests.items():
        for req in requests:
            total_withdrawals += req['amount']
            withdrawals_text += f"👤 User: {uid}\n"
            withdrawals_text += f"💸 Сумма: {req['amount']} ⭐\n"
            withdrawals_text += f"🎁 Подарков: {req['gifts_count']}\n"
            withdrawals_text += f"⏰ Время: {req['timestamp'][:16]}\n"
            withdrawals_text += f"📊 Статус: {req['status']}\n"
            withdrawals_text += "─" * 30 + "\n"
    
    withdrawals_text += f"\n💰 Всего выведено: {total_withdrawals} ⭐"
    
    await update.message.reply_text(withdrawals_text)

# 🔧 ОБРАБОТЧИК РАССЫЛКИ
async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False) or not context.user_data.get('waiting_for_broadcast'):
        return
    
    message_text = update.message.text
    context.user_data['waiting_for_broadcast'] = False
    
    # Отправляем сообщение о начале рассылки
    progress_msg = await update.message.reply_text("🔄 Начинаю рассылку...")
    
    # Рассылаем сообщение всем пользователям
    success_count = 0
    fail_count = 0
    
    for uid in user_data:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 ОБЪЯВЛЕНИЕ ОТ АДМИНИСТРАЦИИ:\n\n{message_text}"
            )
            success_count += 1
            # Небольшая задержка чтобы не превысить лимиты Telegram
            await asyncio.sleep(0.1)
        except Exception as e:
            fail_count += 1
            print(f"Не удалось отправить сообщение пользователю {uid}: {e}")
    
    await progress_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Результаты:\n"
        f"• Успешно: {success_count}\n"
        f"• Не удалось: {fail_count}\n"
        f"• Всего: {success_count + fail_count}"
    )

# 🔄 ОБРАБОТЧИКИ КНОПОК АДМИНКИ
async def handle_admin_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    callback_data = query.data
    
    if callback_data == 'admin_back':
        await admin_panel(update, context)
    elif callback_data == 'admin_stats':
        await admin_stats_callback(update, context)
    elif callback_data == 'admin_users':
        await admin_users_callback(update, context)
    elif callback_data == 'admin_top':
        await admin_top_callback(update, context)
    elif callback_data == 'admin_broadcast':
        await admin_broadcast_callback(update, context)
    elif callback_data == 'admin_balance':
        await admin_balance_callback(update, context)
    elif callback_data == 'admin_search':
        await admin_search_callback(update, context)
    elif callback_data == 'admin_system':
        await admin_system_callback(update, context)
    elif callback_data == 'admin_promo':
        await admin_promo_callback(update, context)
    elif callback_data == 'admin_ban':
        await admin_ban_callback(update, context)
    elif callback_data == 'admin_backup':
        await admin_backup_callback(update, context)
    elif callback_data == 'admin_withdrawals':
        await admin_withdrawals_callback(update, context)
    elif callback_data == 'admin_download_backup':
        await admin_download_backup_callback(update, context)
    elif callback_data == 'admin_play':
        await admin_play_callback(update, context)
    elif callback_data == 'admin_settings':
        await admin_settings_callback(update, context)
    elif callback_data == 'admin_exit':
        await admin_exit_callback(update, context)
    elif callback_data.startswith('admin_play_'):
        # Обработка админских игр
        await handle_game_selection(update, context)
    elif callback_data.startswith('admin_users_'):
        # Обработка пагинации пользователей
        if 'prev' in callback_data:
            page = int(callback_data.split('_')[-1]) - 1
        else:
            page = int(callback_data.split('_')[-1]) + 1
        context.user_data['admin_users_page'] = page
        await admin_users_callback(update, context)

# 🆘 КОМАНДА ПОМОЩИ
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🎰 *NSource Casino - Помощь*

*Основные команды:*
/start - Начать работу с ботом
/profile - Ваш профиль и статистика  
/deposit - Пополнить баланс
/withdraw - Вывести средства
/activity - Ваша активность
/bet [сумма] - Изменить ставку
/help - Эта справка

*Как играть:*
1. Пополните баланс через /deposit
2. Установите ставку через /bet
3. Отправьте любой dice-эмодзи или используйте кнопки
4. Выигрывайте и увеличивайте баланс!

*Доступные игры:*
🎰 Слоты - 64 комбинации, 4 выигрышных (5-20x ставки)
🎰 Слоты 777 - только джекпот 777 (50x ставки)
🎯 Дартс - Победа на 6 (3x ставки)
🎲 Кубик - Победа на 6 (3x ставки)  
🎳 Боулинг - Победа на 6 (3x ставки)
⚽ Футбол - Победа на 5 (3x ставки)
🏀 Баскетбол - Победа на 5 (3x ставки)

*Вывод средств:*
Минимальная сумма: 15 ⭐
1 подарок за каждые 15 ⭐
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# 🔧 ОБНОВЛЕННЫЙ ОБРАБОТЧИК CALLBACK QUERY
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    callback_data = query.data
    
    # АДМИНСКИЕ КОМАНДЫ
    if callback_data.startswith('admin_'):
        await handle_admin_callback_query(update, context)
    
    # СИСТЕМА ВЫВОДА
    elif callback_data == 'withdraw':
        await withdraw_callback(update, context)
    elif callback_data.startswith('withdraw_'):
        await handle_withdraw_selection(update, context)
    elif callback_data == 'confirm_withdraw':
        await confirm_withdraw(update, context)
    
    # ОСНОВНЫЕ КОМАНДЫ
    elif callback_data == 'play_games':
        await play_games_callback(update, context)
    elif callback_data.startswith('buy_'):
        await handle_deposit_selection(update, context)
    elif callback_data.startswith('play_'):
        await handle_game_selection(update, context)
    elif callback_data == 'deposit':
        await deposit_callback(update, context)
    elif callback_data == 'change_bet':
        await change_bet_callback(update, context)
    elif callback_data == 'back_to_profile':
        await back_to_profile_callback(update, context)

# 🌐 FLASK ДЛЯ RAILWAY
app = Flask(__name__)

@app.route('/')
def home():
    return "🎰 NSource Casino Bot - Полная игровая система с выводом средств!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# 📝 УСТАНОВКА ПОДСКАЗОК КОМАНД (БЕЗ АДМИНКИ)
async def set_bot_commands(application):
    """Установка подсказок команд для бота"""
    commands = [
        ("start", "🚀 Запустить бота"),
        ("profile", "📊 Личный кабинет"),
        ("deposit", "💰 Пополнить баланс"),
        ("withdraw", "💸 Вывести средства"),
        ("activity", "📈 Моя активность"),
        ("bet", "🎯 Изменить ставку"),
        ("help", "🆘 Помощь по командам")
        # Убрали админку из списка команд
    ]
    
    from telegram import BotCommand
    await application.bot.set_my_commands(
        [BotCommand(command, description) for command, description in commands]
    )

# 🚀 ЗАПУСК БОТА
def main():
    load_data()
    
    # Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Установка подсказок команд при запуске
    application.post_init = set_bot_commands
    
    # ОСНОВНЫЕ КОМАНДЫ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CommandHandler("withdraw", withdraw_command))
    application.add_handler(CommandHandler("activity", activity_command))
    application.add_handler(CommandHandler("bet", bet_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # АДМИН КОМАНДЫ (скрытые)
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("addbalance", add_balance_command))
    application.add_handler(CommandHandler("setbalance", set_balance_command))
    application.add_handler(CommandHandler("resetbalance", reset_balance_command))
    application.add_handler(CommandHandler("searchid", search_id_command))
    application.add_handler(CommandHandler("resetuser", reset_user_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("withdrawals", withdrawals_command))
    
    # ДОПОЛНИТЕЛЬНЫЕ АДМИН КОМАНДЫ
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("top", top_command))
    
    # CALLBACK'И
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # ПЛАТЕЖИ
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # СООБЩЕНИЯ - ГЛАВНЫЙ ОБРАБОТЧИК DICE ОТ ПОЛЬЗОВАТЕЛЯ
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_user_dice))
    
    # ОБРАБОТЧИК РАССЫЛКИ
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message))
    
    print("🎰 NSource Casino Bot запущен!")
    print("🎮 Доступные игры: 🎰 🎯 🎲 🎳 ⚽ 🏀")
    print("💰 Система с изменяемой ставкой от 1 до 100000 ⭐!")
    print("💸 Полная система вывода средств!")
    print("👑 Скрытая админ-панель (только по коду)!")
    print("⏱️ Оптимизированные задержки для каждой игры!")
    print("📝 Подсказки команд активированы (без админки)!")
    application.run_polling()

if __name__ == '__main__':
    main()
