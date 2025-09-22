import os
import psutil
import docker
import requests
from aiogram import Bot, Dispatcher, executor, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
client = docker.from_env()

SERVICES = {
    "Prometheus": f"http://{SERVER_IP}:9090/-/healthy",
    "Grafana": f"http://{SERVER_IP}:3000/api/health",
    "Loki": f"http://{SERVER_IP}:3100/ready",
    "Nginx": f"http://{SERVER_IP}/",
}

async def check_services():
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
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    await msg.answer(f"🖥 CPU: {cpu}%\n💾 RAM: {mem}%\n📀 Disk: {disk}%")

@dp.message_handler(commands=["containers"])
async def containers(msg: types.Message):
    containers = client.containers.list(all=True)
    text = "\n".join([f"{c.name} — {c.status}" for c in containers])
    await msg.answer(text or "Нет контейнеров")

@dp.message_handler(commands=["logs"])
async def logs(msg: types.Message):
    try:
        container = client.containers.get("server-bot")
        logs = container.logs(tail=10).decode()
        await msg.answer(f"📜 Логи:\n{logs}")
    except Exception as e:
        await msg.answer(str(e))

@dp.message_handler(commands=["check"])
async def check_now(msg: types.Message):
    await check_services()
    await msg.answer("🔎 Проверка завершена")

if __name__ == "__main__":
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_services, "interval", minutes=1)
    scheduler.start()
    executor.start_polling(dp)
