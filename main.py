import os
import datetime
import asyncio
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# 🔧 КОНФИГУРАЦИЯ
BOT_TOKEN = "8378526693:AAFOwAb6pVp1GOE0tXZN4PDLFnD_TTT1djg"

# 🗃️ БАЗА ДАННЫХ
research_data = {
    "🏀": defaultdict(lambda: {'count': 0}),
    "⚽": defaultdict(lambda: {'count': 0})
}

# 👤 ОСНОВНЫЕ КОМАНДЫ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 ИССЛЕДОВАНИЕ АНИМАЦИЙ\n\n"
        "Отправь 🏀 или ⚽ - бот покажет номер анимации (1-5)\n"
        "/stats - статистика\n"
        "/clear - очистить"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_text = "📊 СТАТИСТИКА:\n\n"
    
    for emoji, data in research_data.items():
        game_name = "БАСКЕТБОЛ" if emoji == "🏀" else "ФУТБОЛ"
        stats_text += f"{emoji} {game_name}:\n"
        for value in sorted(data.keys()):
            stats_text += f"Анимация #{value}: {data[value]['count']} раз\n"
        stats_text += "\n"
    
    await update.message.reply_text(stats_text)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    research_data["🏀"].clear()
    research_data["⚽"].clear()
    await update.message.reply_text("✅ Статистика очищена!")

# 🎮 ОБРАБОТКА ИГР
async def handle_game_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emoji = update.message.text
    
    if emoji not in ["🏀", "⚽"]:
        return
    
    # Сразу отправляем текстовое сообщение о том, что получили
    game_name = "БАСКЕТБОЛ" if emoji == "🏀" else "ФУТБОЛ"
    await update.message.reply_text(f"✅ Вы отправили: {emoji} ({game_name})")
    
    # Отправляем dice и получаем значение
    dice_message = await context.bot.send_dice(
        chat_id=update.message.chat_id, 
        emoji=emoji
    )
    
    value = dice_message.dice.value
    
    # Ждем окончания анимации
    await asyncio.sleep(2)
    
    # Обновляем статистику
    research_data[emoji][value]['count'] += 1
    
    # Отправляем результат с номером анимации
    result_text = f"🎯 НОМЕР АНИМАЦИИ: #{value}\n📊 Всего выпадала: {research_data[emoji][value]['count']} раз"
    
    await update.message.reply_text(result_text)

# 🚀 ЗАПУСК БОТА
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # КОМАНДЫ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("clear", clear_command))
    
    # СООБЩЕНИЯ
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(🏀|⚽)$"), handle_game_message))
    
    print("🔍 Бот запущен! Отправляй 🏀 или ⚽")
    application.run_polling()

if __name__ == '__main__':
    main()
