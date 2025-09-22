import logging
import os
import subprocess
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Список контейнеров для управления
CONTAINERS = [
    "grafana",
    "vm_control_bot_1", 
    "prometheus",
    "promtail",
    "nginx",
    "loki",
    "node-exporter"
]

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🔄 Управление контейнерами", callback_data="manage_containers")],
        [InlineKeyboardButton("📊 Статус всех контейнеров", callback_data="status_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Добро пожаловать в панель управления Docker контейнерами!\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "manage_containers":
        await show_containers_list(query)
    elif data == "status_all":
        await status_all_containers(query)
    elif data.startswith("container_"):
        container_name = data.replace("container_", "")
        await show_container_actions(query, container_name)
    elif data.startswith("action_"):
        parts = data.split("_")
        container_name = parts[2]
        action = parts[1]
        await perform_container_action(query, container_name, action)

# Показать список контейнеров
async def show_containers_list(query) -> None:
    keyboard = []
    
    for container in CONTAINERS:
        keyboard.append([InlineKeyboardButton(f"📦 {container}", callback_data=f"container_{container}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📋 Список контейнеров:\nВыберите контейнер для управления:",
        reply_markup=reply_markup
    )

# Показать действия для конкретного контейнера
async def show_container_actions(query, container_name: str) -> None:
    # Проверяем статус контейнера
    status = get_container_status(container_name)
    status_icon = "🟢" if status == "running" else "🔴" if status == "exited" else "⚫"
    
    keyboard = [
        [InlineKeyboardButton("🚀 Запустить", callback_data=f"action_start_{container_name}")],
        [InlineKeyboardButton("⏹️ Остановить", callback_data=f"action_stop_{container_name}")],
        [InlineKeyboardButton("🔄 Перезапустить", callback_data=f"action_restart_{container_name}")],
        [InlineKeyboardButton("📊 Статус", callback_data=f"action_status_{container_name}")],
        [InlineKeyboardButton("🔙 Назад к списку", callback_data="manage_containers")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📦 Контейнер: {container_name}\n"
        f"Статус: {status_icon} {status}\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

# Выполнить действие с контейнером
async def perform_container_action(query, container_name: str, action: str) -> None:
    try:
        if action == "start":
            result = subprocess.run(["docker", "start", container_name], capture_output=True, text=True)
            message = f"✅ Контейнер {container_name} запущен" if result.returncode == 0 else f"❌ Ошибка: {result.stderr}"
        
        elif action == "stop":
            result = subprocess.run(["docker", "stop", container_name], capture_output=True, text=True)
            message = f"⏹️ Контейнер {container_name} остановлен" if result.returncode == 0 else f"❌ Ошибка: {result.stderr}"
        
        elif action == "restart":
            result = subprocess.run(["docker", "restart", container_name], capture_output=True, text=True)
            message = f"🔄 Контейнер {container_name} перезапущен" if result.returncode == 0 else f"❌ Ошибка: {result.stderr}"
        
        elif action == "status":
            status = get_container_status(container_name)
            status_icon = "🟢" if status == "running" else "🔴" if status == "exited" else "⚫"
            message = f"📦 {container_name}: {status_icon} {status}"
        
        await query.edit_message_text(message)
        
        # Показываем кнопки управления снова через 2 секунды
        await asyncio.sleep(2)
        await show_container_actions(query, container_name)
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")

# Получить статус контейнера
def get_container_status(container_name: str) -> str:
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
            capture_output=True, text=True
        )
        return result.stdout.strip() if result.returncode == 0 else "not found"
    except:
        return "error"

# Статус всех контейнеров
async def status_all_containers(query) -> None:
    status_text = "📊 Статус всех контейнеров:\n\n"
    
    for container in CONTAINERS:
        status = get_container_status(container)
        status_icon = "🟢" if status == "running" else "🔴" if status == "exited" else "⚫"
        status_text += f"{status_icon} {container}: {status}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(status_text, reply_markup=reply_markup)

# Обработчик кнопки "Назад"
async def back_to_main(query) -> None:
    keyboard = [
        [InlineKeyboardButton("🔄 Управление контейнерами", callback_data="manage_containers")],
        [InlineKeyboardButton("📊 Статус всех контейнеров", callback_data="status_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Главное меню управления Docker контейнерами:\nВыберите действие:",
        reply_markup=reply_markup
    )

# Основная функция
def main() -> None:
    # Получаем токен бота из переменных окружения
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен!")
        return

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запускаем бота
    application.run_polling()
    logger.info("Бот запущен!")

if __name__ == '__main__':
    main()