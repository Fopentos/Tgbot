import telebot
from telebot.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
import json
import sqlite3
import time
import random
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# ========== КОНФИГУРАЦИЯ ИГР ==========

GAMES_CONFIG = {
    "slots": {
        "name": "🎰 Игровые автоматы",
        "min_bet": 10,
        "max_bet": 1000,
        "payouts": {
            1: {"symbols": ["🍒", "🍒", "🍒"], "multiplier": 3.0, "probability": 0.01},
            2: {"symbols": ["🍋", "🍋", "🍋"], "multiplier": 2.5, "probability": 0.02},
            3: {"symbols": ["🍊", "🍊", "🍊"], "multiplier": 2.0, "probability": 0.03},
            4: {"symbols": ["🍇", "🍇", "🍇"], "multiplier": 1.8, "probability": 0.04},
            5: {"symbols": ["🍉", "🍉", "🍉"], "multiplier": 1.6, "probability": 0.05},
            6: {"symbols": ["🔔", "🔔", "🔔"], "multiplier": 1.4, "probability": 0.06},
            7: {"symbols": ["💎", "💎", "💎"], "multiplier": 5.0, "probability": 0.005},
            8: {"symbols": ["⭐", "⭐", "⭐"], "multiplier": 10.0, "probability": 0.001},
            9: {"symbols": ["🍒", "🍒", "🍋"], "multiplier": 1.2, "probability": 0.08},
            10: {"symbols": ["🍋", "🍋", "🍊"], "multiplier": 1.1, "probability": 0.09},
            11: {"symbols": ["🍊", "🍊", "🍇"], "multiplier": 1.1, "probability": 0.09},
            12: {"symbols": ["🍇", "🍇", "🍉"], "multiplier": 1.1, "probability": 0.09},
            13: {"symbols": ["🍉", "🍉", "🔔"], "multiplier": 1.1, "probability": 0.09},
            14: {"symbols": ["🔔", "🔔", "💎"], "multiplier": 1.3, "probability": 0.07},
            15: {"symbols": ["💎", "💎", "⭐"], "multiplier": 2.0, "probability": 0.04},
            16: {"symbols": ["⭐", "⭐", "💎"], "multiplier": 2.0, "probability": 0.04},
            17: {"symbols": ["🍒", "🍋", "🍊"], "multiplier": 1.0, "probability": 0.12},
            18: {"symbols": ["🍋", "🍊", "🍇"], "multiplier": 1.0, "probability": 0.12},
            19: {"symbols": ["🍊", "🍇", "🍉"], "multiplier": 1.0, "probability": 0.12},
            20: {"symbols": ["🍇", "🍉", "🔔"], "multiplier": 1.0, "probability": 0.12},
            21: {"symbols": ["🍉", "🔔", "💎"], "multiplier": 1.2, "probability": 0.08},
            22: {"symbols": ["🔔", "💎", "⭐"], "multiplier": 1.5, "probability": 0.06},
            23: {"symbols": ["💎", "⭐", "🍒"], "multiplier": 1.5, "probability": 0.06},
            24: {"symbols": ["⭐", "🍒", "🍋"], "multiplier": 1.3, "probability": 0.07},
            25: {"symbols": ["🍒", "🍊", "🍇"], "multiplier": 1.0, "probability": 0.12},
            26: {"symbols": ["🍋", "🍇", "🍉"], "multiplier": 1.0, "probability": 0.12},
            27: {"symbols": ["🍊", "🍉", "🔔"], "multiplier": 1.0, "probability": 0.12},
            28: {"symbols": ["🍇", "🔔", "💎"], "multiplier": 1.2, "probability": 0.08},
            29: {"symbols": ["🍉", "💎", "⭐"], "multiplier": 1.5, "probability": 0.06},
            30: {"symbols": ["🔔", "⭐", "🍒"], "multiplier": 1.5, "probability": 0.06},
            31: {"symbols": ["💎", "🍒", "🍋"], "multiplier": 1.3, "probability": 0.07},
            32: {"symbols": ["⭐", "🍋", "🍊"], "multiplier": 1.3, "probability": 0.07},
            33: {"symbols": ["🍒", "🍇", "🍉"], "multiplier": 1.0, "probability": 0.12},
            34: {"symbols": ["🍋", "🍉", "🔔"], "multiplier": 1.0, "probability": 0.12},
            35: {"symbols": ["🍊", "🔔", "💎"], "multiplier": 1.2, "probability": 0.08},
            36: {"symbols": ["🍇", "💎", "⭐"], "multiplier": 1.5, "probability": 0.06},
            37: {"symbols": ["🍉", "⭐", "🍒"], "multiplier": 1.5, "probability": 0.06},
            38: {"symbols": ["🔔", "🍒", "🍋"], "multiplier": 1.3, "probability": 0.07},
            39: {"symbols": ["💎", "🍋", "🍊"], "multiplier": 1.3, "probability": 0.07},
            40: {"symbols": ["⭐", "🍊", "🍇"], "multiplier": 1.3, "probability": 0.07},
            41: {"symbols": ["🍒", "🍉", "🔔"], "multiplier": 1.0, "probability": 0.12},
            42: {"symbols": ["🍋", "🔔", "💎"], "multiplier": 1.2, "probability": 0.08},
            43: {"symbols": ["🍊", "💎", "⭐"], "multiplier": 1.5, "probability": 0.06},
            44: {"symbols": ["🍇", "⭐", "🍒"], "multiplier": 1.5, "probability": 0.06},
            45: {"symbols": ["🍉", "🍒", "🍋"], "multiplier": 1.3, "probability": 0.07},
            46: {"symbols": ["🔔", "🍋", "🍊"], "multiplier": 1.3, "probability": 0.07},
            47: {"symbols": ["💎", "🍊", "🍇"], "multiplier": 1.3, "probability": 0.07},
            48: {"symbols": ["⭐", "🍇", "🍉"], "multiplier": 1.3, "probability": 0.07},
            49: {"symbols": ["🍒", "🔔", "💎"], "multiplier": 1.2, "probability": 0.08},
            50: {"symbols": ["🍋", "💎", "⭐"], "multiplier": 1.5, "probability": 0.06},
            51: {"symbols": ["🍊", "⭐", "🍒"], "multiplier": 1.5, "probability": 0.06},
            52: {"symbols": ["🍇", "🍒", "🍋"], "multiplier": 1.3, "probability": 0.07},
            53: {"symbols": ["🍉", "🍋", "🍊"], "multiplier": 1.3, "probability": 0.07},
            54: {"symbols": ["🔔", "🍊", "🍇"], "multiplier": 1.3, "probability": 0.07},
            55: {"symbols": ["💎", "🍇", "🍉"], "multiplier": 1.3, "probability": 0.07},
            56: {"symbols": ["⭐", "🍉", "🔔"], "multiplier": 1.3, "probability": 0.07},
            57: {"symbols": ["🍒", "💎", "⭐"], "multiplier": 1.5, "probability": 0.06},
            58: {"symbols": ["🍋", "⭐", "🍒"], "multiplier": 1.5, "probability": 0.06},
            59: {"symbols": ["🍊", "🍒", "🍋"], "multiplier": 1.3, "probability": 0.07},
            60: {"symbols": ["🍇", "🍋", "🍊"], "multiplier": 1.3, "probability": 0.07},
            61: {"symbols": ["🍉", "🍊", "🍇"], "multiplier": 1.3, "probability": 0.07},
            62: {"symbols": ["🔔", "🍇", "🍉"], "multiplier": 1.3, "probability": 0.07},
            63: {"symbols": ["💎", "🍉", "🔔"], "multiplier": 1.3, "probability": 0.07},
            64: {"symbols": ["⭐", "🔔", "💎"], "multiplier": 1.5, "probability": 0.06}
        },
        "symbols": ["🍒", "🍋", "🍊", "🍇", "🍉", "🔔", "💎", "⭐"]
    },
    "dice": {
        "name": "🎲 Кости",
        "min_bet": 10,
        "max_bet": 500,
        "payouts": {
            "classic": {
                2: {"multiplier": 6.0, "probability": 1/36},
                3: {"multiplier": 3.0, "probability": 2/36},
                4: {"multiplier": 2.0, "probability": 3/36},
                5: {"multiplier": 1.5, "probability": 4/36},
                6: {"multiplier": 1.2, "probability": 5/36},
                7: {"multiplier": 1.0, "probability": 6/36},
                8: {"multiplier": 1.2, "probability": 5/36},
                9: {"multiplier": 1.5, "probability": 4/36},
                10: {"multiplier": 2.0, "probability": 3/36},
                11: {"multiplier": 3.0, "probability": 2/36},
                12: {"multiplier": 6.0, "probability": 1/36}
            },
            "even_odd": {
                "even": {"multiplier": 2.0, "probability": 0.5},
                "odd": {"multiplier": 2.0, "probability": 0.5}
            },
            "high_low": {
                "high": {"multiplier": 2.0, "probability": 0.5},
                "low": {"multiplier": 2.0, "probability": 0.5}
            }
        }
    },
    "roulette": {
        "name": "🎡 Рулетка",
        "min_bet": 10,
        "max_bet": 1000,
        "payouts": {
            "red_black": {"multiplier": 2.0, "probability": 18/37},
            "even_odd": {"multiplier": 2.0, "probability": 18/37},
            "high_low": {"multiplier": 2.0, "probability": 18/37},
            "dozen": {"multiplier": 3.0, "probability": 12/37},
            "column": {"multiplier": 3.0, "probability": 12/37},
            "line": {"multiplier": 6.0, "probability": 6/37},
            "square": {"multiplier": 9.0, "probability": 4/37},
            "street": {"multiplier": 12.0, "probability": 3/37},
            "split": {"multiplier": 18.0, "probability": 2/37},
            "straight": {"multiplier": 36.0, "probability": 1/37}
        },
        "numbers": list(range(0, 37)),
        "red": [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36],
        "black": [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
    },
    "blackjack": {
        "name": "🃏 Блэкджек",
        "min_bet": 20,
        "max_bet": 500,
        "payouts": {
            "win": {"multiplier": 2.0, "probability": 0.48},
            "blackjack": {"multiplier": 2.5, "probability": 0.05},
            "push": {"multiplier": 1.0, "probability": 0.08},
            "lose": {"multiplier": 0.0, "probability": 0.39}
        }
    }
}

SLOTS_777_CONFIG = {
    "reels": [
        ["🍒", "🍋", "🍊", "🍇", "🍉", "🔔", "💎", "⭐", "🍒", "🍋", "🍊", "🍇", "🍉", "🔔", "💎", "🍒", "🍋", "🍊", "🍇", "🍉"],
        ["🍒", "🍋", "🍊", "🍇", "🍉", "🔔", "💎", "⭐", "🍒", "🍋", "🍊", "🍇", "🍉", "🔔", "💎", "🍒", "🍋", "🍊", "🍇", "🍉"],
        ["🍒", "🍋", "🍊", "🍇", "🍉", "🔔", "💎", "⭐", "🍒", "🍋", "🍊", "🍇", "🍉", "🔔", "💎", "🍒", "🍋", "🍊", "🍇", "🍉"]
    ],
    "paylines": [
        [0, 0, 0],  # Центральная линия
        [1, 1, 1],  # Верхняя линия
        [-1, -1, -1],  # Нижняя линия
        [0, 1, 0],  # V-образная
        [0, -1, 0],  # Перевернутая V
        [1, 0, -1],  # Диагональ
        [-1, 0, 1]   # Обратная диагональ
    ],
    "symbol_values": {
        "🍒": {"payouts": [0, 2, 5, 10, 20]},
        "🍋": {"payouts": [0, 2, 5, 10, 15]},
        "🍊": {"payouts": [0, 2, 5, 8, 12]},
        "🍇": {"payouts": [0, 2, 4, 8, 10]},
        "🍉": {"payouts": [0, 1, 3, 6, 8]},
        "🔔": {"payouts": [0, 1, 2, 4, 6]},
        "💎": {"payouts": [0, 5, 15, 30, 50]},
        "⭐": {"payouts": [0, 10, 25, 50, 100]}
    }
}

# ========== СИСТЕМА СЕРИЙ ПОБЕД ==========

WIN_STREAK_BONUSES = {
    3: {"bonus": 10, "message": "🔥 Серия из 3 побед! +10⭐"},
    5: {"bonus": 25, "message": "🔥 Серия из 5 побед! +25⭐"},
    10: {"bonus": 100, "message": "🎯 Серия из 10 побед! +100⭐"},
    15: {"bonus": 250, "message": "🚀 Серия из 15 побед! +250⭐"},
    20: {"bonus": 500, "message": "💎 Серия из 20 побед! +500⭐"},
    25: {"bonus": 1000, "message": "👑 Серия из 25 побед! +1000⭐"},
    30: {"bonus": 2000, "message": "🏆 Легендарная серия из 30 побед! +2000⭐"}
}

LOSE_STREAK_BONUSES = {
    5: {"bonus": 10, "message": "💫 Бонус за терпение! +10⭐"},
    10: {"bonus": 25, "message": "💫 Бонус за настойчивость! +25⭐"},
    15: {"bonus": 50, "message": "💫 Бонус за упорство! +50⭐"},
    20: {"bonus": 100, "message": "💫 Бонус за стойкость! +100⭐"}
}

# ========== КЛАСС ДЛЯ РАСЧЕТА ПОДАРКОВ ==========

class GiftCalculator:
    def __init__(self):
        self.available_gifts = [100, 50, 25, 15]
        self.available_gifts.sort(reverse=True)
    
    def can_withdraw_amount(self, amount: int) -> bool:
        """Проверяет, можно ли разложить сумму на доступные номиналы"""
        return self._find_combination(amount) is not None
    
    def find_best_combination(self, amount: int) -> Optional[Dict[int, int]]:
        """Находит оптимальную комбинацию подарков"""
        return self._find_combination(amount)
    
    def _find_combination(self, amount: int) -> Optional[Dict[int, int]]:
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
    
    def get_suggested_amounts(self, desired_amount: int, count: int = 3) -> List[int]:
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
    
    def get_available_amounts_in_range(self, min_amount: int, max_amount: int) -> List[int]:
        """Возвращает все доступные суммы в диапазоне"""
        available = []
        for amount in range(min_amount, max_amount + 1):
            if self.can_withdraw_amount(amount):
                available.append(amount)
        return available

# ========== БАЗА ДАННЫХ ==========

class Database:
    def __init__(self, db_path="casino_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализирует таблицы базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance INTEGER DEFAULT 1000,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                win_streak INTEGER DEFAULT 0,
                lose_streak INTEGER DEFAULT 0,
                max_win_streak INTEGER DEFAULT 0,
                total_deposited INTEGER DEFAULT 0,
                total_withdrawn INTEGER DEFAULT 0,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица транзакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица игровой активности
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_type TEXT,
                bet_amount INTEGER,
                win_amount INTEGER,
                result TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица выводов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                gift_combination TEXT,
                status TEXT DEFAULT 'pending',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получает данные пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM users WHERE user_id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                "user_id": user[0],
                "username": user[1],
                "first_name": user[2],
                "balance": user[3],
                "total_wins": user[4],
                "total_losses": user[5],
                "win_streak": user[6],
                "lose_streak": user[7],
                "max_win_streak": user[8],
                "total_deposited": user[9],
                "total_withdrawn": user[10],
                "registration_date": user[11],
                "last_active": user[12]
            }
        return None
    
    def create_user(self, user_id: int, username: str, first_name: str):
        """Создает нового пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, balance)
            VALUES (?, ?, ?, 1000)
        ''', (user_id, username, first_name))
        
        conn.commit()
        conn.close()
    
    def update_user_balance(self, user_id: int, amount: int):
        """Обновляет баланс пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET balance = balance + ? WHERE user_id = ?
        ''', (amount, user_id))
        
        conn.commit()
        conn.close()
    
    def update_user_stats(self, user_id: int, win: bool, amount: int):
        """Обновляет статистику пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if win:
            cursor.execute('''
                UPDATE users SET 
                total_wins = total_wins + 1,
                win_streak = win_streak + 1,
                lose_streak = 0,
                max_win_streak = MAX(max_win_streak, win_streak + 1),
                last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (user_id,))
        else:
            cursor.execute('''
                UPDATE users SET 
                total_losses = total_losses + 1,
                lose_streak = lose_streak + 1,
                win_streak = 0,
                last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    def add_transaction(self, user_id: int, transaction_type: str, amount: int, description: str):
        """Добавляет запись о транзакции"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, transaction_type, amount, description))
        
        conn.commit()
        conn.close()
    
    def add_game_activity(self, user_id: int, game_type: str, bet_amount: int, win_amount: int, result: str):
        """Добавляет запись об игровой активности"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO game_activity (user_id, game_type, bet_amount, win_amount, result)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, game_type, bet_amount, win_amount, result))
        
        conn.commit()
        conn.close()

# ========== ОСНОВНОЙ КЛАСС БОТА ==========

class CasinoBot:
    def __init__(self, token: str):
        self.bot = telebot.TeleBot(token)
        self.db = Database()
        self.gift_calculator = GiftCalculator()
        self.admin_ids = [123456789]  # Замените на реальные ID администраторов
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков сообщений"""
        
        # Команды
        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            self.handle_start(message)
        
        @self.bot.message_handler(commands=['balance'])
        def balance_command(message):
            self.show_balance(message)
        
        @self.bot.message_handler(commands=['games'])
        def games_command(message):
            self.show_games_menu(message)
        
        @self.bot.message_handler(commands=['withdraw'])
        def withdraw_command(message):
            self.start_withdrawal(message)
        
        @self.bot.message_handler(commands=['deposit'])
        def deposit_command(message):
            self.show_deposit_menu(message)
        
        @self.bot.message_handler(commands=['stats'])
        def stats_command(message):
            self.show_stats(message)
        
        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            self.show_help(message)
        
        # Админ команды
        @self.bot.message_handler(commands=['admin'])
        def admin_command(message):
            self.handle_admin_command(message)
        
        # Обработка callback-запросов
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_all_callbacks(call):
            self.handle_callback(call)
        
        # Обработка текстовых сообщений
        @self.bot.message_handler(content_types=['text'])
        def handle_text(message):
            self.handle_text_message(message)
    
    def handle_start(self, message):
        """Обработка команды /start"""
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        
        # Создаем пользователя если не существует
        self.db.create_user(user_id, username, first_name)
        
        welcome_text = f"""
🎰 Добро пожаловать в Telegram Casino, {first_name}! 🎰

💰 Ваш стартовый баланс: 1000⭐

✨ Доступные игры:
• 🎰 Игровые автоматы
• 🎲 Кости  
• 🎡 Рулетка
• 🃏 Блэкджек

💫 Особенности:
✅ Вывод Telegram Stars через подарки
🔥 Бонусы за серии побед
📊 Подробная статистика
🎁 Ежедневные бонусы

Используйте /games чтобы начать играть!
Используйте /help для справки
        """
        
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row(KeyboardButton("/games"), KeyboardButton("/balance"))
        keyboard.row(KeyboardButton("/deposit"), KeyboardButton("/withdraw"))
        keyboard.row(KeyboardButton("/stats"), KeyboardButton("/help"))
        
        self.bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    def show_games_menu(self, message):
        """Показывает меню игр"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("🎰 Слоты", callback_data="game_slots"),
            InlineKeyboardButton("🎲 Кости", callback_data="game_dice")
        )
        keyboard.row(
            InlineKeyboardButton("🎡 Рулетка", callback_data="game_roulette"),
            InlineKeyboardButton("🃏 Блэкджек", callback_data="game_blackjack")
        )
        
        text = """
🎮 *Выберите игру:*

*🎰 Игровые автоматы* - классические слоты
*🎲 Кости* - ставки на результат броска  
*🎡 Рулетка* - европейская рулетка
*🃏 Блэкджек* - игра против дилера

💡 *Минимальные ставки:*
• Слоты: 10⭐
• Кости: 10⭐  
• Рулетка: 10⭐
• Блэкджек: 20⭐
        """
        
        self.bot.send_message(
            message.chat.id,
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    def show_balance(self, message):
        """Показывает баланс пользователя"""
        user_id = message.from_user.id
        user = self.db.get_user(user_id)
        
        if not user:
            self.bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        text = f"""
💰 *Ваш баланс*

*Доступно:* {user['balance']}⭐
*Всего пополнено:* {user['total_deposited']}⭐
*Всего выведено:* {user['total_withdrawn']}⭐

💫 *Статистика:*
Побед: {user['total_wins']}
Поражений: {user['total_losses']}
Текущая серия: {user['win_streak'] if user['win_streak'] > 0 else user['lose_streak'] * -1}
Макс. серия побед: {user['max_win_streak']}

Используйте /withdraw для вывода средств
        """
        
        self.bot.send_message(
            message.chat.id,
            text,
            parse_mode="Markdown"
        )
    
    def start_withdrawal(self, message):
        """Начинает процесс вывода"""
        user_id = message.from_user.id
        user = self.db.get_user(user_id)
        
        if not user:
            self.bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        user_balance = user['balance']
        
        if user_balance < 15:
            self.bot.reply_to(
                message,
                f"❌ *Недостаточно средств для вывода*\n"
                f"Минимальная сумма: 15⭐\n"
                f"Ваш баланс: {user_balance}⭐",
                parse_mode="Markdown"
            )
            return
        
        # Показываем примеры доступных сумм
        examples = self.gift_calculator.get_available_amounts_in_range(15, min(100, user_balance))
        examples_text = "\n".join([f"• {amt}⭐" for amt in examples[:8]])
        
        text = f"""
💫 *Запрос на вывод средств*

*Ваш баланс:* {user_balance}⭐
*Минимальный вывод:* 15⭐

Введите сумму для вывода:

*Примеры доступных сумм:*
{examples_text}

💡 *Примечание:* Сумма должна быть такой, чтобы её можно было собрать из подарков 15⭐, 25⭐, 50⭐, 100⭐
        """
        
        self.bot.reply_to(message, text, parse_mode="Markdown")
        self.bot.register_next_step_handler(message, self.process_amount_input)
    
    def process_amount_input(self, message):
        """Обрабатывает ввод суммы для вывода"""
        user_id = message.from_user.id
        
        # Отменяем если команда
        if message.text.startswith('/'):
            self.bot.reply_to(message, "❌ Ввод суммы отменен")
            return
        
        # Извлекаем число
        amount_text = re.sub(r'[^\d]', '', message.text)
        if not amount_text:
            self.bot.reply_to(message, "❌ Пожалуйста, введите число")
            self.bot.register_next_step_handler(message, self.process_amount_input)
            return
        
        try:
            amount = int(amount_text)
        except ValueError:
            self.bot.reply_to(message, "❌ Пожалуйста, введите корректное число")
            self.bot.register_next_step_handler(message, self.process_amount_input)
            return
        
        # Проверяем баланс
        user = self.db.get_user(user_id)
        if not user:
            self.bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        user_balance = user['balance']
        if amount > user_balance:
            self.bot.reply_to(
                message,
                f"❌ *Недостаточно средств*\nЗапрошено: {amount}⭐\nДоступно: {user_balance}⭐\n\nВведите меньшую сумму:",
                parse_mode="Markdown"
            )
            self.bot.register_next_step_handler(message, self.process_amount_input)
            return
        
        if amount < 15:
            self.bot.reply_to(
                message,
                f"❌ *Слишком маленькая сумма*\nМинимальный вывод: 15⭐\n\nВведите сумму от 15⭐:",
                parse_mode="Markdown"
            )
            self.bot.register_next_step_handler(message, self.process_amount_input)
            return
        
        # Проверяем возможность вывода
        if not self.gift_calculator.can_withdraw_amount(amount):
            self.handle_invalid_amount(message, amount, user_id)
            return
        
        # Показываем подтверждение
        combination = self.gift_calculator.find_best_combination(amount)
        self.show_confirmation(message, user_id, amount, combination)
    
    def handle_invalid_amount(self, message, amount: int, user_id: int):
        """Обрабатывает случай когда сумму нельзя разложить"""
        suggestions = self.gift_calculator.get_suggested_amounts(amount, 3)
        suggestions_text = "\n".join([f"• {s}⭐" for s in suggestions])
        
        # Показываем пример для ближайшей суммы
        example_combo = self.gift_calculator.find_best_combination(suggestions[0])
        example_text = " + ".join([f"{count}×{value}⭐" for value, count in example_combo.items()])
        
        text = f"""
❌ *Сумма {amount}⭐ не доступна для вывода*

Эту сумму невозможно собрать из подарков 15⭐, 25⭐, 50⭐, 100⭐.

*Ближайшие доступные суммы:*
{suggestions_text}

*Например, {suggestions[0]}⭐ = {example_text}*

Пожалуйста, введите одну из доступных сумм:
        """
        
        self.bot.reply_to(message, text, parse_mode="Markdown")
        self.bot.register_next_step_handler(message, self.process_amount_input)
    
    def show_confirmation(self, message, user_id: int, amount: int, combination: Dict[int, int]):
        """Показывает подтверждение вывода"""
        combination_text = " + ".join([f"{count}×{value}⭐" for value, count in combination.items()])
        gift_count = sum(combination.values())
        
        text = f"""
✅ *Подтверждение вывода*

*Сумма:* {amount}⭐
*Количество подарков:* {gift_count}

*Комбинация подарков:*
{combination_text}

После подтверждения вы получите {gift_count} подарков.
        """
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_withdraw_{amount}"),
            InlineKeyboardButton("❌ Отменить", callback_data="cancel_withdraw")
        )
        
        self.bot.send_message(
            message.chat.id,
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    
    def execute_withdrawal(self, call, amount: int):
        """Выполняет вывод средств"""
        user_id = call.from_user.id
        user = self.db.get_user(user_id)
        
        if not user:
            self.bot.answer_callback_query(call.id, "❌ Пользователь не найден", show_alert=True)
            return
        
        # Проверяем баланс
        user_balance = user['balance']
        if user_balance < amount:
            self.bot.answer_callback_query(call.id, "❌ Недостаточно средств", show_alert=True)
            return
        
        # Находим комбинацию
        combination = self.gift_calculator.find_best_combination(amount)
        if not combination:
            self.bot.answer_callback_query(call.id, "❌ Ошибка расчета комбинации", show_alert=True)
            return
        
        try:
            # Списываем средства
            self.db.update_user_balance(user_id, -amount)
            self.db.add_transaction(user_id, "withdraw", -amount, f"Вывод {amount}⭐")
            
            # Обновляем статистику выводов
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET total_withdrawn = total_withdrawn + ? WHERE user_id = ?
            ''', (amount, user_id))
            conn.commit()
            conn.close()
            
            # Сохраняем запрос на вывод
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO withdrawals (user_id, amount, gift_combination)
                VALUES (?, ?, ?)
            ''', (user_id, amount, json.dumps(combination)))
            conn.commit()
            conn.close()
            
            # Показываем успех
            combination_text = " + ".join([f"{count}×{value}⭐" for value, count in combination.items()])
            
            success_text = f"""
🎉 *Вывод выполнен успешно!*

*Сумма:* {amount}⭐
*Отправлено подарков:* {sum(combination.values())}

*Комбинация:*
{combination_text}

💫 Подарки отправлены в ваш аккаунт! Вы можете обменять их на Stars в течение 7 дней.

💰 Новый баланс: {user_balance - amount}⭐
            """
            
            self.bot.edit_message_text(
                success_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            # Возвращаем средства при ошибке
            self.db.update_user_balance(user_id, amount)
            self.bot.edit_message_text(
                f"❌ Ошибка при выводе: {str(e)}",
                call.message.chat.id,
                call.message.message_id
            )
    
    def show_deposit_menu(self, message):
        """Показывает меню пополнения"""
        text = """
💳 *Пополнение баланса*

Для пополнения баланса:
1. Отправьте любую сумму Stars в виде подарка этому боту
2. Баланс будет автоматически пополнен
3. Минимальное пополнение: 15⭐

💡 *Как отправить подарок:*
1. Нажмите на значок 📎 рядом с полем ввода
2. Выберите "Подарок"  
3. Выберите количество Stars
4. Отправьте этому боту

💰 *Доступные номиналы:* 15⭐, 25⭐, 50⭐, 100⭐
        """
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("🔄 Проверить пополнение", callback_data="check_deposit"),
            InlineKeyboardButton("📊 Баланс", callback_data="show_balance")
        )
        
        self.bot.send_message(
            message.chat.id,
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    def show_stats(self, message):
        """Показывает статистику пользователя"""
        user_id = message.from_user.id
        user = self.db.get_user(user_id)
        
        if not user:
            self.bot.reply_to(message, "❌ Пользователь не найден")
            return
        
        total_games = user['total_wins'] + user['total_losses']
        win_rate = (user['total_wins'] / total_games * 100) if total_games > 0 else 0
        
        # Получаем последние игры
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT game_type, COUNT(*) as games_played, 
                   SUM(win_amount) as total_won, SUM(bet_amount) as total_bet
            FROM game_activity 
            WHERE user_id = ? 
            GROUP BY game_type
        ''', (user_id,))
        game_stats = cursor.fetchall()
        conn.close()
        
        game_stats_text = ""
        for game in game_stats:
            profit = game[2] - game[3]
            game_stats_text += f"• {game[0]}: {game[1]} игр, {profit:+}⭐\n"
        
        text = f"""
📊 *Статистика игрока*

👤 *Общая статистика:*
Игр сыграно: {total_games}
Побед: {user['total_wins']} ({win_rate:.1f}%)
Поражений: {user['total_losses']}
Текущая серия: {user['win_streak'] if user['win_streak'] > 0 else user['lose_streak'] * -1}
Макс. серия побед: {user['max_win_streak']}

💰 *Финансы:*
Пополнено: {user['total_deposited']}⭐
Выведено: {user['total_withdrawn']}⭐
Текущий баланс: {user['balance']}⭐

🎮 *По играм:*
{game_stats_text if game_stats_text else "• Пока нет данных об играх"}

📅 Зарегистрирован: {user['registration_date'][:10]}
        """
        
        self.bot.send_message(
            message.chat.id,
            text,
            parse_mode="Markdown"
        )
    
    def show_help(self, message):
        """Показывает справку"""
        text = """
🎰 *Telegram Casino - Помощь*

*Основные команды:*
/start - Начать работу
/games - Игровое меню  
/balance - Баланс
/deposit - Пополнить баланс
/withdraw - Вывести средства
/stats - Статистика
/help - Эта справка

*🎮 Игры:*
• *🎰 Слоты* - классические игровые автоматы
• *🎲 Кости* - ставки на результат броска
• *🎡 Рулетка* - европейская рулетка  
• *🃏 Блэкджек* - игра против дилера

*💫 Вывод средств:*
Минимальная сумма: 15⭐
Сумма должна раскладываться на подарки 15/25/50/100⭐
Вывод осуществляется отправкой подарков

*🔥 Бонусы:*
• Бонусы за серии побед
• Бонусы за серии поражений
• Ежедневные бонусы

*📊 Статистика:*
Ведется полная статистика по всем играм
Можно отслеживать прогресс и результаты

💡 *Совет:* Начинайте с небольших ставок!
        """
        
        self.bot.send_message(
            message.chat.id,
            text,
            parse_mode="Markdown"
        )
    
    def handle_admin_command(self, message):
        """Обрабатывает админ команды"""
        user_id = message.from_user.id
        
        if user_id not in self.admin_ids:
            self.bot.reply_to(message, "❌ Доступ запрещен")
            return
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("📊 Статистика бота", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")
        )
        keyboard.row(
            InlineKeyboardButton("💰 Управление балансом", callback_data="admin_balance"),
            InlineKeyboardButton("🎮 Игровая статистика", callback_data="admin_games")
        )
        keyboard.row(
            InlineKeyboardButton("📈 Финансы", callback_data="admin_finance"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")
        )
        
        text = """
⚙️ *Панель администратора*

Выберите раздел для управления:
        """
        
        self.bot.send_message(
            message.chat.id,
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    def handle_callback(self, call):
        """Обрабатывает все callback-запросы"""
        try:
            if call.data.startswith("game_"):
                self.handle_game_callback(call)
            elif call.data.startswith("confirm_withdraw_"):
                amount = int(call.data.replace("confirm_withdraw_", ""))
                self.execute_withdrawal(call, amount)
            elif call.data == "cancel_withdraw":
                self.bot.edit_message_text(
                    "❌ Вывод отменен",
                    call.message.chat.id,
                    call.message.message_id
                )
            elif call.data == "check_deposit":
                self.bot.answer_callback_query(call.id, "Функция в разработке")
            elif call.data == "show_balance":
                user_id = call.from_user.id
                user = self.db.get_user(user_id)
                if user:
                    self.bot.answer_callback_query(
                        call.id, 
                        f"Ваш баланс: {user['balance']}⭐", 
                        show_alert=True
                    )
            elif call.data.startswith("admin_"):
                self.handle_admin_callback(call)
            elif call.data.startswith("slots_bet_"):
                self.handle_slots_bet(call)
            elif call.data.startswith("dice_bet_"):
                self.handle_dice_bet(call)
            elif call.data.startswith("roulette_bet_"):
                self.handle_roulette_bet(call)
            elif call.data.startswith("blackjack_"):
                self.handle_blackjack_bet(call)
            
        except Exception as e:
            self.bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")
    
    def handle_game_callback(self, call):
        """Обрабатывает выбор игры"""
        game_type = call.data.replace("game_", "")
        
        if game_type == "slots":
            self.show_slots_menu(call)
        elif game_type == "dice":
            self.show_dice_menu(call)
        elif game_type == "roulette":
            self.show_roulette_menu(call)
        elif game_type == "blackjack":
            self.show_blackjack_menu(call)
    
    def show_slots_menu(self, call):
        """Показывает меню слотов"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("10⭐", callback_data="slots_bet_10"),
            InlineKeyboardButton("50⭐", callback_data="slots_bet_50"),
            InlineKeyboardButton("100⭐", callback_data="slots_bet_100")
        )
        keyboard.row(
            InlineKeyboardButton("250⭐", callback_data="slots_bet_250"),
            InlineKeyboardButton("500⭐", callback_data="slots_bet_500"),
            InlineKeyboardButton("1000⭐", callback_data="slots_bet_1000")
        )
        keyboard.row(
            InlineKeyboardButton("🎰 Крутить!", callback_data="slots_spin"),
            InlineKeyboardButton("📊 Правила", callback_data="slots_rules")
        )
        
        text = """
🎰 *Игровые автоматы*

*Минимальная ставка:* 10⭐
*Максимальная ставка:* 1000⭐

*Выигрышные комбинации:*
🍒🍒🍒 = 3x
🍋🍋🍋 = 2.5x  
🍊🍊🍊 = 2x
💎💎💎 = 5x
⭐⭐⭐ = 10x

Выберите ставку и нажмите "Крутить!"
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    def handle_slots_bet(self, call):
        """Обрабатывает ставку в слотах"""
        bet_amount = int(call.data.replace("slots_bet_", ""))
        user_id = call.from_user.id
        user = self.db.get_user(user_id)
        
        if not user:
            self.bot.answer_callback_query(call.id, "❌ Пользователь не найден")
            return
        
        if user['balance'] < bet_amount:
            self.bot.answer_callback_query(call.id, "❌ Недостаточно средств")
            return
        
        # Имитация вращения слотов
        self.bot.answer_callback_query(call.id, f"🎰 Ставка {bet_amount}⭐ принята!")
        
        # Генерируем результат
        reels = [
            random.choice(SLOTS_777_CONFIG["reels"][0]),
            random.choice(SLOTS_777_CONFIG["reels"][1]), 
            random.choice(SLOTS_777_CONFIG["reels"][2])
        ]
        
        # Определяем выигрыш
        win_amount = 0
        result_text = "❌ Проигрыш"
        
        # Проверяем выигрышные комбинации
        for combo_id, combo_data in GAMES_CONFIG["slots"]["payouts"].items():
            if reels == combo_data["symbols"]:
                win_amount = int(bet_amount * combo_data["multiplier"])
                result_text = f"🎉 Выигрыш {win_amount}⭐ (x{combo_data['multiplier']})"
                break
        
        # Обновляем баланс и статистику
        if win_amount > 0:
            self.db.update_user_balance(user_id, win_amount - bet_amount)
            self.db.update_user_stats(user_id, True, win_amount)
            self.check_streak_bonus(user_id, user['win_streak'] + 1)
        else:
            self.db.update_user_balance(user_id, -bet_amount) 
            self.db.update_user_stats(user_id, False, bet_amount)
            self.check_lose_streak_bonus(user_id, user['lose_streak'] + 1)
        
        self.db.add_game_activity(
            user_id, "slots", bet_amount, win_amount, 
            "win" if win_amount > 0 else "lose"
        )
        
        # Показываем результат
        result_display = f"[ {reels[0]} | {reels[1]} | {reels[2]} ]"
        
        text = f"""
🎰 *Результат слотов*

{result_display}

*Ставка:* {bet_amount}⭐
*Результат:* {result_text}

💰 *Новый баланс:* {user['balance'] + (win_amount - bet_amount)}⭐
        """
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("🎰 Крутить снова", callback_data=f"slots_bet_{bet_amount}"),
            InlineKeyboardButton("📊 Статистика", callback_data="show_balance")
        )
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    def show_dice_menu(self, call):
        """Показывает меню костей"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("10⭐", callback_data="dice_bet_10"),
            InlineKeyboardButton("50⭐", callback_data="dice_bet_50"), 
            InlineKeyboardButton("100⭐", callback_data="dice_bet_100")
        )
        keyboard.row(
            InlineKeyboardButton("🎯 Классика", callback_data="dice_mode_classic"),
            InlineKeyboardButton("⚪ Чёт/Нечет", callback_data="dice_mode_even_odd")
        )
        keyboard.row(
            InlineKeyboardButton("📈 Высокое/Низкое", callback_data="dice_mode_high_low"),
            InlineKeyboardButton("📊 Правила", callback_data="dice_rules")
        )
        
        text = """
🎲 *Игра в кости*

*Режимы игры:*
• *🎯 Классика* - ставка на конкретное число (2-12)
• *⚪ Чёт/Нечет* - ставка на четность суммы
• *📈 Высокое/Низкое* - ставка на диапазон

Выберите ставку и режим игры!
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    def handle_dice_bet(self, call):
        """Обрабатывает ставку в костях"""
        # Реализация игры в кости
        self.bot.answer_callback_query(call.id, "🎲 Бросок костей!")
        
        # Отправляем анимацию броска костей
        dice_message = self.bot.send_dice(call.message.chat.id, emoji='🎲')
        
        # Ждем завершения анимации
        time.sleep(4)
        
        # Определяем результат
        dice_value = dice_message.dice.value
        bet_amount = 10  # Базовая ставка
        
        # Здесь должна быть логика расчета выигрыша
        # Временно просто показываем результат
        text = f"""
🎲 *Результат броска*

Выпало: {dice_value}

*Ставка:* {bet_amount}⭐
*Режим:* Классика

💡 Выберите число для следующей ставки!
        """
        
        keyboard = InlineKeyboardMarkup()
        for i in range(2, 13):
            if i <= 7:
                keyboard.add(InlineKeyboardButton(f"{i}", callback_data=f"dice_number_{i}"))
            else:
                if i == 8:
                    keyboard.add(InlineKeyboardButton(f"{i}", callback_data=f"dice_number_{i}"))
        
        self.bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    def show_roulette_menu(self, call):
        """Показывает меню рулетки"""
        keyboard = InlineKeyboardMarkup()
        
        # Ставки
        keyboard.row(
            InlineKeyboardButton("10⭐", callback_data="roulette_bet_10"),
            InlineKeyboardButton("50⭐", callback_data="roulette_bet_50"),
            InlineKeyboardButton("100⭐", callback_data="roulette_bet_100")
        )
        
        # Типы ставок
        keyboard.row(
            InlineKeyboardButton("🔴 Красное", callback_data="roulette_color_red"),
            InlineKeyboardButton("⚫ Черное", callback_data="roulette_color_black")
        )
        keyboard.row(
            InlineKeyboardButton("⚪ Четное", callback_data="roulette_even"),
            InlineKeyboardButton("🔘 Нечетное", callback_data="roulette_odd")
        )
        keyboard.row(
            InlineKeyboardButton("1-12", callback_data="roulette_dozen_1"),
            InlineKeyboardButton("13-24", callback_data="roulette_dozen_2"),
            InlineKeyboardButton("25-36", callback_data="roulette_dozen_3")
        )
        
        text = """
🎡 *Европейская рулетка*

*Доступные ставки:*
• *Цвет* (x2) - 🔴 Красное / ⚫ Черное
• *Четность* (x2) - ⚪ Четное / 🔘 Нечетное  
• *Дюжины* (x3) - 1-12, 13-24, 25-36
• *Конкретное число* (x36) - 0-36

Выберите тип ставки и сумму!
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    def handle_roulette_bet(self, call):
        """Обрабатывает ставку в рулетке"""
        # Реализация рулетки
        self.bot.answer_callback_query(call.id, "🎡 Вращение рулетки!")
        
        # Здесь должна быть логика игры в рулетку
        # Временно показываем сообщение
        text = """
🎡 *Рулетка*

Функция в разработке...
В следующем обновлении будет полностью реализована!
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    def show_blackjack_menu(self, call):
        """Показывает меню блэкджека"""
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("20⭐", callback_data="blackjack_bet_20"),
            InlineKeyboardButton("50⭐", callback_data="blackjack_bet_50"),
            InlineKeyboardButton("100⭐", callback_data="blackjack_bet_100")
        )
        keyboard.row(
            InlineKeyboardButton("250⭐", callback_data="blackjack_bet_250"),
            InlineKeyboardButton("500⭐", callback_data="blackjack_bet_500")
        )
        keyboard.row(
            InlineKeyboardButton("🎯 Начать игру", callback_data="blackjack_start"),
            InlineKeyboardButton("📊 Правила", callback_data="blackjack_rules")
        )
        
        text = """
🃏 *Блэкджек*

*Минимальная ставка:* 20⭐
*Цель:* набрать 21 очко или больше дилера

*Правила:*
• Карты 2-10 = номинал
• Валет, Дама, Король = 10
• Туз = 1 или 11
• Блэкджек = 21 с двумя картами (x2.5)

Выберите ставку и начните игру!
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    def handle_blackjack_bet(self, call):
        """Обрабатывает ставку в блэкджеке"""
        # Реализация блэкджека
        self.bot.answer_callback_query(call.id, "🃏 Начало игры!")
        
        # Здесь должна быть логика игры в блэкджек
        # Временно показываем сообщение
        text = """
🃏 *Блэкджек*

Функция в разработке...
В следующем обновлении будет полностью реализована!
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    def handle_admin_callback(self, call):
        """Обрабатывает админ callback'и"""
        if call.data == "admin_stats":
            self.show_admin_stats(call)
        elif call.data == "admin_users":
            self.show_admin_users(call)
        elif call.data == "admin_balance":
            self.show_admin_balance(call)
        elif call.data == "admin_games":
            self.show_admin_games(call)
        elif call.data == "admin_finance":
            self.show_admin_finance(call)
        elif call.data == "admin_settings":
            self.show_admin_settings(call)
    
    def show_admin_stats(self, call):
        """Показывает статистику бота для админа"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE last_active > datetime("now", "-1 day")')
        active_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(balance) FROM users')
        total_balance = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "deposit"')
        total_deposited = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "withdraw"')
        total_withdrawn = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM game_activity')
        total_games = cursor.fetchone()[0]
        
        conn.close()
        
        text = f"""
📊 *Статистика бота*

👥 *Пользователи:*
Всего пользователей: {total_users}
Активных за сутки: {active_users}

💰 *Финансы:*
Общий баланс: {total_balance}⭐
Всего пополнено: {total_deposited}⭐
Всего выведено: {abs(total_withdrawn)}⭐

🎮 *Игры:*
Всего сыграно игр: {total_games}

🔄 *Система:*
Бот работает стабильно
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    def show_admin_users(self, call):
        """Показывает управление пользователями"""
        text = """
👥 *Управление пользователями*

Функции управления пользователями будут добавлены в следующем обновлении.
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    def show_admin_balance(self, call):
        """Показывает управление балансами"""
        text = """
💰 *Управление балансами*

Функции управления балансами будут добавлены в следующем обновлении.
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    def show_admin_games(self, call):
        """Показывает игровую статистику"""
        text = """
🎮 *Игровая статистика*

Функции просмотра игровой статистики будут добавлены в следующем обновлении.
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    def show_admin_finance(self, call):
        """Показывает финансовую статистику"""
        text = """
📈 *Финансовая статистика*

Функции финансовой статистики будут добавлены в следующем обновлении.
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    def show_admin_settings(self, call):
        """Показывает настройки бота"""
        text = """
⚙️ *Настройки бота*

Функции настроек будут добавлены в следующем обновлении.
        """
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    
    def handle_text_message(self, message):
        """Обрабатывает текстовые сообщения"""
        # Обработка пополнений (имитация)
        if "пополнить" in message.text.lower() or "deposit" in message.text.lower():
            self.show_deposit_menu(message)
        elif "игры" in message.text.lower() or "games" in message.text.lower():
            self.show_games_menu(message)
        elif "баланс" in message.text.lower() or "balance" in message.text.lower():
            self.show_balance(message)
        elif "вывод" in message.text.lower() or "withdraw" in message.text.lower():
            self.start_withdrawal(message)
        elif "статистика" in message.text.lower() or "stats" in message.text.lower():
            self.show_stats(message)
        elif "помощь" in message.text.lower() or "help" in message.text.lower():
            self.show_help(message)
        else:
            # Ответ на неизвестные сообщения
            self.bot.reply_to(
                message,
                "🤖 Я не понял ваше сообщение. Используйте /help для списка команд."
            )
    
    def check_streak_bonus(self, user_id: int, streak: int):
        """Проверяет и выдает бонус за серию побед"""
        if streak in WIN_STREAK_BONUSES:
            bonus_data = WIN_STREAK_BONUSES[streak]
            self.db.update_user_balance(user_id, bonus_data["bonus"])
            self.db.add_transaction(
                user_id, "bonus", bonus_data["bonus"], 
                f"Бонус за серию {streak} побед"
            )
            
            # Отправляем уведомление
            user = self.db.get_user(user_id)
            if user:
                self.bot.send_message(
                    user_id,
                    f"🎉 {bonus_data['message']}\n💰 Новый баланс: {user['balance'] + bonus_data['bonus']}⭐",
                    parse_mode="Markdown"
                )
    
    def check_lose_streak_bonus(self, user_id: int, streak: int):
        """Проверяет и выдает бонус за серию поражений"""
        if streak in LOSE_STREAK_BONUSES:
            bonus_data = LOSE_STREAK_BONUSES[streak]
            self.db.update_user_balance(user_id, bonus_data["bonus"])
            self.db.add_transaction(
                user_id, "bonus", bonus_data["bonus"],
                f"Бонус за серию {streak} поражений"  
            )
            
            # Отправляем уведомление
            user = self.db.get_user(user_id)
            if user:
                self.bot.send_message(
                    user_id,
                    f"💫 {bonus_data['message']}\n💰 Новый баланс: {user['balance'] + bonus_data['bonus']}⭐",
                    parse_mode="Markdown"
                )
    
    def migrate_user_data(self):
        """Миграция данных пользователей"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Добавляем новые поля если их нет
            cursor.execute('PRAGMA table_info(users)')
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'max_win_streak' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN max_win_streak INTEGER DEFAULT 0')
            
            if 'total_deposited' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN total_deposited INTEGER DEFAULT 0')
            
            if 'total_withdrawn' not in columns:
                cursor.execute('ALTER TABLE users ADD COLUMN total_withdrawn INTEGER DEFAULT 0')
            
            conn.commit()
            conn.close()
            print("✅ Миграция данных пользователей завершена")
            
        except Exception as e:
            print(f"❌ Ошибка миграции пользователей: {e}")
    
    def migrate_activity_data(self):
        """Миграция данных активности"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Создаем таблицу если не существует
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_activity_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    game_type TEXT,
                    bet_amount INTEGER,
                    win_amount INTEGER, 
                    result TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Переносим данные если старая таблица существует
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='game_activity'
            ''')
            
            if cursor.fetchone():
                cursor.execute('''
                    INSERT INTO game_activity_new 
                    (user_id, game_type, bet_amount, win_amount, result, timestamp)
                    SELECT user_id, game_type, bet_amount, win_amount, result, timestamp
                    FROM game_activity
                ''')
                
                cursor.execute('DROP TABLE game_activity')
                cursor.execute('ALTER TABLE game_activity_new RENAME TO game_activity')
            
            conn.commit()
            conn.close()
            print("✅ Миграция данных активности завершена")
            
        except Exception as e:
            print(f"❌ Ошибка миграции активности: {e}")
    
    def run(self):
        """Запускает бота"""
        print("🔄 Запуск миграции данных...")
        self.migrate_user_data()
        self.migrate_activity_data()
        
        print("🎰 Бот запущен...")
        self.bot.polling(none_stop=True)

# ========== ЗАПУСК БОТА ==========

if __name__ == "__main__":
    # Замените 'YOUR_BOT_TOKEN' на реальный токен от @BotFather
    TOKEN = "YOUR_BOT_TOKEN"
    
    bot = CasinoBot(TOKEN)
    bot.run()
