import os
import json
import datetime
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from threading import Thread
from flask import Flask

# 🔧 КОНФИГУРАЦИЯ
BOT_TOKEN = "8378526693:AAFOwAb6pVp1GOE0tXZN4PDLFnD_TTT1djg"

# 🎯 НАСТРОЙКИ ИГР
GAME_COST = 0  # Бесплатно для тестирования

# 🎰 КОНФИГУРАЦИЯ СЛОТОВ (64 значения)
SLOT_CONFIG = {
    "values": {
        1: {"win": True, "message": "🎰 ТРИ БАРА! Выигрыш!"},
        2: {"win": False, "message": "🎰 Комбинация #2 - проигрыш"},
        # ... (все 64 значения как в вашем коде)
        64: {"win": True, "message": "🎰 ДЖЕКПОТ 777! Выигрыш!"}
    }
}

# 🏀 КОНФИГУРАЦИЯ БАСКЕТБОЛА (5 значений)
BASKETBALL_CONFIG = {
    "values": {
        1: {"win": False, "message": "🏀 БРОСОК МИМО - проигрыш"},
        2: {"win": False, "message": "🏀 БРОСОК МИМО - проигрыш"}, 
        3: {"win": False, "message": "🏀 БРОСОК МИМО - проигрыш"},
        4: {"win": False, "message": "🏀 БРОСОК МИМО - проигрыш"},
        5: {"win": True, "message": "🏀 ПОПАДАНИЕ! Выигрыш!"}
    }
}

# ⚽ КОНФИГУРАЦИЯ ФУТБОЛА (5 значений)  
FOOTBALL_CONFIG = {
    "values": {
        1: {"win": False, "message": "⚽ УДАР МИМО - проигрыш"},
        2: {"win": False, "message": "⚽ УДАР МИМО - проигрыш"},
        3: {"win": False, "message": "⚽ УДАР МИМО - проигрыш"}, 
        4: {"win": False, "message": "⚽ УДАР МИМО - проигрыш"},
        5: {"win": True, "message": "⚽ ГОООЛ! Выигрыш!"}
    }
}

# 🗃️ БАЗА ДАННЫХ ДЛЯ ИССЛЕДОВАНИЯ
research_data = {
    "🎰": {},  # Для слотов
    "🏀": {},  # Для баскетбола  
    "⚽": {}   # Для футбола
}

user_data = defaultdict(lambda: {
    'total_games': 0,
})

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 РЕЖИМ ИССЛЕДОВАНИЯ АНИМАЦИЙ\n\n"
        "Исследуем анимации 🎰, 🏀 и ⚽!\n\n"
        "Команды:\n"
        "/research - Показать все найденные значения\n"
        "/test_all - Начать тестирование\n\n"
        "Отправь 🎰, 🏀 или ⚽ чтобы определить номер анимации!"
    )

async def test_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск тестирования всех игр"""
    await update.message.reply_text(
        "🎯 ТЕСТИРОВАНИЕ ВСЕХ ИГР АКТИВИРОВАНО\n\n"
        "Отправляй 🎰, 🏀 или ⚽ в чат - я буду показывать номер каждой анимации!\n\n"
        "После теста используй /research для просмотра статистики."
    )

async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать результаты исследования всех игр"""
    research_text = "📊 РЕЗУЛЬТАТЫ ИССЛЕДОВАНИЯ ВСЕХ ИГР\n\n"
    
    # Слоты
    research_text += "🎰 СЛОТЫ (64 значения):\n"
    slot_data = research_data["🎰"]
    if slot_data:
        research_text += f"📊 Найдено: {len(slot_data)}/64 значений\n"
        for value in sorted(slot_data.keys()):
            data = slot_data[value]
            research_text += f"🎰 #{value}: {data['count']} раз\n"
    else:
        research_text += "❓ Данных пока нет\n"
    
    # Баскетбол
    research_text += "\n🏀 БАСКЕТБОЛ (5 значений):\n"
    basketball_data = research_data["🏀"]
    if basketball_data:
        research_text += f"📊 Найдено: {len(basketball_data)}/5 значений\n"
        for value in sorted(basketball_data.keys()):
            data = basketball_data[value]
            config = BASKETBALL_CONFIG["values"][value]
            result = "🏆 ВЫИГРЫШ" if config["win"] else "💸 ПРОИГРЫШ"
            research_text += f"🏀 #{value}: {data['count']} раз - {result}\n"
    else:
        research_text += "❓ Данных пока нет\n"
    
    # Футбол
    research_text += "\n⚽ ФУТБОЛ (5 значений):\n"
    football_data = research_data["⚽"]
    if football_data:
        research_text += f"📊 Найдено: {len(football_data)}/5 значений\n"
        for value in sorted(football_data.keys()):
            data = football_data[value]
            config = FOOTBALL_CONFIG["values"][value]
            result = "🏆 ВЫИГРЫШ" if config["win"] else "💸 ПРОИГРЫШ"
            research_text += f"⚽ #{value}: {data['count']} раз - {result}\n"
    else:
        research_text += "❓ Данных пока нет\n"
    
    await update.message.reply_text(research_text)

# 🎮 СИСТЕМА ИГР - ТЕСТОВЫЙ РЕЖИМ ДЛЯ ВСЕХ ИГР
async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    emoji = update.message.text
    
    if emoji not in ["🎰", "🏀", "⚽"]:
        await update.message.reply_text("🎯 В этом режиме работают только 🎰, 🏀 и ⚽!")
        return
    
    user_data[user_id]['total_games'] += 1
    
    context.user_data['expecting_dice'] = True
    context.user_data['last_game_emoji'] = emoji
    context.user_data['last_game_user_id'] = user_id
    
    dice_message = await context.bot.send_dice(chat_id=update.message.chat_id, emoji=emoji)
    context.user_data['last_dice_message_id'] = dice_message.message_id
    
    game_name = {
        "🎰": "СЛОТЫ",
        "🏀": "БАСКЕТБОЛ", 
        "⚽": "ФУТБОЛ"
    }[emoji]
    
    await update.message.reply_text(
        f"🔬 Тестовый бросок #{user_data[user_id]['total_games']} ({game_name})\n"
        f"🎯 Определяю номер анимации..."
    )

# 🎯 ОБРАБОТКА DICE - УНИКАЛЬНЫЕ СООБЩЕНИЯ ДЛЯ КАЖДОГО ЗНАЧЕНИЯ
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
    
    if emoji in ["🎰", "🏀", "⚽"]:
        # СОХРАНЯЕМ ДАННЫЕ ИССЛЕДОВАНИЯ
        game_data = research_data[emoji]
        
        if value not in game_data:
            game_data[value] = {
                'first_seen': datetime.datetime.now().isoformat(),
                'count': 0,
                'users': set()
            }
        
        game_data[value]['count'] += 1
        game_data[value]['users'].add(user_id)
        
        # ПОЛУЧАЕМ КОНФИГУРАЦИЮ ДЛЯ ЭТОЙ ИГРЫ
        if emoji == "🎰":
            config = SLOT_CONFIG
            max_values = 64
        elif emoji == "🏀":
            config = BASKETBALL_CONFIG  
            max_values = 5
        else:  # ⚽
            config = FOOTBALL_CONFIG
            max_values = 5
        
        # СООБЩЕНИЕ О РЕЗУЛЬТАТЕ
        if value in config["values"]:
            result_config = config["values"][value]
            result_text = f"{result_config['message']}\n🔢 Номер значения: {value}/{max_values}"
            
            if result_config["win"]:
                result_text += "\n🎉 **ВЫИГРЫШНАЯ КОМБИНАЦИЯ!**"
            else:
                result_text += "\n💸 Проигрышная комбинация"
        else:
            result_text = f"{emoji} АНИМАЦИЯ #{value} - НОВАЯ КОМБИНАЦИЯ!\n🔢 Номер значения: {value}/{max_values}"
        
        # ДОБАВЛЯЕМ СТАТИСТИКУ
        result_text += f"\n\n📊 Статистика этой анимации:"
        result_text += f"\n{emoji} Выпадала раз: {game_data[value]['count']}"
        result_text += f"\n👥 Уникальных тестеров: {len(game_data[value]['users'])}"
        result_text += f"\n📈 Всего найдено: {len(game_data)}/{max_values}"
        
        await message.reply_text(result_text)
    
    context.user_data.pop('expecting_dice', None)
    context.user_data.pop('last_game_emoji', None)
    context.user_data.pop('last_dice_message_id', None)
    context.user_data.pop('last_game_user_id', None)

# 🌐 FLASK ДЛЯ RAILWAY
app = Flask(__name__)

@app.route('/')
def home():
    return "🎯 Research Bot - Исследуем анимации 🎰, 🏀 и ⚽!"

@app.route('/research')
def research_web():
    """Веб-страница с исследованием"""
    html = "<h1>🎯 Исследование анимаций 🎰, 🏀 и ⚽</h1>"
    
    # Баскетбол
    html += "<h2>🏀 Баскетбол</h2>"
    basketball_data = research_data["🏀"]
    if basketball_data:
        html += f"<p>Найдено значений: {len(basketball_data)}/5</p>"
        html += "<table border='1'><tr><th>Значение</th><th>Результат</th><th>Количество</th><th>Тестеров</th></tr>"
        for value in sorted(basketball_data.keys()):
            data = basketball_data[value]
            config = BASKETBALL_CONFIG["values"][value]
            result = "ВЫИГРЫШ" if config["win"] else "ПРОИГРЫШ"
            html += f"<tr><td>{value}</td><td>{result}</td><td>{data['count']}</td><td>{len(data['users'])}</td></tr>"
        html += "</table>"
    else:
        html += "<p>Данных пока нет</p>"
    
    # Футбол
    html += "<h2>⚽ Футбол</h2>"
    football_data = research_data["⚽"]
    if football_data:
        html += f"<p>Найдено значений: {len(football_data)}/5</p>"
        html += "<table border='1'><tr><th>Значение</th><th>Результат</th><th>Количество</th><th>Тестеров</th></tr>"
        for value in sorted(football_data.keys()):
            data = football_data[value]
            config = FOOTBALL_CONFIG["values"][value]
            result = "ВЫИГРЫШ" if config["win"] else "ПРОИГРЫШ"
            html += f"<tr><td>{value}</td><td>{result}</td><td>{data['count']}</td><td>{len(data['users'])}</td></tr>"
        html += "</table>"
    else:
        html += "<p>Данных пока нет</p>"
    
    return html

# 🚀 ЗАПУСК БОТА
def main():
    port = int(os.environ.get("PORT", 5000))
    
    def run_flask():
        app.run(host='0.0.0.0', port=port)
    
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # КОМАНДЫ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test_all", test_all))
    application.add_handler(CommandHandler("research", research_command))
    
    # СООБЩЕНИЯ
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(🎰|🏀|⚽)$"), handle_game_message))
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice_result))
    
    print("🎯 Research Bot запущен!")
    print("🔬 Исследуем анимации 🎰, 🏀 и ⚽!")
    print("📊 Команды: /start, /test_all, /research")
    application.run_polling()

if __name__ == '__main__':
    main()
