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

# 💰 ПАКЕТЫ ПОПОЛНЕНИЯ
PRODUCTS = {
    "pack_5": {"title": "5 Игровых звезд", "description": "Пополнение баланса на 5 игровых звезд", "price": 5, "currency": "XTR", "credits": 5},
    "pack_10": {"title": "10 Игровых звезд", "description": "Пополнение баланса на 10 игровых звезд", "price": 10, "currency": "XTR", "credits": 10},
}

# 🎰 КОНФИГУРАЦИЯ СЛОТОВ (упрощенная для теста)
SLOT_CONFIG = {
    1: {"name": "ДЖЕКПОТ 777", "stars": 100},
    22: {"name": "ТРИ ЛИМОНА", "stars": 50},
    33: {"name": "ТРИ ВИШНИ", "stars": 25},
    44: {"name": "ТРИ БАРА", "stars": 15},
}

# 🎮 КОНФИГУРАЦИЯ ИГР
GAMES_CONFIG = {
    "🎰": {"cost": 5, "type": "slots"},
    "🎯": {"cost": 5, "type": "dart", "win": 6, "prize": 15},
    "🎲": {"cost": 5, "type": "dice", "win": 6, "prize": 15},
}

# 🗃️ БАЗА ДАННЫХ
user_data = defaultdict(lambda: {
    'game_balance': 100,  # Стартовый баланс для теста
    'total_games': 0,
    'total_wins': 0,
})

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎰 NSource Casino Бот\n\n"
        "Доступные игры:\n"
        "🎰 Слоты | 🎯 Дартс | 🎲 Кубик\n\n"
        "Просто отправь эмодзи игры чтобы начать!"
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    data = user_data[user_id]
    
    profile_text = f"""
📊 Личный кабинет

👤 Имя: {user.first_name}
💰 Баланс: {data['game_balance']} звезд
🎮 Всего игр: {data['total_games']}
🏆 Побед: {data['total_wins']}
    """
    
    keyboard = [
        [InlineKeyboardButton("🎮 Играть", callback_data="play_games")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(profile_text, reply_markup=reply_markup)

# 🎮 СИСТЕМА ИГР
async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    emoji = update.message.text
    
    if emoji not in GAMES_CONFIG:
        return
    
    if user_data[user_id]['game_balance'] < GAME_COST:
        await update.message.reply_text("❌ Недостаточно средств! Баланс: " + str(user_data[user_id]['game_balance']))
        return
    
    user_data[user_id]['game_balance'] -= GAME_COST
    user_data[user_id]['total_games'] += 1
    
    game_type = GAMES_CONFIG[emoji]["type"]
    context.user_data['expecting_dice'] = True
    context.user_data['last_game_type'] = game_type
    context.user_data['last_game_user_id'] = user_id
    
    dice_message = await context.bot.send_dice(chat_id=update.message.chat_id, emoji=emoji)
    context.user_data['last_dice_message_id'] = dice_message.message_id
    
    await update.message.reply_text(f"🎮 Игра запущена! {emoji}\n💸 Списано: {GAME_COST} звезд\n💰 Остаток: {user_data[user_id]['game_balance']} звезд")

# 🎰 ОБРАБОТКА DICE - ИСПРАВЛЕННАЯ!
async def handle_dice_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if not message.dice:
        return
    
    if not context.user_data.get('expecting_dice', False):
        return
    
    if context.user_data.get('last_game_user_id') != user_id:
        return
    
    emoji = message.dice.emoji
    value = message.dice.value
    
    result_text = ""
    
    if emoji == "🎰":
        if value in SLOT_CONFIG:
            win_combo = SLOT_CONFIG[value]
            user_data[user_id]['game_balance'] += win_combo["stars"]
            user_data[user_id]['total_wins'] += 1
            result_text = f"🎉 {win_combo['name']}!\n💰 Выигрыш: {win_combo['stars']} звезд\n💎 Баланс: {user_data[user_id]['game_balance']} звезд"
        else:
            result_text = f"😢 Не повезло...\n💎 Баланс: {user_data[user_id]['game_balance']} звезд"
    
    elif emoji in ["🎯", "🎲", "🎳", "⚽", "🏀"]:
        if value == 6:  # Для дартса и кубика
            prize = 15
            user_data[user_id]['game_balance'] += prize
            user_data[user_id]['total_wins'] += 1
            result_text = f"🎉 ПОБЕДА!\n💰 Выигрыш: {prize} звезд\n💎 Баланс: {user_data[user_id]['game_balance']} звезд"
        else:
            result_text = f"😢 Мимо...\n💎 Баланс: {user_data[user_id]['game_balance']} звезд"
    
    if result_text:
        await message.reply_text(result_text)
    
    context.user_data.pop('expecting_dice', None)
    context.user_data.pop('last_game_type', None)
    context.user_data.pop('last_dice_message_id', None)
    context.user_data.pop('last_game_user_id', None)

# 🔄 ОБРАБОТЧИКИ КНОПОК
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    callback_data = query.data
    
    if callback_data == 'play_games':
        user_id = query.from_user.id
        balance = user_data[user_id]['game_balance']
        
        games_text = f"🎮 Выбор игры\n💎 Баланс: {balance} звезд"
        
        keyboard = [
            [InlineKeyboardButton("🎰 Слоты (5 звезд)", callback_data="play_slots")],
            [InlineKeyboardButton("🎯 Дартс (5 звезд)", callback_data="play_dart")],
            [InlineKeyboardButton("🎲 Кубик (5 звезд)", callback_data="play_dice")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(games_text, reply_markup=reply_markup)
    
    elif callback_data.startswith('play_'):
        user_id = query.from_user.id
        game_type = callback_data.replace("play_", "")
        
        if user_data[user_id]['game_balance'] < GAME_COST:
            await query.answer("❌ Недостаточно средств!", show_alert=True)
            return
        
        user_data[user_id]['game_balance'] -= GAME_COST
        user_data[user_id]['total_games'] += 1
        
        game_emojis = {'slots': '🎰', 'dart': '🎯', 'dice': '🎲'}
        emoji = game_emojis.get(game_type, '🎰')
        
        context.user_data['expecting_dice'] = True
        context.user_data['last_game_type'] = game_type
        context.user_data['last_game_user_id'] = user_id
        
        dice_message = await context.bot.send_dice(chat_id=query.message.chat_id, emoji=emoji)
        context.user_data['last_dice_message_id'] = dice_message.message_id
        
        await query.edit_message_text(
            f"🎮 Игра запущена! {emoji}\n💸 Списано: {GAME_COST} звезд\n💰 Остаток: {user_data[user_id]['game_balance']} звезд"
        )

# 🌐 FLASK ДЛЯ RAILWAY
app = Flask(__name__)

@app.route('/')
def home():
    return "🎰 NSource Casino Bot is running!"

@app.route('/health')
def health():
    return "OK"

# 🚀 ЗАПУСК БОТА
def main():
    # Получаем порт из переменных Railway
    port = int(os.environ.get("PORT", 5000))
    
    # Запускаем Flask в отдельном потоке
    def run_flask():
        app.run(host='0.0.0.0', port=port)
    
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Создаем и запускаем бота
    application = Application.builder().token(BOT_TOKEN).build()
    
    # КОМАНДЫ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    
    # CALLBACK'И
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # СООБЩЕНИЯ - ИСПРАВЛЕННЫЕ ФИЛЬТРЫ!
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(🎰|🎯|🎲)$"), handle_game_message))
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice_result))  # ИСПРАВЛЕННАЯ СТРОКА!
    
    print("🎰 NSource Casino Bot запущен на Railway!")
    application.run_polling()

if __name__ == '__main__':
    main()
