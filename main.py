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
GAME_COST = 0  # Бесплатно для тестирования

# 🎰 ТЕСТОВЫЙ РЕЖИМ - МЫ ХОТИМ УЗНАТЬ ВСЕ ЗНАЧЕНИЯ
SLOT_VALUES_RESEARCH = {}

# 🗃️ БАЗА ДАННЫХ
user_data = defaultdict(lambda: {
    'game_balance': 1000,  # Много звезд для тестирования
    'total_games': 0,
    'total_wins': 0,
})

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔬 РЕЖИМ ТЕСТИРОВАНИЯ СЛОТОВ\n\n"
        "🎯 Цель: определить все 64 значения слотов\n\n"
        "Команды:\n"
        "/test_slots - Протестировать слоты\n"
        "/research - Показать собранные данные\n"
        "/reset_research - Сбросить исследование\n\n"
        "Просто отправь 🎰 чтобы начать тест!"
    )

async def test_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск тестирования слотов"""
    user_id = update.effective_user.id
    
    # Даем бесплатные звезды для тестирования
    user_data[user_id]['game_balance'] = 1000
    
    await update.message.reply_text(
        "🎰 ЗАПУСК ТЕСТИРОВАНИЯ СЛОТОВ\n\n"
        "💰 Баланс: 1000 звезд (бесплатно)\n"
        "🎯 Играй в слоты и я буду записывать все значения\n"
        "📊 Используй /research чтобы посмотреть прогресс\n\n"
        "Отправь 🎰 чтобы начать!"
    )

async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать результаты исследования"""
    user_id = update.effective_user.id
    
    if not SLOT_VALUES_RESEARCH:
        await update.message.reply_text("📊 Исследование пусто. Сыграй в слоты чтобы собрать данные!")
        return
    
    research_text = "🔬 РЕЗУЛЬТАТЫ ИССЛЕДОВАНИЯ СЛОТОВ\n\n"
    research_text += f"📈 Найдено значений: {len(SLOT_VALUES_RESEARCH)}/64\n\n"
    
    # Группируем значения по диапазонам для удобства
    for i in range(0, 64, 8):
        range_values = []
        for j in range(i+1, i+9):
            if j in SLOT_VALUES_RESEARCH:
                range_values.append(f"🎰{j}")
            else:
                range_values.append(f"❓{j}")
        
        research_text += f"{i+1:02d}-{i+8:02d}: {' '.join(range_values)}\n"
    
    research_text += f"\n📋 Все найденные значения: {sorted(SLOT_VALUES_RESEARCH.keys())}"
    
    await update.message.reply_text(research_text)

async def reset_research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбросить исследование"""
    SLOT_VALUES_RESEARCH.clear()
    await update.message.reply_text("🔄 Исследование сброшено! Начинаем заново.")

# 🎮 СИСТЕМА ИГР - ТЕСТОВЫЙ РЕЖИМ
async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    emoji = update.message.text
    
    if emoji != "🎰":
        await update.message.reply_text("🔬 В режиме тестирования работают только слоты (🎰)")
        return
    
    user_data[user_id]['total_games'] += 1
    
    context.user_data['expecting_dice'] = True
    context.user_data['last_game_type'] = 'slots'
    context.user_data['last_game_user_id'] = user_id
    
    dice_message = await context.bot.send_dice(chat_id=update.message.chat_id, emoji=emoji)
    context.user_data['last_dice_message_id'] = dice_message.message_id
    
    await update.message.reply_text(
        f"🔬 Тестовый бросок #{user_data[user_id]['total_games']}\n"
        f"💸 Списано: 0 звезд (тестовый режим)\n"
        f"💰 Баланс: {user_data[user_id]['game_balance']} звезд"
    )

# 🎰 ОБРАБОТКА DICE - ИССЛЕДОВАТЕЛЬСКИЙ РЕЖИМ
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
    
    if emoji == "🎰":
        # ЗАПИСЫВАЕМ ЗНАЧЕНИЕ В БАЗУ ДАННЫХ ИССЛЕДОВАНИЯ
        if value not in SLOT_VALUES_RESEARCH:
            SLOT_VALUES_RESEARCH[value] = {
                'first_seen': datetime.datetime.now().isoformat(),
                'count': 0,
                'users': set()
            }
        
        SLOT_VALUES_RESEARCH[value]['count'] += 1
        SLOT_VALUES_RESEARCH[value]['users'].add(user_id)
        
        # ФОРМИРУЕМ ДЕТАЛЬНЫЙ ОТЧЕТ
        result_text = f"🎰 ТЕСТОВЫЙ РЕЗУЛЬТАТ\n\n"
        result_text += f"🔢 Выпавшее значение: {value}\n"
        result_text += f"📊 Всего таких значений: {SLOT_VALUES_RESEARCH[value]['count']}\n"
        result_text += f"👥 Уникальных тестеров: {len(SLOT_VALUES_RESEARCH[value]['users'])}\n"
        result_text += f"📈 Прогресс: {len(SLOT_VALUES_RESEARCH)}/64 значений\n\n"
        
        # АНАЛИЗ КОМБИНАЦИИ
        if value <= 16:
            combo_type = "ВЫСОКОЕ (1-16)"
        elif value <= 32:
            combo_type = "СРЕДНЕЕ (17-32)" 
        elif value <= 48:
            combo_type = "НИЗКОЕ (33-48)"
        else:
            combo_type = "ОЧЕНЬ НИЗКОЕ (49-64)"
        
        result_text += f"🎯 Диапазон: {combo_type}\n"
        
        # ПРЕДПОЛОЖЕНИЕ О ВЫИГРЫШЕ
        if value in [1, 17, 33, 49]:
            result_text += "💎 Возможный ДЖЕКПОТ (крайние значения диапазонов)\n"
        elif value % 8 == 0:
            result_text += "🔥 Возможный большой выигрыш (кратные 8)\n"
        elif value % 4 == 0:
            result_text += "⭐ Возможный средний выигрыш (кратные 4)\n"
        else:
            result_text += "🎪 Обычная комбинация\n"
        
        result_text += f"\n💡 Используй /research для полной статистики"
        
        await message.reply_text(result_text)
    
    context.user_data.pop('expecting_dice', None)
    context.user_data.pop('last_game_type', None)
    context.user_data.pop('last_dice_message_id', None)
    context.user_data.pop('last_game_user_id', None)

# 🔄 ОБРАБОТЧИКИ КНОПОК
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    callback_data = query.data
    
    if callback_data == 'test_slots':
        user_id = query.from_user.id
        user_data[user_id]['game_balance'] = 1000
        
        await query.edit_message_text(
            "🎰 РЕЖИМ ТЕСТИРОВАНИЯ АКТИВИРОВАН\n\n"
            "Отправь 🎰 в чат чтобы сделать тестовый бросок!\n\n"
            "Команды:\n"
            "/research - Статистика\n"
            "/reset_research - Сбросить"
        )

# 🌐 FLASK ДЛЯ RAILWAY
app = Flask(__name__)

@app.route('/')
def home():
    return "🔬 Slot Research Bot is running!"

@app.route('/research')
def research_web():
    """Веб-страница с исследованием"""
    if not SLOT_VALUES_RESEARCH:
        return "Исследование пусто"
    
    html = "<h1>🔬 Исследование Слотов</h1>"
    html += f"<p>Найдено значений: {len(SLOT_VALUES_RESEARCH)}/64</p>"
    html += "<table border='1'><tr><th>Значение</th><th>Количество</th><th>Тестеров</th></tr>"
    
    for value, data in sorted(SLOT_VALUES_RESEARCH.items()):
        html += f"<tr><td>{value}</td><td>{data['count']}</td><td>{len(data['users'])}</td></tr>"
    
    html += "</table>"
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
    application.add_handler(CommandHandler("test_slots", test_slots))
    application.add_handler(CommandHandler("research", research_command))
    application.add_handler(CommandHandler("reset_research", reset_research))
    
    # CALLBACK'И
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # СООБЩЕНИЯ
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(🎰)$"), handle_game_message))
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice_result))
    
    print("🔬 Slot Research Bot запущен на Railway!")
    application.run_polling()

if __name__ == '__main__':
    main()
