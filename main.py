import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiohttp import web

import config
import database
from handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    """Регистрирует список команд в меню Telegram."""
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="setrole", description="🎭 Установить роль/промпт"),
        BotCommand(command="getrole", description="👀 Посмотреть текущую роль"),
        BotCommand(command="clear", description="🧹 Очистить историю диалога"),
        BotCommand(command="reset", description="🔄 Сбросить настройки"),
        BotCommand(command="help", description="📖 Справка и примеры"),
    ]
    await bot.set_my_commands(commands)


async def handle_health_check(request):
    """Эндпоинт для проверки здоровья облачными хостингами (Render, Koyeb, Railway)."""
    return web.Response(text="Telegram Bot is alive 24/7! 🚀", status=200)


async def start_web_health_server():
    """Запускает мини-веб-сервер, если облачный хостинг передает переменную PORT."""
    port_str = os.getenv("PORT")
    if not port_str:
        return None

    port = int(port_str)
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Health-check веб-сервер запущен на порту {port}")
    return runner


async def run_bot_session():
    """Запуск одной сессии бота."""
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        logger.error(
            "❌ ОШИБКА: TELEGRAM_BOT_TOKEN не задан! "
            "Укажите токен вашего бота в файле .env или переменных окружения хостинга."
        )
        return False

    logger.info("Инициализация базы данных...")
    await database.init_db()

    bot = Bot(
        token=config.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await set_bot_commands(bot)
    await bot.delete_webhook(drop_pending_updates=False)

    # Запускаем мини веб-сервер для облачных платформ (Render, Koyeb и др.)
    web_runner = await start_web_health_server()

    logger.info("🟢 Бот успешно запущен в режиме 24/7...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if web_runner:
            await web_runner.cleanup()

    return True


async def main():
    """Главный цикл с автоматическим переподключением при сбоях."""
    retry_delay = 5
    while True:
        try:
            started = await run_bot_session()
            if not started:
                break
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Остановка бота.")
            break
        except Exception as exc:
            logger.error(f"⚠️ Непредвиденная ошибка в работе: {exc}", exc_info=True)
            logger.info(f"⏳ Перезапуск через {retry_delay} секунд...")
            await asyncio.sleep(retry_delay)


if __name__ == "__main__":
    asyncio.run(main())
