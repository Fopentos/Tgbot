import os
import json
import random
import datetime
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

# 🎮 БАЗОВЫЕ ВЫИГРЫШИ ДЛЯ СТАВКИ 1 ⭐
BASE_PRIZES = {
    "🎰": {
        "ТРИ БАРА": 3,
        "ТРИ ВИШНИ": 5, 
        "ТРИ ЛИМОНА": 10,
        "ДЖЕКПОТ 777": 20
    },
    "🎯": {"ПОПАДАНИЕ В ЦЕЛЬ": 3},
    "🎲": {"ВЫПАЛО 6": 3},
    "🎳": {"СТРАЙК": 3},
    "⚽": {"ГОООЛ": 3},
    "🏀": {"ПОПАДАНИЕ": 3}
}

# 🎮 КОНФИГУРАЦИЯ ИГР
GAMES_CONFIG = {
    "🎰": {
        "values": {
            # СЛОТЫ - 64 значения, 4 выигрышных
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

# 🗃️ БАЗА ДАННЫХ
user_data = defaultdict(lambda: {
    'game_balance': 0,
    'total_games': 0,
    'total_wins': 0,
    'total_deposited': 0,
    'real_money_spent': 0,
    'current_bet': 5,  # Ставка по умолчанию
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

# 💾 СОХРАНЕНИЕ ДАННЫХ
def save_data():
    try:
        data = {
            'user_data': dict(user_data),
            'user_activity': dict(user_activity),
            'consecutive_wins': dict(consecutive_wins),
            'admin_mode': dict(admin_mode)
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
    except FileNotFoundError:
        pass

# 🎁 СИСТЕМА АКТИВНОСТИ
WEEKLY_REWARDS = [15, 25, 50]

def update_daily_activity(user_id: int):
    today = datetime.datetime.now().date()
    activity = user_activity[user_id]
    
    if activity['last_play_date'] != today:
        if activity['last_play_date'] and activity['plays_today'] >= 3:
            activity['consecutive_days'] += 1
        elif activity['last_play_date'] and (today - activity['last_play_date']).days > 1:
            activity['consecutive_days'] = 0
        
        activity['plays_today'] = 0
        activity['last_play_date'] = today
    
    activity['plays_today'] += 1
    
    if (activity['consecutive_days'] >= 7 and 
        activity['plays_today'] >= 3 and 
        not activity['weekly_reward_claimed']):
        
        reward = random.choice(WEEKLY_REWARDS)
        activity['consecutive_days'] = 0
        activity['weekly_reward_claimed'] = True
        return reward
    
    return None

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🎰 NSource Casino

Добро пожаловать в казино!

Доступные игры (ставка от 1 до 100000 ⭐):
🎰 Слоты - 64 комбинации, 4 выигрышных (3-20x ставки)
🎯 Дартс - победа на 6 (3x ставки)
🎲 Кубик - победа на 6 (3x ставки)
🎳 Боулинг - победа на 6 (3x ставки)
⚽ Футбол - победа на 5 (3x ставки)
🏀 Баскетбол - победа на 5 (3x ставки)

💰 Пополнение: 1:1
1 реальная звезда = 1 ⭐

🎁 Система активности:
Играй 3+ раза в день 7 дней подряд = случайный подарок (15-50 ⭐)

Команды:
/profile - Личный кабинет
/deposit - Пополнить баланс  
/activity - Моя активность
/bet <сумма> - Изменить ставку

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
        [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
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

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /deposit"""
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

async def activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /activity"""
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

# 💳 СИСТЕМА ПОПОЛНЕНИЯ
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

# 💰 ОБРАБОТКА ПЛАТЕЖЕЙ
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

# 🎮 СИСТЕМА ИГР С ИЗМЕНЯЕМОЙ СТАВКОЙ
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
📊 Диапазон ставок: {MIN_BET}-{MAX_BET} ⭐

Выберите игру или просто отправь любой dice эмодзи в чат!
    """
    
    keyboard = [
        [InlineKeyboardButton("🎰 Слоты", callback_data="play_slots")],
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
        'slots': '🎰', 'dart': '🎯', 'dice': '🎲',
        'bowling': '🎳', 'football': '⚽', 'basketball': '🏀'
    }
    
    emoji = game_emojis.get(game_type, '🎰')
    
    # Отправляем dice от имени бота
    dice_message = await context.bot.send_dice(chat_id=query.message.chat_id, emoji=emoji)
    
    # Обрабатываем результат сразу
    await process_dice_result(user_id, emoji, dice_message.dice.value, current_bet if not admin_mode.get(user_id, False) else 0, dice_message, context)
    
    save_data()

# 🎰 ОБРАБОТКА DICE ОТ ПОЛЬЗОВАТЕЛЯ
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
    
    # Обрабатываем результат
    await process_dice_result(user_id, emoji, value, cost, message, context)
    
    save_data()

# 🎯 ОБРАБОТКА РЕЗУЛЬТАТА DICE С ПРОПОРЦИОНАЛЬНЫМИ ВЫИГРЫШАМИ
async def process_dice_result(user_id: int, emoji: str, value: int, cost: int, message, context: ContextTypes.DEFAULT_TYPE):
    game_config = GAMES_CONFIG.get(emoji)
    if not game_config:
        return
    
    # Получаем результат для этого значения
    result_config = game_config["values"].get(value)
    if not result_config:
        result_config = {"win": False, "base_prize": 0, "message": f"{emoji} - проигрыш"}
    
    # ВЫЧИСЛЯЕМ РЕАЛЬНЫЙ ВЫИГРЫШ НА ОСНОВЕ СТАВКИ
    current_bet = user_data[user_id]['current_bet']
    actual_prize = result_config["base_prize"] * current_bet
    
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

# 👑 АДМИН СИСТЕМА (остается без изменений)
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if len(context.args) == 0:
        await update.message.reply_text("Использование: /admin <код>")
        return
    
    code = context.args[0]
    if code == ADMIN_CODE:
        admin_mode[user_id] = True
        await update.message.reply_text(
            "👑 Режим администратора активирован!\n\n"
            "Теперь вы можете:\n"
            "• Играть бесплатно\n"
            "• Просматривать статистику\n"
            "• Управлять пользователями\n"
            "• Пополнять балансы\n\n"
            "Используйте кнопки в профиле для управления."
        )
    else:
        await update.message.reply_text("❌ Неверный код админа")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    total_users = len(user_data)
    total_games = sum(data['total_games'] for data in user_data.values())
    total_balance = sum(data['game_balance'] for data in user_data.values())
    
    admin_text = f"""
👑 АДМИН ПАНЕЛЬ

📊 Статистика бота:
👤 Пользователей: {total_users}
🎮 Всего игр: {total_games}
💎 Общий баланс: {total_balance} ⭐

Доступные функции:
    """
    
    keyboard = [
        [InlineKeyboardButton("🎮 Бесплатные игры", callback_data="admin_play")],
        [InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👤 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton("💎 Пополнить баланс пользователя", callback_data="admin_add_balance")],
        [InlineKeyboardButton("🔄 Сбросить данные", callback_data="admin_reset_confirm")],
        [InlineKeyboardButton("❌ Выйти из админки", callback_data="admin_exit")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(admin_text, reply_markup=reply_markup)

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
    
    win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
    
    stats_text = f"""
📊 ДЕТАЛЬНАЯ СТАТИСТИКА

👤 Пользователей: {total_users}
🎮 Всего игр: {total_games}
🏆 Всего побед: {total_wins}
📈 Винрейт: {win_rate:.1f}%

💎 Балансы:
💰 Общий баланс: {total_balance} ⭐
💳 Пополнено: {total_deposited} ⭐
💵 Реальные деньги: {total_real_money} Stars
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    # Показываем топ-10 пользователей по балансу
    top_users = sorted(user_data.items(), key=lambda x: x[1]['game_balance'], reverse=True)[:10]
    
    users_text = "👤 ТОП-10 ПОЛЬЗОВАТЕЛЕЙ ПО БАЛАНСУ:\n\n"
    
    for i, (uid, data) in enumerate(top_users, 1):
        users_text += f"{i}. ID: {uid} | 💰: {data['game_balance']} ⭐ | 🎮: {data['total_games']}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(users_text, reply_markup=reply_markup)

async def admin_add_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    add_balance_text = """
💎 ПОПОЛНЕНИЕ БАЛАНСА ПОЛЬЗОВАТЕЛЯ

Для пополнения баланса пользователя используйте команду:
`/addbalance <user_id> <amount>`

Пример:
`/addbalance 123456789 100`

Это добавит 100 ⭐ пользователю с ID 123456789
    """
    
    keyboard = [[InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(add_balance_text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_reset_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    reset_text = """
🔄 СБРОС ДАННЫХ

⚠️ ВНИМАНИЕ: Это действие нельзя отменить!

Вы уверены, что хотите сбросить ВСЕ данные бота?
Все пользовательские данные, балансы и статистика будут удалены.
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Да, сбросить всё", callback_data="admin_reset")],
        [InlineKeyboardButton("❌ Нет, отменить", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(reset_text, reply_markup=reply_markup)

async def admin_reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    # Сохраняем текущего админа
    current_admin = user_id
    
    # Очищаем все данные
    user_data.clear()
    user_activity.clear()
    consecutive_wins.clear()
    admin_mode.clear()
    
    # Восстанавливаем админский режим для текущего пользователя
    admin_mode[current_admin] = True
    
    save_data()
    
    await query.edit_message_text(
        "✅ Все данные были успешно сброшены!\n\n"
        "Базы данных очищены. Бот готов к работе с чистой статистикой."
    )

async def admin_play_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    games_text = "👑 АДМИН - БЕСПЛАТНЫЕ ИГРЫ\n\n🎮 Выберите игру:"
    
    keyboard = [
        [InlineKeyboardButton("🎰 Слоты (БЕСПЛАТНО)", callback_data="admin_play_slots")],
        [InlineKeyboardButton("🎯 Дартс (БЕСПЛАТНО)", callback_data="admin_play_dart")],
        [InlineKeyboardButton("🎲 Кубик (БЕСПЛАТНО)", callback_data="admin_play_dice")],
        [InlineKeyboardButton("🎳 Боулинг (БЕСПЛАТНО)", callback_data="admin_play_bowling")],
        [InlineKeyboardButton("⚽ Футбол (БЕСПЛАТНО)", callback_data="admin_play_football")],
        [InlineKeyboardButton("🏀 Баскетбол (БЕСПЛАТНО)", callback_data="admin_play_basketball")],
        [InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(games_text, reply_markup=reply_markup)

async def admin_handle_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not admin_mode.get(user_id, False):
        return
    
    game_type = query.data.replace("admin_play_", "")
    
    # В режиме админа не списываем средства
    user_data[user_id]['total_games'] += 1
    user_data[user_id]['last_activity'] = datetime.datetime.now().isoformat()
    
    game_emojis = {
        'slots': '🎰', 'dart': '🎯', 'dice': '🎲',
        'bowling': '🎳', 'football': '⚽', 'basketball': '🏀'
    }
    
    emoji = game_emojis.get(game_type, '🎰')
    
    # Отправляем dice от имени бота
    dice_message = await context.bot.send_dice(chat_id=query.message.chat_id, emoji=emoji)
    
    # Обрабатываем результат
    current_bet = user_data[user_id]['current_bet']
    await process_dice_result(user_id, emoji, dice_message.dice.value, 0, dice_message, context)

# 🔧 АДМИН КОМАНДЫ
async def add_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not admin_mode.get(user_id, False):
        await update.message.reply_text("❌ Эта команда только для админов")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("Использование: /addbalance <user_id> <amount>")
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

# 🔄 ОБРАБОТЧИКИ КНОПОК
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    callback_data = query.data
    
    # Сначала обрабатываем play_games отдельно
    if callback_data == 'play_games':
        await play_games_callback(update, context)
    
    # АДМИНСКИЕ КОМАНДЫ
    elif callback_data.startswith('admin_'):
        if callback_data == 'admin_panel':
            await admin_panel(update, context)
        elif callback_data == 'admin_play':
            await admin_play_callback(update, context)
        elif callback_data == 'admin_stats':
            await admin_stats_callback(update, context)
        elif callback_data == 'admin_users':
            await admin_users_callback(update, context)
        elif callback_data == 'admin_add_balance':
            await admin_add_balance_callback(update, context)
        elif callback_data == 'admin_reset_confirm':
            await admin_reset_confirm_callback(update, context)
        elif callback_data == 'admin_reset':
            await admin_reset_callback(update, context)
        elif callback_data.startswith('admin_play_'):
            await admin_handle_game_selection(update, context)
        elif callback_data == 'admin_back':
            await admin_panel(update, context)
        elif callback_data == 'admin_exit':
            user_id = query.from_user.id
            admin_mode[user_id] = False
            await query.edit_message_text("👑 Режим админа деактивирован")
    
    # ОСНОВНЫЕ КОМАНДЫ
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

async def back_to_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await profile(update, context)

# 🌐 FLASK ДЛЯ RAILWAY
app = Flask(__name__)

@app.route('/')
def home():
    return "🎰 NSource Casino Bot - Полная игровая система!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# 🚀 ЗАПУСК БОТА
def main():
    load_data()
    
    # Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # КОМАНДЫ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CommandHandler("activity", activity_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("addbalance", add_balance_command))
    application.add_handler(CommandHandler("bet", bet_command))
    
    # CALLBACK'И
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # ПЛАТЕЖИ
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # СООБЩЕНИЯ - ГЛАВНЫЙ ОБРАБОТЧИК DICE ОТ ПОЛЬЗОВАТЕЛЯ
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_user_dice))
    
    print("🎰 NSource Casino Bot запущен!")
    print("🎮 Доступные игры: 🎰 🎯 🎲 🎳 ⚽ 🏀")
    print("💰 Система с изменяемой ставкой от 1 до 100000 ⭐!")
    print("⭐ Все выигрыши пропорциональны ставке!")
    application.run_polling()

if __name__ == '__main__':
    main()
