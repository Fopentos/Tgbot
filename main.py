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

# 🎮 КОНФИГУРАЦИЯ ИССЛЕДОВАНИЯ ВСЕХ ИГР
GAMES_RESEARCH = {
    "🎯": {
        "name": "Дартс",
        "values_range": 6,
        "research_data": {},
        "messages": {
            1: "🎯 АНИМАЦИЯ #1 - Мимо мишени!",
            2: "🎯 АНИМАЦИЯ #2 - Попадание в край!",
            3: "🎯 АНИМАЦИЯ #3 - Близко к центру!",
            4: "🎯 АНИМАЦИЯ #4 - Хороший бросок!",
            5: "🎯 АНИМАЦИЯ #5 - Почти в яблочко!",
            6: "🎯 АНИМАЦИЯ #6 - ПОПАДАНИЕ В ЦЕЛЬ!"
        }
    },
    "🎲": {
        "name": "Кости", 
        "values_range": 6,
        "research_data": {},
        "messages": {
            1: "🎲 АНИМАЦИЯ #1 - Выпала 1!",
            2: "🎲 АНИМАЦИЯ #2 - Выпала 2!",
            3: "🎲 АНИМАЦИЯ #3 - Выпала 3!",
            4: "🎲 АНИМАЦИЯ #4 - Выпала 4!",
            5: "🎲 АНИМАЦИЯ #5 - Выпала 5!",
            6: "🎲 АНИМАЦИЯ #6 - Выпала 6!"
        }
    },
    "🎳": {
        "name": "Боулинг",
        "values_range": 6,
        "research_data": {},
        "messages": {
            1: "🎳 АНИМАЦИЯ #1 - 1 кегля!",
            2: "🎳 АНИМАЦИЯ #2 - 2 кегли!",
            3: "🎳 АНИМАЦИЯ #3 - 3 кегли!",
            4: "🎳 АНИМАЦИЯ #4 - 4 кегли!",
            5: "🎳 АНИМАЦИЯ #5 - 5 кеглей!",
            6: "🎳 АНИМАЦИЯ #6 - СТРАЙК!"
        }
    },
    "⚽": {
        "name": "Футбол",
        "values_range": 5,
        "research_data": {},
        "messages": {
            1: "⚽ АНИМАЦИЯ #1 - Мяч в аут!",
            2: "⚽ АНИМАЦИЯ #2 - Удар по штанге!",
            3: "⚽ АНИМАЦИЯ #3 - Блок защитника!",
            4: "⚽ АНИМАЦИЯ #4 - Сейв вратаря!",
            5: "⚽ АНИМАЦИЯ #5 - ГОООЛ!"
        }
    },
    "🏀": {
        "name": "Баскетбол",
        "values_range": 5, 
        "research_data": {},
        "messages": {
            1: "🏀 АНИМАЦИЯ #1 - Промах!",
            2: "🏀 АНИМАЦИЯ #2 - Задел обод!",
            3: "🏀 АНИМАЦИЯ #3 - Колебался и вылетел!",
            4: "🏀 АНИМАЦИЯ #4 - Почти попал!",
            5: "🏀 АНИМАЦИЯ #5 - ПОПАДАНИЕ!"
        }
    }
}

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 РЕЖИМ ИССЛЕДОВАНИЯ ВСЕХ ИГР\n\n"
        "Просто отправь эмодзи игры в чат:\n"
        "🎯 Дартс (6 значений)\n"
        "🎲 Кости (6 значений)\n" 
        "🎳 Боулинг (6 значений)\n"
        "⚽ Футбол (5 значений)\n"
        "🏀 Баскетбол (5 значений)\n\n"
        "Команды:\n"
        "/research - Показать все найденные значения\n"
        "/game_stats - Статистика по играм\n"
        "/test_all - Начать тестирование всех игр\n\n"
        "Бот определит номер каждой анимации!"
    )

async def test_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск тестирования всех игр"""
    await update.message.reply_text(
        "🎮 ТЕСТИРОВАНИЕ ВСЕХ ИГР АКТИВИРОВАНО\n\n"
        "Отправляй эмодзи игр в чат:\n"
        "🎯 Дартс - 6 возможных значений\n"
        "🎲 Кости - 6 возможных значений\n"
        "🎳 Боулинг - 6 возможных значений\n"
        "⚽ Футбол - 5 возможных значений\n"
        "🏀 Баскетбол - 5 возможных значений\n\n"
        "После теста используй /research для просмотра статистики."
    )

async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать результаты исследования всех игр"""
    research_text = "🎮 РЕЗУЛЬТАТЫ ИССЛЕДОВАНИЯ ВСЕХ ИГР\n\n"
    
    for emoji, game_data in GAMES_RESEARCH.items():
        research_data = game_data["research_data"]
        found_count = len(research_data)
        total_count = game_data["values_range"]
        
        research_text += f"{emoji} {game_data['name']}: {found_count}/{total_count} значений\n"
        
        # Показываем найденные значения
        if research_data:
            values_line = ""
            for value in range(1, total_count + 1):
                if value in research_data:
                    count = research_data[value]['count']
                    values_line += f"{value}({count}) "
                else:
                    values_line += f"❓{value} "
            research_text += values_line + "\n\n"
        else:
            research_text += "❓ Еще не найдено\n\n"
    
    await update.message.reply_text(research_text)

async def game_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальная статистика по играм"""
    stats_text = "📊 ДЕТАЛЬНАЯ СТАТИСТИКА ПО ИГРАМ\n\n"
    
    for emoji, game_data in GAMES_RESEARCH.items():
        research_data = game_data["research_data"]
        found_count = len(research_data)
        total_count = game_data["values_range"]
        
        stats_text += f"{emoji} {game_data['name']}:\n"
        stats_text += f"📈 Найдено: {found_count}/{total_count}\n"
        
        if research_data:
            # Общее количество бросков
            total_throws = sum(data['count'] for data in research_data.values())
            # Количество уникальных тестеров
            all_users = set()
            for data in research_data.values():
                all_users.update(data['users'])
            
            stats_text += f"🎮 Всего бросков: {total_throws}\n"
            stats_text += f"👥 Уникальных тестеров: {len(all_users)}\n"
            
            # Самые частые значения
            if research_data:
                most_common = max(research_data.items(), key=lambda x: x[1]['count'])
                stats_text += f"🏆 Чаще всего: #{most_common[0]} ({most_common[1]['count']} раз)\n"
        else:
            stats_text += "📊 Данных пока нет\n"
        
        stats_text += "\n"
    
    await update.message.reply_text(stats_text)

async def game_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о конкретной игре"""
    if not context.args:
        await update.message.reply_text(
            "Использование: /game_info <эмодзи>\n\n"
            "Примеры:\n"
            "/game_info 🎯 - информация о дартсе\n"
            "/game_info 🎲 - информация о костях\n"
            "/game_info 🎳 - информация о боулинге\n" 
            "/game_info ⚽ - информация о футболе\n"
            "/game_info 🏀 - информация о баскетболе"
        )
        return
    
    emoji = context.args[0]
    if emoji not in GAMES_RESEARCH:
        await update.message.reply_text("❌ Неизвестная игра! Используй: 🎯, 🎲, 🎳, ⚽, 🏀")
        return
    
    game_data = GAMES_RESEARCH[emoji]
    research_data = game_data["research_data"]
    
    info_text = f"{emoji} ИНФОРМАЦИЯ О {game_data['name'].upper()}\n\n"
    info_text += f"🎯 Всего значений: {game_data['values_range']}\n"
    info_text += f"📊 Найдено: {len(research_data)}/{game_data['values_range']}\n\n"
    
    if research_data:
        info_text += "📈 НАЙДЕННЫЕ ЗНАЧЕНИЯ:\n"
        for value in sorted(research_data.keys()):
            data = research_data[value]
            info_text += f"#{value}: {data['count']} раз, {len(data['users'])} тестеров\n"
    else:
        info_text += "❓ Значения еще не найдены\n"
    
    info_text += f"\n💡 Отправь {emoji} в чат для тестирования!"
    
    await update.message.reply_text(info_text)

def generate_game_message(emoji, value):
    """Генерирует уникальное сообщение для каждого значения игры"""
    game_data = GAMES_RESEARCH[emoji]
    
    if value in game_data["messages"]:
        message = game_data["messages"][value]
    else:
        message = f"{emoji} АНИМАЦИЯ #{value} - УНИКАЛЬНАЯ КОМБИНАЦИЯ!"
    
    return f"{message}\n🔢 Номер значения: {value}/{game_data['values_range']}"

# 🎮 ОБРАБОТКА DICE - ДЛЯ ВСЕХ ИГР
async def handle_dice_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if not message.dice:
        return
    
    emoji = message.dice.emoji
    value = message.dice.value
    
    # Проверяем, что это одна из исследуемых игр
    if emoji not in GAMES_RESEARCH:
        return
    
    game_data = GAMES_RESEARCH[emoji]
    research_data = game_data["research_data"]
    
    # СОХРАНЯЕМ ДАННЫЕ ИССЛЕДОВАНИЯ
    if value not in research_data:
        research_data[value] = {
            'first_seen': datetime.datetime.now().isoformat(),
            'count': 0,
            'users': set()
        }
    
    research_data[value]['count'] += 1
    research_data[value]['users'].add(user_id)
    
    # УНИКАЛЬНОЕ СООБЩЕНИЕ ДЛЯ КАЖДОГО ЗНАЧЕНИЯ
    result_text = generate_game_message(emoji, value)
    
    # ДОБАВЛЯЕМ СТАТИСТИКУ
    result_text += f"\n\n📊 Статистика этого значения:"
    result_text += f"\n{emoji} Выпадало раз: {research_data[value]['count']}"
    result_text += f"\n👥 Уникальных тестеров: {len(research_data[value]['users'])}"
    result_text += f"\n📈 Всего найдено: {len(research_data)}/{game_data['values_range']}"
    
    # ССЫЛКА НА КОМАНДУ ДЛЯ ПРОСМОТРА
    result_text += f"\n\n💡 Подробнее: /game_info {emoji}"
    
    await message.reply_text(result_text)

# 🔄 ОБРАБОТЧИКИ КНОПОК
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    callback_data = query.data
    
    if callback_data == 'test_all':
        await query.answer()
        await query.edit_message_text(
            "🎮 РЕЖИМ ТЕСТИРОВАНИЯ ВСЕХ ИГР АКТИВИРОВАН\n\n"
            "Отправляй эмодзи игр в чат:\n"
            "🎯 Дартс - 6 значений\n"
            "🎲 Кости - 6 значений\n"
            "🎳 Боулинг - 6 значений\n"
            "⚽ Футбол - 5 значений\n"
            "🏀 Баскетбол - 5 значений\n\n"
            "Я покажу номер каждой анимации!"
        )

# 🌐 FLASK ДЛЯ RAILWAY
app = Flask(__name__)

@app.route('/')
def home():
    return "🎮 Games Research Bot - Определяем номера анимаций всех игр!"

@app.route('/research')
def research_web():
    """Веб-страница с исследованием всех игр"""
    html = "<h1>🎮 Исследование всех игр</h1>"
    
    for emoji, game_data in GAMES_RESEARCH.items():
        research_data = game_data["research_data"]
        found_count = len(research_data)
        total_count = game_data["values_range"]
        
        html += f"<h2>{emoji} {game_data['name']} - {found_count}/{total_count}</h2>"
        
        if research_data:
            html += "<table border='1'><tr><th>Значение</th><th>Сообщение</th><th>Количество</th><th>Тестеров</th></tr>"
            
            for value in sorted(research_data.keys()):
                data = research_data[value]
                message = game_data["messages"].get(value, "УНИКАЛЬНАЯ КОМБИНАЦИЯ")
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
    application.add_handler(CommandHandler("game_stats", game_stats_command))
    application.add_handler(CommandHandler("game_info", game_info_command))
    
    # CALLBACK'И
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # СООБЩЕНИЯ - ОБРАБАТЫВАЕМ DICE (анимации)
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice_result))
    
    print("🎮 Games Research Bot запущен!")
    print("🔬 Бот будет реагировать на анимации: 🎯 🎲 🎳 ⚽ 🏀")
    application.run_polling()

if __name__ == '__main__':
    main()
