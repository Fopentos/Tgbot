import os
import json
import random
import datetime
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from threading import Thread
from flask import Flask

# 🔧 КОНФИГУРАЦИЯ
BOT_TOKEN = "8378526693:AAFOwAb6pVp1GOE0tXZN4PDLFnD_TTT1djg"

# 🎯 НАСТРОЙКИ ИГР
BASKETBALL_VALUES = 5  # Предполагаемое количество анимаций баскетбола
FOOTBALL_VALUES = 5    # Предполагаемое количество анимаций футбола

# 🏀 УНИКАЛЬНЫЕ СООБЩЕНИЯ ДЛЯ КАЖДОЙ АНИМАЦИИ БАСКЕТБОЛА
BASKETBALL_MESSAGES = {
    1: "🏀 АНИМАЦИЯ #1 - КРАСИВОЕ ПОПАДАНИЕ!",
    2: "🏀 АНИМАЦИЯ #2 - ИДЕАЛЬНЫЙ БРОСОК!",
    3: "🏀 АНИМАЦИЯ #3 - ТРЕХОЧКОВЫЙ!",
    4: "🏀 АНИМАЦИЯ #4 - СЛЭМ-ДАНК!",
    5: "🏀 АНИМАЦИЯ #5 - КОРОТКИЙ БРОСОК!"
}

# ⚽ УНИКАЛЬНЫЕ СООБЩЕНИЯ ДЛЯ КАЖДОЙ АНИМАЦИИ ФУТБОЛА
FOOTBALL_MESSAGES = {
    1: "⚽ АНИМАЦИЯ #1 - КРАСИВЫЙ УДАР!",
    2: "⚽ АНИМАЦИЯ #2 - ИДЕАЛЬНЫЙ ГОЛ!",
    3: "⚽ АНИМАЦИЯ #3 - СИЛЬНЫЙ УДАР!",
    4: "⚽ АНИМАЦИЯ #4 - ПЕНАЛЬТИ!",
    5: "⚽ АНИМАЦИЯ #5 - КОРОТКИЙ УДАР!"
}

# 🗃️ БАЗА ДАННЫХ ДЛЯ ИССЛЕДОВАНИЯ
basketball_research_data = {}
football_research_data = {}
user_data = defaultdict(lambda: {
    'total_games': 0,
})

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 РЕЖИМ ИССЛЕДОВАНИЯ АНИМАЦИЙ\n\n"
        "Исследуем анимации баскетбола 🏀 и футбола ⚽!\n\n"
        "Команды:\n"
        "/research - Показать все найденные значения\n"
        "/basketball X - Информация о анимации баскетбола\n"
        "/football X - Информация о анимации футбола\n"
        "/test_all - Начать тестирование всех игр\n\n"
        "Отправь 🏀 или ⚽ чтобы определить номер анимации!"
    )

async def test_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск тестирования всех игр"""
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        "🎯 ТЕСТИРОВАНИЕ ВСЕХ ИГР АКТИВИРОВАНО\n\n"
        "Отправляй 🏀 или ⚽ в чат - я буду показывать номер каждой анимации!\n\n"
        f"🏀 Баскетбол: {BASKETBALL_VALUES} предполагаемых анимаций\n"
        f"⚽ Футбол: {FOOTBALL_VALUES} предполагаемых анимаций\n\n"
        "После теста используй /research для просмотра статистики."
    )

async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать результаты исследования всех игр"""
    research_text = "📊 РЕЗУЛЬТАТЫ ИССЛЕДОВАНИЯ ВСЕХ ИГР\n\n"
    
    # Баскетбол
    research_text += "🏀 БАСКЕТБОЛ:\n"
    if basketball_research_data:
        research_text += f"📊 Найдено: {len(basketball_research_data)}/{BASKETBALL_VALUES} значений\n"
        for value in sorted(basketball_research_data.keys()):
            data = basketball_research_data[value]
            research_text += f"🏀 #{value}: {data['count']} раз\n"
    else:
        research_text += "❓ Данных пока нет\n"
    
    research_text += "\n⚽ ФУТБОЛ:\n"
    if football_research_data:
        research_text += f"📊 Найдено: {len(football_research_data)}/{FOOTBALL_VALUES} значений\n"
        for value in sorted(football_research_data.keys()):
            data = football_research_data[value]
            research_text += f"⚽ #{value}: {data['count']} раз\n"
    else:
        research_text += "❓ Данных пока нет\n"
    
    await update.message.reply_text(research_text)

async def basketball_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о конкретной анимации баскетбола"""
    if not context.args:
        await update.message.reply_text("Использование: /basketball <номер>")
        return
    
    try:
        anim_number = int(context.args[0])
        if anim_number in basketball_research_data:
            data = basketball_research_data[anim_number]
            info_text = f"🏀 ИНФОРМАЦИЯ О АНИМАЦИИ #{anim_number}\n\n"
            info_text += f"📊 Выпадала раз: {data['count']}\n"
            info_text += f"👥 Тестеров: {len(data['users'])}\n"
            info_text += f"📅 Первый раз: {data['first_seen'][:19]}\n"
            info_text += f"🎯 Сообщение: {BASKETBALL_MESSAGES.get(anim_number, 'НЕИЗВЕСТНО')}\n"
        else:
            info_text = f"🏀 Анимация #{anim_number} еще не найдена!\nПродолжай тестировать 🏀"
            
        await update.message.reply_text(info_text)
        
    except ValueError:
        await update.message.reply_text("Номер должен быть числом")

async def football_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о конкретной анимации футбола"""
    if not context.args:
        await update.message.reply_text("Использование: /football <номер>")
        return
    
    try:
        anim_number = int(context.args[0])
        if anim_number in football_research_data:
            data = football_research_data[anim_number]
            info_text = f"⚽ ИНФОРМАЦИЯ О АНИМАЦИИ #{anim_number}\n\n"
            info_text += f"📊 Выпадала раз: {data['count']}\n"
            info_text += f"👥 Тестеров: {len(data['users'])}\n"
            info_text += f"📅 Первый раз: {data['first_seen'][:19]}\n"
            info_text += f"🎯 Сообщение: {FOOTBALL_MESSAGES.get(anim_number, 'НЕИЗВЕСТНО')}\n"
        else:
            info_text = f"⚽ Анимация #{anim_number} еще не найдена!\nПродолжай тестировать ⚽"
            
        await update.message.reply_text(info_text)
        
    except ValueError:
        await update.message.reply_text("Номер должен быть числом")

def generate_basketball_message(value):
    """Генерирует уникальное сообщение для каждого значения баскетбола"""
    if value in BASKETBALL_MESSAGES:
        message = BASKETBALL_MESSAGES[value]
    else:
        message = f"🏀 АНИМАЦИЯ #{value} - НОВАЯ КОМБИНАЦИЯ!"
    
    return f"{message}\n🔢 Номер значения: {value}"

def generate_football_message(value):
    """Генерирует уникальное сообщение для каждого значения футбола"""
    if value in FOOTBALL_MESSAGES:
        message = FOOTBALL_MESSAGES[value]
    else:
        message = f"⚽ АНИМАЦИЯ #{value} - НОВАЯ КОМБИНАЦИЯ!"
    
    return f"{message}\n🔢 Номер значения: {value}"

# 🎮 СИСТЕМА ИГР - ТЕСТОВЫЙ РЕЖИМ ДЛЯ ВСЕХ ИГР
async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    emoji = update.message.text
    
    if emoji not in ["🏀", "⚽"]:
        await update.message.reply_text("🎯 В этом режиме работают только 🏀 и ⚽!")
        return
    
    user_data[user_id]['total_games'] += 1
    
    context.user_data['expecting_dice'] = True
    context.user_data['last_game_type'] = 'basketball' if emoji == "🏀" else 'football'
    context.user_data['last_game_user_id'] = user_id
    
    dice_message = await context.bot.send_dice(chat_id=update.message.chat_id, emoji=emoji)
    context.user_data['last_dice_message_id'] = dice_message.message_id
    
    game_name = "БАСКЕТБОЛ" if emoji == "🏀" else "ФУТБОЛ"
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
    
    if emoji == "🏀":
        # СОХРАНЯЕМ ДАННЫЕ ИССЛЕДОВАНИЯ ДЛЯ БАСКЕТБОЛА
        if value not in basketball_research_data:
            basketball_research_data[value] = {
                'first_seen': datetime.datetime.now().isoformat(),
                'count': 0,
                'users': set()
            }
        
        basketball_research_data[value]['count'] += 1
        basketball_research_data[value]['users'].add(user_id)
        
        # УНИКАЛЬНОЕ СООБЩЕНИЕ ДЛЯ КАЖДОГО ЗНАЧЕНИЯ
        result_text = generate_basketball_message(value)
        
        # ДОБАВЛЯЕМ СТАТИСТИКУ
        result_text += f"\n\n📊 Статистика этой анимации:"
        result_text += f"\n🏀 Выпадала раз: {basketball_research_data[value]['count']}"
        result_text += f"\n👥 Уникальных тестеров: {len(basketball_research_data[value]['users'])}"
        result_text += f"\n📈 Всего найдено: {len(basketball_research_data)}/{BASKETBALL_VALUES}"
        
        # ССЫЛКА НА КОМАНДУ ДЛЯ ПРОСМОТРА
        result_text += f"\n\n💡 Подробнее: /basketball {value}"
        
        await message.reply_text(result_text)
    
    elif emoji == "⚽":
        # СОХРАНЯЕМ ДАННЫЕ ИССЛЕДОВАНИЯ ДЛЯ ФУТБОЛА
        if value not in football_research_data:
            football_research_data[value] = {
                'first_seen': datetime.datetime.now().isoformat(),
                'count': 0,
                'users': set()
            }
        
        football_research_data[value]['count'] += 1
        football_research_data[value]['users'].add(user_id)
        
        # УНИКАЛЬНОЕ СООБЩЕНИЕ ДЛЯ КАЖДОГО ЗНАЧЕНИЯ
        result_text = generate_football_message(value)
        
        # ДОБАВЛЯЕМ СТАТИСТИКУ
        result_text += f"\n\n📊 Статистика этой анимации:"
        result_text += f"\n⚽ Выпадала раз: {football_research_data[value]['count']}"
        result_text += f"\n👥 Уникальных тестеров: {len(football_research_data[value]['users'])}"
        result_text += f"\n📈 Всего найдено: {len(football_research_data)}/{FOOTBALL_VALUES}"
        
        # ССЫЛКА НА КОМАНДУ ДЛЯ ПРОСМОТРА
        result_text += f"\n\n💡 Подробнее: /football {value}"
        
        await message.reply_text(result_text)
    
    context.user_data.pop('expecting_dice', None)
    context.user_data.pop('last_game_type', None)
    context.user_data.pop('last_dice_message_id', None)
    context.user_data.pop('last_game_user_id', None)

# 🌐 FLASK ДЛЯ RAILWAY
app = Flask(__name__)

@app.route('/')
def home():
    return "🎯 Research Bot - Исследуем анимации 🏀 и ⚽!"

@app.route('/research')
def research_web():
    """Веб-страница с исследованием"""
    html = "<h1>🎯 Исследование анимаций 🏀 и ⚽</h1>"
    
    # Баскетбол
    html += "<h2>🏀 Баскетбол</h2>"
    if basketball_research_data:
        html += f"<p>Найдено значений: {len(basketball_research_data)}/{BASKETBALL_VALUES}</p>"
        html += "<table border='1'><tr><th>Значение</th><th>Сообщение</th><th>Количество</th><th>Тестеров</th></tr>"
        for value in sorted(basketball_research_data.keys()):
            data = basketball_research_data[value]
            message = BASKETBALL_MESSAGES.get(value, "НОВАЯ КОМБИНАЦИЯ")
            html += f"<tr><td>{value}</td><td>{message}</td><td>{data['count']}</td><td>{len(data['users'])}</td></tr>"
        html += "</table>"
    else:
        html += "<p>Данных пока нет</p>"
    
    # Футбол
    html += "<h2>⚽ Футбол</h2>"
    if football_research_data:
        html += f"<p>Найдено значений: {len(football_research_data)}/{FOOTBALL_VALUES}</p>"
        html += "<table border='1'><tr><th>Значение</th><th>Сообщение</th><th>Количество</th><th>Тестеров</th></tr>"
        for value in sorted(football_research_data.keys()):
            data = football_research_data[value]
            message = FOOTBALL_MESSAGES.get(value, "НОВАЯ КОМБИНАЦИЯ")
            html += f"<tr><td>{value}</td><td>{message}</td><td>{data['count']}</td><td>{len(data['users'])}</td></tr>"
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
    application.add_handler(CommandHandler("basketball", basketball_info_command))
    application.add_handler(CommandHandler("football", football_info_command))
    
    # СООБЩЕНИЯ
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(🏀|⚽)$"), handle_game_message))
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice_result))
    
    print("🎯 Research Bot запущен!")
    print("🔬 Исследуем анимации 🏀 и ⚽!")
    print("📊 Команды: /start, /test_all, /research, /basketball, /football")
    application.run_polling()

if __name__ == '__main__':
    main()
