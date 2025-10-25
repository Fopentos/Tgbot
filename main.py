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

# 🎰 УНИКАЛЬНЫЕ СООБЩЕНИЯ ДЛЯ КАЖДОЙ АНИМАЦИИ
SLOT_MESSAGES = {
    1: "🎰 АНИМАЦИЯ #1 - ЗОЛОТЫЕ 777!",
    2: "🎰 АНИМАЦИЯ #2 - БЛЕСТЯЩИЕ БАРЫ!",
    3: "🎰 АНИМАЦИЯ #3 - ОГНЕННЫЕ ВИШНИ!",
    4: "🎰 АНИМАЦИЯ #4 - СИЯЮЩИЕ ЛИМОНЫ!",
    5: "🎰 АНИМАЦИЯ #5 - ЗВЕЗДНЫЕ СЕМЕРКИ!",
    6: "🎰 АНИМАЦИЯ #6 - МЕТАЛЛИЧЕСКИЕ БАРЫ!",
    7: "🎰 АНИМАЦИЯ #7 - РУБИНОВЫЕ ВИШНИ!",
    8: "🎰 АНИМАЦИЯ #8 - ЗОЛОТЫЕ ЛИМОНЫ!",
    9: "🎰 АНИМАЦИЯ #9 - КРИСТАЛЬНЫЕ 777!",
    10: "🎰 АНИМАЦИЯ #10 - НЕБЕСНЫЕ БАРЫ!",
    11: "🎰 АНИМАЦИЯ #11 - ИЗУМРУДНЫЕ ВИШНИ!",
    12: "🎰 АНИМАЦИЯ #12 - ЭЛЕКТРИЧЕСКИЕ ЛИМОНЫ!",
    13: "🎰 АНИМАЦИЯ #13 - ЛУННЫЕ СЕМЕРКИ!",
    14: "🎰 АНИМАЦИЯ #14 - ВУЛКАНИЧЕСКИЕ БАРЫ!",
    15: "🎰 АНИМАЦИЯ #15 - САПФИРОВЫЕ ВИШНИ!",
    16: "🎰 АНИМАЦИЯ #16 - РАДУЖНЫЕ ЛИМОНЫ!",
    17: "🎰 АНИМАЦИЯ #17 - ГАЛАКТИЧЕСКИЕ 777!",
    18: "🎰 АНИМАЦИЯ #18 - ЛЕДЯНЫЕ БАРЫ!",
    19: "🎰 АНИМАЦИЯ #19 - АЛМАЗНЫЕ ВИШНИ!",
    20: "🎰 АНИМАЦИЯ #20 - ОГНЕННЫЕ ЛИМОНЫ!",
    21: "🎰 АНИМАЦИЯ #21 - КОСМИЧЕСКИЕ СЕМЕРКИ!",
    22: "🎰 АНИМАЦИЯ #22 - ЗОЛОТИСТЫЕ БАРЫ!",
    23: "🎰 АНИМАЦИЯ #23 - ПЛАМЕННЫЕ ВИШНИ!",
    24: "🎰 АНИМАЦИЯ #24 - СВЕРКАЮЩИЕ ЛИМОНЫ!",
    25: "🎰 АНИМАЦИЯ #25 - МАГИЧЕСКИЕ 777!",
    26: "🎰 АНИМАЦИЯ #26 - СТАЛЬНЫЕ БАРЫ!",
    27: "🎰 АНИМАЦИЯ #27 - БУРЯНЫЕ ВИШНИ!",
    28: "🎰 АНИМАЦИЯ #28 - МЕДОВЫЕ ЛИМОНЫ!",
    29: "🎰 АНИМАЦИЯ #29 - ЗАГАДОЧНЫЕ СЕМЕРКИ!",
    30: "🎰 АНИМАЦИЯ #30 - МРАМОРНЫЕ БАРЫ!",
    31: "🎰 АНИМАЦИЯ #31 - ШОКОЛАДНЫЕ ВИШНИ!",
    32: "🎰 АНИМАЦИЯ #32 - ВИХРЕВЫЕ ЛИМОНЫ!",
    33: "🎰 АНИМАЦИЯ #33 - СКАЗОЧНЫЕ 777!",
    34: "🎰 АНИМАЦИЯ #34 - ДЫМЧАТЫЕ БАРЫ!",
    35: "🎰 АНИМАЦИЯ #35 - ВИННЫЕ ВИШНИ!",
    36: "🎰 АНИМАЦИЯ #36 - ЦИТРУСОВЫЕ ЛИМОНЫ!",
    37: "🎰 АНИМАЦИЯ #37 - ТАИНСТВЕННЫЕ СЕМЕРКИ!",
    38: "🎰 АНИМАЦИЯ #38 - ГРАНИТНЫЕ БАРЫ!",
    39: "🎰 АНИМАЦИЯ #39 - КЛУБНИЧНЫЕ ВИШНИ!",
    40: "🎰 АНИМАЦИЯ #40 - СОЛНЕЧНЫЕ ЛИМОНЫ!",
    41: "🎰 АНИМАЦИЯ #41 - ЛЕГЕНДАРНЫЕ 777!",
    42: "🎰 АНИМАЦИЯ #42 - ПЕСОЧНЫЕ БАРЫ!",
    43: "🎰 АНИМАЦИЯ #43 - ВЕСЕННИЕ ВИШНИ!",
    44: "🎰 АНИМАЦИЯ #44 - ТРОПИЧЕСКИЕ ЛИМОНЫ!",
    45: "🎰 АНИМАЦИЯ #45 - МИСТИЧЕСКИЕ СЕМЕРКИ!",
    46: "🎰 АНИМАЦИЯ #46 - БЕТОННЫЕ БАРЫ!",
    47: "🎰 АНИМАЦИЯ #47 - ОСЕННИЕ ВИШНИ!",
    48: "🎰 АНИМАЦИЯ #48 - ЛАЙМОВЫЕ ЛИМОНЫ!",
    49: "🎰 АНИМАЦИЯ #49 - БАЗОВЫЕ 777!",
    50: "🎰 АНИМАЦИЯ #50 - ДЕРЕВЯННЫЕ БАРЫ!",
    51: "🎰 АНИМАЦИЯ #51 - СВЕЖИЕ ВИШНИ!",
    52: "🎰 АНИМАЦИЯ #52 - КЛАССИЧЕСКИЕ ЛИМОНЫ!",
    53: "🎰 АНИМАЦИЯ #53 - СТАНДАРТНЫЕ СЕМЕРКИ!",
    54: "🎰 АНИМАЦИЯ #54 - ПРОСТЫЕ БАРЫ!",
    55: "🎰 АНИМАЦИЯ #55 - ЗЕЛЕНЫЕ ВИШНИ!",
    56: "🎰 АНИМАЦИЯ #56 - ЖЕЛТЫЕ ЛИМОНЫ!",
    57: "🎰 АНИМАЦИЯ #57 - ОБЫЧНЫЕ 777!",
    58: "🎰 АНИМАЦИЯ #58 - ПРОЗРАЧНЫЕ БАРЫ!",
    59: "🎰 АНИМАЦИЯ #59 - КРАСНЫЕ ВИШНИ!",
    60: "🎰 АНИМАЦИЯ #60 - СИНИЕ ЛИМОНЫ!",
    61: "🎰 АНИМАЦИЯ #61 - ФИНАЛЬНЫЕ СЕМЕРКИ!",
    62: "🎰 АНИМАЦИЯ #62 - ПОСЛЕДНИЕ БАРЫ!",
    63: "🎰 АНИМАЦИЯ #63 - УЛЬТИМАТИВНЫЕ ВИШНИ!",
    64: "🎰 АНИМАЦИЯ #64 - ЛЕГЕНДАРНЫЕ ЛИМОНЫ!"
}

# 🗃️ БАЗА ДАННЫХ ДЛЯ ИССЛЕДОВАНИЯ
slot_research_data = {}
user_data = defaultdict(lambda: {
    'game_balance': 1000,
    'total_games': 0,
    'total_wins': 0,
})

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎰 РЕЖИМ ИССЛЕДОВАНИЯ СЛОТОВ\n\n"
        "Каждой из 64 анимаций будет присвоен уникальный номер!\n\n"
        "Команды:\n"
        "/research - Показать все найденные значения\n"
        "/slot X - Информация о конкретном слоте (1-64)\n"
        "/test_slots - Начать тестирование\n\n"
        "Отправь 🎰 чтобы определить номер анимации!"
    )

async def test_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск тестирования слотов"""
    user_id = update.effective_user.id
    user_data[user_id]['game_balance'] = 1000
    
    await update.message.reply_text(
        "🎰 ТЕСТИРОВАНИЕ АКТИВИРОВАНО\n\n"
        "Отправляй 🎰 в чат - я буду показывать номер каждой анимации!\n"
        "Всего существует 64 возможных значения.\n\n"
        "После теста используй /research для просмотра статистики."
    )

async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать результаты исследования"""
    if not slot_research_data:
        await update.message.reply_text("🔍 Данных пока нет. Сыграй в слоты!")
        return
    
    research_text = "🎰 РЕЗУЛЬТАТЫ ИССЛЕДОВАНИЯ\n\n"
    research_text += f"📊 Найдено: {len(slot_research_data)}/64 значений\n\n"
    
    # Группируем по 8 значений в строке
    for i in range(0, 64, 8):
        line = ""
        for j in range(i+1, i+9):
            if j in slot_research_data:
                count = slot_research_data[j]['count']
                line += f"🎰{j:02d}({count}) "
            else:
                line += f"❓{j:02d} "
        research_text += line + "\n"
    
    research_text += f"\n📋 Полный список: {sorted(slot_research_data.keys())}"
    
    await update.message.reply_text(research_text)

async def slot_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о конкретном слоте"""
    if not context.args:
        await update.message.reply_text("Использование: /slot <номер от 1 до 64>")
        return
    
    try:
        slot_number = int(context.args[0])
        if slot_number < 1 or slot_number > 64:
            await update.message.reply_text("Номер слота должен быть от 1 до 64")
            return
            
        if slot_number in slot_research_data:
            data = slot_research_data[slot_number]
            info_text = f"🎰 ИНФОРМАЦИЯ О СЛОТЕ #{slot_number}\n\n"
            info_text += f"📊 Выпадал раз: {data['count']}\n"
            info_text += f"👥 Тестеров: {len(data['users'])}\n"
            info_text += f"📅 Первый раз: {data['first_seen'][:19]}\n"
            info_text += f"🎯 Диапазон: {get_slot_range(slot_number)}\n"
            
        else:
            info_text = f"🎰 Слот #{slot_number} еще не найден!\nПродолжай тестировать 🎰"
            
        await update.message.reply_text(info_text)
        
    except ValueError:
        await update.message.reply_text("Номер должен быть числом от 1 до 64")

def get_slot_range(slot_number):
    """Определяем диапазон слота"""
    if slot_number <= 16:
        return "ВЫСОКИЙ (1-16)"
    elif slot_number <= 32:
        return "СРЕДНИЙ (17-32)"
    elif slot_number <= 48:
        return "НИЗКИЙ (33-48)"
    else:
        return "ОЧЕНЬ НИЗКИЙ (49-64)"

def generate_unique_slot_message(slot_value):
    """Генерирует уникальное сообщение для каждого значения слота"""
    if slot_value in SLOT_MESSAGES:
        message = SLOT_MESSAGES[slot_value]
    else:
        message = f"🎰 АНИМАЦИЯ #{slot_value} - УНИКАЛЬНАЯ КОМБИНАЦИЯ!"
    
    return f"{message}\n🔢 Номер значения: {slot_value}/64\n🎯 Диапазон: {get_slot_range(slot_value)}"

# 🎮 СИСТЕМА ИГР - ТЕСТОВЫЙ РЕЖИМ
async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    emoji = update.message.text
    
    if emoji != "🎰":
        await update.message.reply_text("🎰 В этом режиме работают только слоты!")
        return
    
    user_data[user_id]['total_games'] += 1
    
    context.user_data['expecting_dice'] = True
    context.user_data['last_game_type'] = 'slots'
    context.user_data['last_game_user_id'] = user_id
    
    dice_message = await context.bot.send_dice(chat_id=update.message.chat_id, emoji=emoji)
    context.user_data['last_dice_message_id'] = dice_message.message_id
    
    await update.message.reply_text(
        f"🔬 Тестовый бросок #{user_data[user_id]['total_games']}\n"
        f"🎯 Определяю номер анимации..."
    )

# 🎰 ОБРАБОТКА DICE - УНИКАЛЬНЫЕ СООБЩЕНИЯ ДЛЯ КАЖДОГО ЗНАЧЕНИЯ
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
        # СОХРАНЯЕМ ДАННЫЕ ИССЛЕДОВАНИЯ
        if value not in slot_research_data:
            slot_research_data[value] = {
                'first_seen': datetime.datetime.now().isoformat(),
                'count': 0,
                'users': set()
            }
        
        slot_research_data[value]['count'] += 1
        slot_research_data[value]['users'].add(user_id)
        
        # УНИКАЛЬНОЕ СООБЩЕНИЕ ДЛЯ КАЖДОГО ЗНАЧЕНИЯ
        result_text = generate_unique_slot_message(value)
        
        # ДОБАВЛЯЕМ СТАТИСТИКУ
        result_text += f"\n\n📊 Статистика этого значения:"
        result_text += f"\n🎰 Выпадало раз: {slot_research_data[value]['count']}"
        result_text += f"\n👥 Уникальных тестеров: {len(slot_research_data[value]['users'])}"
        result_text += f"\n📈 Всего найдено: {len(slot_research_data)}/64"
        
        # ССЫЛКА НА КОМАНДУ ДЛЯ ПРОСМОТРА
        result_text += f"\n\n💡 Подробнее: /slot {value}"
        
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
            "Отправляй 🎰 в чат - я покажу номер каждой анимации!\n"
            "Всего 64 возможных значения."
        )

# 🌐 FLASK ДЛЯ RAILWAY
app = Flask(__name__)

@app.route('/')
def home():
    return "🎰 Slot Research Bot - Определяем номера анимаций!"

@app.route('/research')
def research_web():
    """Веб-страница с исследованием"""
    if not slot_research_data:
        return "<h1>🎰 Исследование слотов</h1><p>Данных пока нет</p>"
    
    html = "<h1>🎰 Исследование слотов</h1>"
    html += f"<p>Найдено значений: {len(slot_research_data)}/64</p>"
    html += "<table border='1'><tr><th>Значение</th><th>Сообщение</th><th>Количество</th><th>Тестеров</th></tr>"
    
    for value in sorted(slot_research_data.keys()):
        data = slot_research_data[value]
        message = SLOT_MESSAGES.get(value, "УНИКАЛЬНАЯ КОМБИНАЦИЯ")
        html += f"<tr><td>{value}</td><td>{message}</td><td>{data['count']}</td><td>{len(data['users'])}</td></tr>"
    
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
    application.add_handler(CommandHandler("slot", slot_info_command))
    
    # CALLBACK'И
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # СООБЩЕНИЯ
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(🎰)$"), handle_game_message))
    application.add_handler(MessageHandler(filters.Dice.ALL, handle_dice_result))
    
    print("🎰 Slot Research Bot запущен!")
    print("🔬 Каждой анимации будет присвоен уникальный номер!")
    application.run_polling()

if __name__ == '__main__':
    main()
