import os
import json
import datetime
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from threading import Thread
from flask import Flask

# 🔧 КОНФИГУРАЦИЯ
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8378526693:AAFOwAb6pVp1GOE0tXZN4PDLFnD_TTT1djg")
GAME_COST = 5

# 🎰 КОНФИГУРАЦИЯ ВСЕХ ИГР С ПОЛНЫМИ РЕЗУЛЬТАТАМИ
GAMES_CONFIG = {
    "🎰": {
        "cost": 5,
        "values": {
            # ВЫИГРЫШНЫЕ КОМБИНАЦИИ (определены тобой)
            1: {"win": True, "prize": 15, "message": "🎰 ТРИ БАРА! Выигрыш: 15 звезд"},
            22: {"win": True, "prize": 25, "message": "🎰 ТРИ ВИШНИ! Выигрыш: 25 звезд"},
            43: {"win": True, "prize": 50, "message": "🎰 ТРИ ЛИМОНА! Выигрыш: 50 звезд"},
            64: {"win": True, "prize": 100, "message": "🎰 ДЖЕКПОТ 777! Выигрыш: 100 звезд"},
            # ПРОИГРЫШНЫЕ КОМБИНАЦИИ (все остальные значения)
            **{i: {"win": False, "prize": 0, "message": f"🎰 Комбинация #{i} - Не повезло..."} for i in range(1, 65) if i not in [1, 22, 43, 64]}
        }
    },
    "🎯": {
        "cost": 5,
        "values": {
            # Дартс: 1-6, где 6 - победа
            1: {"win": False, "prize": 0, "message": "🎯 Мимо цели... Попробуй еще!"},
            2: {"win": False, "prize": 0, "message": "🎯 Близко, но не попал!"},
            3: {"win": False, "prize": 0, "message": "🎯 Почти у цели!"},
            4: {"win": False, "prize": 0, "message": "🎯 Рядом с мишенью!"},
            5: {"win": False, "prize": 0, "message": "🎯 Задел край мишени!"},
            6: {"win": True, "prize": 15, "message": "🎯 ПОПАДАНИЕ В ЦЕЛЬ! Выигрыш: 15 звезд"}
        }
    },
    "🎲": {
        "cost": 5,
        "values": {
            # Кости: 1-6, где 6 - победа
            1: {"win": False, "prize": 0, "message": "🎲 Выпала 1... Не повезло!"},
            2: {"win": False, "prize": 0, "message": "🎲 Выпала 2... Почти!"},
            3: {"win": False, "prize": 0, "message": "🎲 Выпала 3... Уже лучше!"},
            4: {"win": False, "prize": 0, "message": "🎲 Выпала 4... Близко!"},
            5: {"win": False, "prize": 0, "message": "🎲 Выпала 5... Еще чуть-чуть!"},
            6: {"win": True, "prize": 15, "message": "🎲 ВЫПАЛО 6! Выигрыш: 15 звезд"}
        }
    },
    "🎳": {
        "cost": 5,
        "values": {
            # Боулинг: 1-6, где 6 - страйк
            1: {"win": False, "prize": 0, "message": "🎳 Всего 1 кегля... Неудача!"},
            2: {"win": False, "prize": 0, "message": "🎳 2 кегли... Могло быть лучше!"},
            3: {"win": False, "prize": 0, "message": "🎳 3 кегли... Неплохо!"},
            4: {"win": False, "prize": 0, "message": "🎳 4 кегли... Хороший бросок!"},
            5: {"win": False, "prize": 0, "message": "🎳 5 кеглей... Почти страйк!"},
            6: {"win": True, "prize": 15, "message": "🎳 СТРАЙК! Выигрыш: 15 звезд"}
        }
    },
    "⚽": {
        "cost": 5,
        "values": {
            # Футбол: 1-5, где 5 - гол
            1: {"win": False, "prize": 0, "message": "⚽ Мяч ушел в аут..."},
            2: {"win": False, "prize": 0, "message": "⚽ Удар по штанге!"},
            3: {"win": False, "prize": 0, "message": "⚽ Мяч заблокирован защитником!"},
            4: {"win": False, "prize": 0, "message": "⚽ Вратарь парировал удар!"},
            5: {"win": True, "prize": 15, "message": "⚽ ГОООЛ! Выигрыш: 15 звезд"}
        }
    },
    "🏀": {
        "cost": 5,
        "values": {
            # Баскетбол: 1-5, где 5 - попадание
            1: {"win": False, "prize": 0, "message": "🏀 Промах... Мимо кольца!"},
            2: {"win": False, "prize": 0, "message": "🏀 Мяч задел обод!"},
            3: {"win": False, "prize": 0, "message": "🏀 Колебался на ободе и вылетел!"},
            4: {"win": False, "prize": 0, "message": "🏀 Почти попал!"},
            5: {"win": True, "prize": 15, "message": "🏀 ПОПАДАНИЕ! Выигрыш: 15 звезд"}
        }
    }
}

# 🗃️ БАЗА ДАННЫХ
user_data = defaultdict(lambda: {
    'game_balance': 100,  # Стартовый баланс для тестирования
    'total_games': 0,
    'total_wins': 0,
    'last_activity': datetime.datetime.now().isoformat()
})

# 💾 СОХРАНЕНИЕ ДАННЫХ
def save_data():
    try:
        with open('game_data.json', 'w') as f:
            json.dump(dict(user_data), f, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

def load_data():
    try:
        with open('game_data.json', 'r') as f:
            data = json.load(f)
            user_data.update(data)
    except FileNotFoundError:
        pass

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 ИГРОВОЙ БОТ С ПОЛНОЙ СИСТЕМОЙ\n\n"
        "Доступные игры (5 звезд за попытку):\n"
        "🎰 Слоты - 64 варианта, 4 выигрышных комбинации\n"
        "🎯 Дартс - 6 вариантов, победа на 6\n"  
        "🎲 Кубик - 6 вариантов, победа на 6\n"
        "🎳 Боулинг - 6 вариантов, победа на 6\n"
        "⚽ Футбол - 5 вариантов, победа на 5\n"
        "🏀 Баскетбол - 5 вариантов, победа на 5\n\n"
        "Просто отправь эмодзи игры в чат!\n\n"
        "Команды:\n"
        "/balance - Мой баланс\n"
        "/stats - Статистика\n"
        "/games - Список игр"
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    
    await update.message.reply_text(
        f"💎 Ваш баланс: {data['game_balance']} звезд\n"
        f"🎮 Всего игр: {data['total_games']}\n"
        f"🏆 Побед: {data['total_wins']}\n"
        f"📈 Винрейт: {(data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0:.1f}%"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    
    stats_text = f"""
📊 ВАША СТАТИСТИКА

💎 Баланс: {data['game_balance']} звезд
🎮 Всего игр: {data['total_games']}
🏆 Побед: {data['total_wins']}
📈 Винрейт: {(data['total_wins'] / data['total_games'] * 100) if data['total_games'] > 0 else 0:.1f}%
🕒 Последняя активность: {data['last_activity'][11:16]}
    """
    
    await update.message.reply_text(stats_text)

async def games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    games_text = """
🎮 ДОСТУПНЫЕ ИГРЫ

🎰 Слоты (5 звезд)
• 64 различных анимации
• 4 выигрышные комбинации:
  - ТРИ БАРА (15 звезд)
  - ТРИ ВИШНИ (25 звезд) 
  - ТРИ ЛИМОНА (50 звезд)
  - ДЖЕКПОТ 777 (100 звезд)

🎯 Дартс (5 звезд)
• 6 вариантов броска
• Победа при 6: 15 звезд

🎲 Кубик (5 звезд)  
• 6 вариантов броска
• Победа при 6: 15 звезд

🎳 Боулинг (5 звезд)
• 6 вариантов броска
• Победа при 6: 15 звезд

⚽ Футбол (5 звезд)
• 5 вариантов броска
• Победа при 5: 15 звезд

🏀 Баскетбол (5 звезд)
• 5 вариантов броска
• Победа при 5: 15 звезд

Просто отправь эмодзи игры в чат!
    """
    
    await update.message.reply_text(games_text)

# 🎮 ОБРАБОТКА ИГРОВЫХ СООБЩЕНИЙ
async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    emoji = update.message.text
    
    if emoji not in GAMES_CONFIG:
        return
    
    game_config = GAMES_CONFIG[emoji]
    
    # ПРОВЕРКА БАЛАНСА
    if user_data[user_id]['game_balance'] < game_config["cost"]:
        await update.message.reply_text(
            f"❌ Недостаточно средств!\n\n"
            f"💰 Ваш баланс: {user_data[user_id]['game_balance']} звезд\n"
            f"🎯 Требуется: {game_config['cost']} звезд\n\n"
            "Пополните баланс чтобы играть!"
        )
        return
    
    # СПИСАНИЕ СРЕДСТВ
    user_data[user_id]['game_balance'] -= game_config["cost"]
    user_data[user_id]['total_games'] += 1
    user_data[user_id]['last_activity'] = datetime.datetime.now().isoformat()
    
    # Сохраняем информацию об игре
    context.user_data['expecting_dice'] = True
    context.user_data['last_game_emoji'] = emoji
    context.user_data['last_game_user_id'] = user_id
    context.user_data['last_game_cost'] = game_config["cost"]
    
    # Отправляем dice
    dice_message = await context.bot.send_dice(chat_id=update.message.chat_id, emoji=emoji)
    context.user_data['last_dice_message_id'] = dice_message.message_id
    
    # Сообщение о запуске игры
    await update.message.reply_text(
        f"🎮 Запускаем {emoji}...\n"
        f"💸 Списано: {game_config['cost']} звезд\n"
        f"💰 Остаток: {user_data[user_id]['game_balance']} звезд"
    )
    
    save_data()

# 🎯 ОБРАБОТКА РЕЗУЛЬТАТОВ DICE - ПОЛНАЯ СИСТЕМА
async def handle_dice_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    # Проверяем, что это результат нашей игры
    if not message.dice:
        return
    
    if not context.user_data.get('expecting_dice', False):
        return
        
    if context.user_data.get('last_game_user_id') != user_id:
        return
    
    emoji = message.dice.emoji
    value = message.dice.value
    
    # Обновляем активность
    user_data[user_id]['last_activity'] = datetime.datetime.now().isoformat()
    
    # Получаем конфиг игры
    game_config = GAMES_CONFIG.get(emoji)
    if not game_config:
        return
    
    # Получаем результат для этого значения
    result_config = game_config["values"].get(value)
    if not result_config:
        # Если значение не найдено, считаем проигрышем
        result_config = {"win": False, "prize": 0, "message": f"{emoji} Неизвестный результат..."}
    
    # ОБРАБОТКА РЕЗУЛЬТАТА
    result_text = ""
    
    if result_config["win"]:
        # ВЫИГРЫШ
        win_amount = result_config["prize"]
        user_data[user_id]['game_balance'] += win_amount
        user_data[user_id]['total_wins'] += 1
        
        result_text = (
            f"🎉 {result_config['message']}\n\n"
            f"💎 Итоговый баланс: {user_data[user_id]['game_balance']} звезд\n"
            f"📊 (Списано: {context.user_data['last_game_cost']} звезд + Выигрыш: {win_amount} звезд)"
        )
    else:
        # ПРОИГРЫШ
        result_text = (
            f"😢 {result_config['message']}\n\n"
            f"💎 Итоговый баланс: {user_data[user_id]['game_balance']} звезд\n"
            f"📊 (Списано: {context.user_data['last_game_cost']} звезд)"
        )
    
    # Отправляем результат
    await message.reply_text(result_text)
    
    # Очищаем данные игры
    context.user_data.pop('expecting_dice', None)
    context.user_data.pop('last_game_emoji', None)
    context.user_data.pop('last_dice_message_id', None)
    context.user_data.pop('last_game_user_id', None)
    context.user_data.pop('last_game_cost', None)
    
    save_data()

# 🌐 FLASK ДЛЯ RAILWAY
app = Flask(__name__)

@app.route('/')
def home():
    return "🎮 Game Bot - Полная игровая система!"

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
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("games", games_command))
    
    # СООБЩЕНИЯ
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(🎰|🎯|🎲|🎳|⚽|🏀)$"), handle_game_message))
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice_result))
    
    print("🎮 Game Bot запущен!")
    print("🎯 Доступные игры: 🎰 🎯 🎲 🎳 ⚽ 🏀")
    application.run_polling()

if __name__ == '__main__':
    main()
