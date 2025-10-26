import os
import datetime
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from threading import Thread
from flask import Flask

# 🔧 КОНФИГУРАЦИЯ
BOT_TOKEN = "8378526693:AAFOwAb6pVp1GOE0tXZN4PDLFnD_TTT1djg"

# 🗃️ БАЗА ДАННЫХ ДЛЯ ИССЛЕДОВАНИЯ
research_data = {
    "🏀": defaultdict(lambda: {'count': 0, 'users': set(), 'first_seen': None}),
    "⚽": defaultdict(lambda: {'count': 0, 'users': set(), 'first_seen': None})
}

user_stats = defaultdict(lambda: {'total_games': 0})
active_sessions = {}

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 РЕЖИМ ИССЛЕДОВАНИЯ АНИМАЦИЙ\n\n"
        "Просто отправь 🏀 или ⚽ в чат!\n"
        "Я покажу номер анимации и статистику.\n\n"
        "Команды:\n"
        "/stats - Показать статистику\n"
        "/clear - Очистить статистику\n\n"
        "Отправляй эмодзи и узнавай номера анимаций!"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику по всем анимациям"""
    stats_text = "📊 СТАТИСТИКА ИССЛЕДОВАНИЯ\n\n"
    
    # Баскетбол
    basketball_data = research_data["🏀"]
    if basketball_data:
        stats_text += "🏀 БАСКЕТБОЛ:\n"
        for value in sorted(basketball_data.keys()):
            data = basketball_data[value]
            stats_text += f"🔢 Анимация #{value}: {data['count']} раз\n"
        stats_text += f"📈 Всего анимаций: {len(basketball_data)}\n\n"
    else:
        stats_text += "🏀 Баскетбол: данных нет\n\n"
    
    # Футбол
    football_data = research_data["⚽"]
    if football_data:
        stats_text += "⚽ ФУТБОЛ:\n"
        for value in sorted(football_data.keys()):
            data = football_data[value]
            stats_text += f"🔢 Анимация #{value}: {data['count']} раз\n"
        stats_text += f"📈 Всего анимаций: {len(football_data)}\n"
    else:
        stats_text += "⚽ Футбол: данных нет\n"
    
    await update.message.reply_text(stats_text)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистить статистику"""
    research_data["🏀"].clear()
    research_data["⚽"].clear()
    user_stats.clear()
    active_sessions.clear()
    await update.message.reply_text("✅ Статистика очищена!")

# 🎮 ОБРАБОТКА ИГР
async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    emoji = update.message.text
    
    if emoji not in ["🏀", "⚽"]:
        await update.message.reply_text("❌ Отправь только 🏀 или ⚽!")
        return
    
    user_stats[user_id]['total_games'] += 1
    
    # Сохраняем информацию о текущей игре
    chat_id = update.message.chat_id
    active_sessions[chat_id] = {
        'emoji': emoji,
        'user_id': user_id,
        'waiting_for_dice': True
    }
    
    # Отправляем dice
    dice_message = await context.bot.send_dice(chat_id=chat_id, emoji=emoji)
    
    # Сохраняем ID dice сообщения для отслеживания
    active_sessions[chat_id]['dice_message_id'] = dice_message.message_id
    
    game_name = "БАСКЕТБОЛ" if emoji == "🏀" else "ФУТБОЛ"
    await update.message.reply_text(
        f"🎯 Бросок #{user_stats[user_id]['total_games']} ({game_name})\n"
        f"⏳ Определяю номер анимации..."
    )

# 📊 ОБРАБОТКА РЕЗУЛЬТАТОВ DICE
async def handle_dice_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    
    if not message.dice:
        return
    
    # Проверяем, есть ли активная сессия для этого чата
    if chat_id not in active_sessions:
        return
    
    session = active_sessions[chat_id]
    
    # Проверяем, что это то же самое dice сообщение, которое мы отправили
    if message.message_id != session.get('dice_message_id'):
        return
    
    emoji = message.dice.emoji
    value = message.dice.value
    
    if emoji in ["🏀", "⚽"]:
        # Обновляем статистику
        game_data = research_data[emoji]
        
        if game_data[value]['first_seen'] is None:
            game_data[value]['first_seen'] = datetime.datetime.now().isoformat()
        
        game_data[value]['count'] += 1
        game_data[value]['users'].add(session['user_id'])
        
        # Формируем сообщение с результатом
        game_name = "БАСКЕТБОЛ" if emoji == "🏀" else "ФУТБОЛ"
        
        result_text = (
            f"{emoji} {game_name} - АНИМАЦИЯ #{value}\n\n"
            f"📊 Статистика этой анимации:\n"
            f"🔄 Выпадала раз: {game_data[value]['count']}\n"
            f"👥 Уникальных тестеров: {len(game_data[value]['users'])}\n"
            f"📈 Всего найдено анимаций: {len(game_data)}"
        )
        
        await message.reply_text(result_text)
    
    # Очищаем сессию
    del active_sessions[chat_id]

# 🌐 FLASK ДЛЯ RAILWAY
app = Flask(__name__)

@app.route('/')
def home():
    return "🔍 Animation Research Bot - Исследуем анимации 🏀 и ⚽!"

@app.route('/stats')
def stats_web():
    """Веб-страница со статистикой"""
    html = "<h1>🔍 Статистика анимаций 🏀 и ⚽</h1>"
    
    # Баскетбол
    html += "<h2>🏀 Баскетбол</h2>"
    basketball_data = research_data["🏀"]
    if basketball_data:
        html += f"<p>Найдено анимаций: {len(basketball_data)}</p>"
        html += "<table border='1'><tr><th>Номер анимации</th><th>Количество</th><th>Тестеров</th><th>Первое появление</th></tr>"
        for value in sorted(basketball_data.keys()):
            data = basketball_data[value]
            first_seen = data['first_seen'][:19] if data['first_seen'] else "N/A"
            html += f"<tr><td>{value}</td><td>{data['count']}</td><td>{len(data['users'])}</td><td>{first_seen}</td></tr>"
        html += "</table>"
    else:
        html += "<p>Данных пока нет</p>"
    
    # Футбол
    html += "<h2>⚽ Футбол</h2>"
    football_data = research_data["⚽"]
    if football_data:
        html += f"<p>Найдено анимаций: {len(football_data)}</p>"
        html += "<table border='1'><tr><th>Номер анимации</th><th>Количество</th><th>Тестеров</th><th>Первое появление</th></tr>"
        for value in sorted(football_data.keys()):
            data = football_data[value]
            first_seen = data['first_seen'][:19] if data['first_seen'] else "N/A"
            html += f"<tr><td>{value}</td><td>{data['count']}</td><td>{len(data['users'])}</td><td>{first_seen}</td></tr>"
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
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("clear", clear_command))
    
    # СООБЩЕНИЯ
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(🏀|⚽)$"), handle_game_message))
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice_result))
    
    print("🔍 Animation Research Bot запущен!")
    print("🎯 Бот готов к исследованию анимаций 🏀 и ⚽!")
    print("📊 Команды: /start, /stats, /clear")
    application.run_polling()

if __name__ == '__main__':
    main()
