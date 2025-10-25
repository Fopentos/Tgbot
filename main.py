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

# 🎯 НАСТРОЙКИ ИГР
GAME_COST = 5

# 💰 ПАКЕТЫ ПОПОЛНЕНИЯ (1 реальная звезда = 1 игровая звезда)
PRODUCTS = {
    "pack_5": {"title": "5 Игровых звезд", "description": "Пополнение баланса на 5 игровых звезд", "price": 5, "currency": "XTR", "credits": 5},
    "pack_10": {"title": "10 Игровых звезд", "description": "Пополнение баланса на 10 игровых звезд", "price": 10, "currency": "XTR", "credits": 10},
    "pack_25": {"title": "25 Игровых звезд", "description": "Пополнение баланса на 25 игровых звезд", "price": 25, "currency": "XTR", "credits": 25},
    "pack_50": {"title": "50 Игровых звезд", "description": "Пополнение баланса на 50 игровых звезд", "price": 50, "currency": "XTR", "credits": 50},
    "pack_100": {"title": "100 Игровых звезд", "description": "Пополнение баланса на 100 игровых звезд", "price": 100, "currency": "XTR", "credits": 100},
    "pack_250": {"title": "250 Игровых звезд", "description": "Пополнение баланса на 250 игровых звезд", "price": 250, "currency": "XTR", "credits": 250},
    "pack_500": {"title": "500 Игровых звезд", "description": "Пополнение баланса на 500 игровых звезд", "price": 500, "currency": "XTR", "credits": 500},
    "pack_1000": {"title": "1000 Игровых звезд", "description": "Пополнение баланса на 1000 игровых звезд", "price": 1000, "currency": "XTR", "credits": 1000}
}

# 🎰 ПРАВИЛЬНАЯ КОНФИГУРАЦИЯ СЛОТОВ
SLOT_CONFIG = {
    1: {"name": "ТРИ БАРА", "stars": 15},
    22: {"name": "ТРИ ВИШНИ", "stars": 25}, 
    43: {"name": "ТРИ ЛИМОНА", "stars": 50},
    64: {"name": "ДЖЕКПОТ 777", "stars": 100}
}

# 🎮 КОНФИГУРАЦИЯ ИГР
GAMES_CONFIG = {
    "🎰": {"cost": 5, "type": "slots"},
    "🎯": {"cost": 5, "type": "dart", "win": 6, "prize": 15},
    "🎲": {"cost": 5, "type": "dice", "win": 6, "prize": 15},
    "🎳": {"cost": 5, "type": "bowling", "win": 6, "prize": 15},
    "⚽": {"cost": 5, "type": "football", "win": 5, "prize": 15},
    "🏀": {"cost": 5, "type": "basketball", "win": 5, "prize": 15}
}

# 🗃️ БАЗА ДАННЫХ
user_data = defaultdict(lambda: {
    'game_balance': 0,  # Стартовый баланс 0
    'total_games': 0,
    'total_wins': 0,
    'total_deposited': 0,
    'real_money_spent': 0,
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

Доступные игры (5 звезд за игру):
🎰 Слоты - шанс выиграть до 100 звезд!
🎯 Дартс | 🎲 Кубик | 🎳 Боулинг
⚽ Футбол | 🏀 Баскетбол

💰 Пополнение: 1:1
1 реальная звезда = 1 игровая звезда

🎁 Система активности:
Играй 3+ раза в день 7 дней подряд = случайный подарок (15-50 звезд)

Команды:
/profile - Личный кабинет
/deposit - Пополнить баланс  
/activity - Моя активность

Нажми "🎮 Играть" чтобы начать!
    """
    
    await update.message.reply_text(welcome_text)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    data = user_data[user_id]
    
    win_rate = (data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0
    
    profile_text = f"""
📊 Личный кабинет

👤 Имя: {user.first_name}
💰 Баланс: {data['game_balance']} звезд
🎮 Всего игр: {data['total_games']}
🏆 Побед: {data['total_wins']}
📈 Винрейт: {win_rate:.1f}%
💳 Пополнено: {data['total_deposited']} звезд
    """
    
    keyboard = [
        [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton("🎮 Играть", callback_data="play_games")]
    ]
    
    if admin_mode.get(user_id, False):
        keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(profile_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(profile_text, reply_markup=reply_markup)

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /deposit"""
    user_id = update.effective_user.id
    data = user_data[user_id]
    
    deposit_text = f"""
💰 Пополнение баланса

💎 Текущий баланс: {data['game_balance']} звезд

🎯 Выберите пакет пополнения:
💫 1 реальная звезда = 1 игровая звезда
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

💎 Текущий баланс: {current_balance} звезд

🎯 Выберите пакет пополнения:
💫 1 реальная звезда = 1 игровая звезда
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
        prices=[LabeledPrice(product["title"], product["price"] * 100)],
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
        f"💎 Зачислено: {product['credits']} игровых звезд\n"
        f"💰 Баланс: {user_data[user_id]['game_balance']} звезд\n\n"
        f"🎮 Приятной игры!"
    )

# 🎮 СИСТЕМА ИГР
async def play_games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    balance = user_data[user_id]['game_balance']
    
    games_text = f"""
🎮 Выбор игры

💎 Баланс: {balance} звезд
🎯 Стоимость игры: 5 звезд

Выберите игру:
    """
    
    keyboard = [
        [InlineKeyboardButton("🎰 Слоты (5 звезд)", callback_data="play_slots")],
        [InlineKeyboardButton("🎯 Дартс (5 звезд)", callback_data="play_dart")],
        [InlineKeyboardButton("🎲 Кубик (5 звезд)", callback_data="play_dice")],
        [InlineKeyboardButton("🎳 Боулинг (5 звезд)", callback_data="play_bowling")],
        [InlineKeyboardButton("⚽ Футбол (5 звезд)", callback_data="play_football")],
        [InlineKeyboardButton("🏀 Баскетбол (5 звезд)", callback_data="play_basketball")],
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
    
    # ПРОВЕРКА БАЛАНСА
    if user_data[user_id]['game_balance'] < GAME_COST:
        await query.edit_message_text(
            "❌ Недостаточно средств!\n\n"
            f"💰 Ваш баланс: {user_data[user_id]['game_balance']} звезд\n"
            f"🎯 Требуется: {GAME_COST} звезд\n\n"
            "💳 Пополните баланс чтобы играть!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
                [InlineKeyboardButton("📊 Личный кабинет", callback_data="back_to_profile")]
            ])
        )
        return
    
    # СПИСАНИЕ СРЕДСТВ
    user_data[user_id]['game_balance'] -= GAME_COST
    user_data[user_id]['total_games'] += 1
    user_data[user_id]['last_activity'] = datetime.datetime.now().isoformat()
    
    game_emojis = {
        'slots': '🎰', 'dart': '🎯', 'dice': '🎲',
        'bowling': '🎳', 'football': '⚽', 'basketball': '🏀'
    }
    
    emoji = game_emojis.get(game_type, '🎰')
    
    # Сохраняем информацию об игре для обработки результата
    context.user_data['expecting_dice'] = True
    context.user_data['last_game_type'] = game_type
    context.user_data['last_game_user_id'] = user_id
    
    dice_message = await context.bot.send_dice(chat_id=query.message.chat_id, emoji=emoji)
    context.user_data['last_dice_message_id'] = dice_message.message_id
    
    message_text = f"🎮 Игра запущена! {emoji}\n💸 Списано: {GAME_COST} звезд\n💰 Остаток: {user_data[user_id]['game_balance']} звезд"
    
    await query.edit_message_text(message_text)
    save_data()

# 🎰 ОБРАБОТКА DICE - ИСПРАВЛЕННАЯ!
async def handle_dice_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    # Проверяем, что это результат нашей игры
    if not message.dice:
        return
    
    # Проверяем, ожидаем ли мы dice от этого пользователя
    if not context.user_data.get('expecting_dice', False):
        return
    
    # Проверяем, что это тот же пользователь
    if context.user_data.get('last_game_user_id') != user_id:
        return
    
    emoji = message.dice.emoji
    value = message.dice.value
    
    user_data[user_id]['last_activity'] = datetime.datetime.now().isoformat()
    
    result_text = ""
    
    # 🎰 ОБРАБОТКА СЛОТОВ
    if emoji == "🎰":
        print(f"🎰 Slot value: {value}")
        
        if value in SLOT_CONFIG:
            win_combo = SLOT_CONFIG[value]
            user_data[user_id]['game_balance'] += win_combo["stars"]
            user_data[user_id]['total_wins'] += 1
            
            result_text = (
                f"🎉 {win_combo['name']}!\n\n"
                f"💰 Выигрыш: {win_combo['stars']} звезд\n"
                f"💎 Баланс: {user_data[user_id]['game_balance']} звезд"
            )
        else:
            result_text = f"😢 Не повезло...\n💎 Баланс: {user_data[user_id]['game_balance']} звезд"
    
    # 🎯 ДРУГИЕ ИГРЫ
    else:
        game_type = context.user_data.get('last_game_type')
        if not game_type:
            return
            
        game_config = None
        for emoji_key, config in GAMES_CONFIG.items():
            if config["type"] == game_type:
                game_config = config
                break
        
        if game_config and value == game_config["win"]:
            base_prize = game_config["prize"]
            user_data[user_id]['game_balance'] += base_prize
            user_data[user_id]['total_wins'] += 1
            
            game_names = {
                "dart": "🎯 ПОПАДАНИЕ В ЦЕЛЬ!",
                "dice": "🎲 ВЫПАЛО 6!",
                "bowling": "🎳 СТРАЙК!",
                "football": "⚽ ГОООЛ!",
                "basketball": "🏀 ПОПАДАНИЕ!"
            }
            
            result_text = (
                f"🎉 {game_names[game_type]}\n\n"
                f"💰 Выигрыш: {base_prize} звезд\n"
                f"💎 Баланс: {user_data[user_id]['game_balance']} звезд"
            )
        else:
            result_text = f"😢 Мимо...\n💎 Баланс: {user_data[user_id]['game_balance']} звезд"
    
    # Отправляем результат
    if result_text:
        await message.reply_text(result_text)
    
    # 📊 ОБНОВЛЕНИЕ АКТИВНОСТИ
    weekly_reward = update_daily_activity(user_id)
    if weekly_reward:
        user_data[user_id]['game_balance'] += weekly_reward
        await message.reply_text(
            f"🎁 ЕЖЕНЕДЕЛЬНАЯ НАГРАДА!\n\n"
            f"💰 Награда: {weekly_reward} звезд\n"
            f"💎 Баланс: {user_data[user_id]['game_balance']} звезд"
        )
    
    # Очищаем данные игры
    context.user_data.pop('expecting_dice', None)
    context.user_data.pop('last_game_type', None)
    context.user_data.pop('last_dice_message_id', None)
    context.user_data.pop('last_game_user_id', None)
    
    save_data()

# 👑 АДМИН СИСТЕМА
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if len(context.args) == 0:
        await update.message.reply_text("Использование: /admin <код>")
        return
    
    code = context.args[0]
    if code == ADMIN_CODE:
        admin_mode[user_id] = True
        await update.message.reply_text("👑 Режим администратора активирован!")

# 🔄 ОБРАБОТЧИКИ КНОПОК
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    callback_data = query.data
    
    if callback_data.startswith('buy_'):
        await handle_deposit_selection(update, context)
    elif callback_data.startswith('play_'):
        await handle_game_selection(update, context)
    elif callback_data == 'deposit':
        await deposit_callback(update, context)
    elif callback_data == 'play_games':
        await play_games_callback(update, context)
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
    return "🎰 NSource Casino Bot is alive!"

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
    
    # CALLBACK'И
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # ПЛАТЕЖИ
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    
    # DICE СООБЩЕНИЯ
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice_result))
    
    print("🎰 NSource Casino Bot запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
