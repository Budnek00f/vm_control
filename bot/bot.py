import os
import psutil
import docker
import requests
import logging
from aiogram import Bot, Dispatcher, executor, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")

# Проверка обязательных переменных
if not BOT_TOKEN:
    logger.error("BOT_TOKEN не установлен!")
    exit(1)

if not ADMIN_ID:
    logger.error("ADMIN_ID не установлен!")
    exit(1)

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    logger.error("ADMIN_ID должен быть числом!")
    exit(1)

try:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot)
    client = docker.from_env()
except Exception as e:
    logger.error(f"Ошибка инициализации: {e}")
    exit(1)

SERVICES = {
    "Prometheus": f"http://{SERVER_IP}:9090/-/healthy",
    "Grafana": f"http://{SERVER_IP}:3000/api/health",
    "Loki": f"http://{SERVER_IP}:3100/ready",
    "Nginx": f"http://{SERVER_IP}/",
}

async def check_services():
    """Проверка доступности сервисов"""
    for name, url in SERVICES.items():
        try:
            r = requests.get(url, timeout=5)
            if r.status_code not in (200, 204):
                await bot.send_message(ADMIN_ID, f"⚠️ {name} недоступен! Код: {r.status_code}")
        except Exception as e:
            await bot.send_message(ADMIN_ID, f"❌ {name} недоступен! Ошибка: {e}")

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return await msg.answer("⛔ Нет доступа")
    await msg.answer("✅ Бот запущен. Команды:\n/status\n/containers\n/logs\n/check")

@dp.message_handler(commands=["status"])
async def status(msg: types.Message):
    try:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        await msg.answer(f"🖥 CPU: {cpu}%\n💾 RAM: {mem}%\n📀 Disk: {disk}%")
    except Exception as e:
        await msg.answer(f"❌ Ошибка получения статуса: {e}")

@dp.message_handler(commands=["containers"])
async def containers(msg: types.Message):
    try:
        containers_list = client.containers.list(all=True)
        text = "\n".join([f"{c.name} — {c.status}" for c in containers_list])
        await msg.answer(text or "Нет контейнеров")
    except Exception as e:
        await msg.answer(f"❌ Ошибка получения контейнеров: {e}")

@dp.message_handler(commands=["logs"])
async def logs(msg: types.Message):
    try:
        container = client.containers.get("vm_control_bot_1")  # исправлено имя контейнера
        logs_text = container.logs(tail=10).decode('utf-8', errors='ignore')
        # Ограничиваем длину сообщения
        if len(logs_text) > 4000:
            logs_text = logs_text[:4000] + "..."
        await msg.answer(f"📜 Логи:\n{logs_text}")
    except Exception as e:
        await msg.answer(f"❌ Ошибка получения логов: {e}")

@dp.message_handler(commands=["check"])
async def check_now(msg: types.Message):
    await check_services()
    await msg.answer("🔎 Проверка завершена")

if __name__ == "__main__":
    try:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(check_services, "interval", minutes=1)
        scheduler.start()
        logger.info("Бот запускается...")
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")