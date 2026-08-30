from aiogram import Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender

import database
import llm_service
from config import DEFAULT_SYSTEM_PROMPT, DEFAULT_TEMPERATURE

router = Router()


class RoleStates(StatesGroup):
    waiting_for_prompt = State()


def split_text(text: str, max_length: int = 4000) -> list[str]:
    """Разбивает длинный текст на части для соблюдения лимитов Telegram (4096 символов)."""
    chunks = []
    while len(text) > max_length:
        split_idx = text.rfind("\n", 0, max_length)
        if split_idx == -1:
            split_idx = max_length
        chunks.append(text[:split_idx])
        text = text[split_idx:].lstrip()
    if text:
        chunks.append(text)
    return chunks


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    text = (
        "👋 **Добро пожаловать в бота с настраиваемыми ролями!**\n\n"
        "Вы можете задать любую роль или инструкцию (системный промпт), "
        "и бот будет отвечать строго по вашей схеме.\n\n"
        "📌 **Основные команды:**\n"
        "• `/setrole` — Задать новую роль (промпт)\n"
        "• `/getrole` — Посмотреть текущую роль\n"
        "• `/settemp` — Настроить температуру (креативность, например `0.8`)\n"
        "• `/clear` — Очистить историю диалога (роль сохранится)\n"
        "• `/reset` — Сбросить настройки на стандартные\n"
        "• `/help` — Справка и примеры\n\n"
        "💬 *Просто напишите сообщение, чтобы начать диалог!*"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "📖 **Справка по использованию бота**\n\n"
        "🔹 **Управление ролью:**\n"
        "• `/setrole` — напишите команду и отправьте текст промпта в ответ.\n"
        "  *Или в одну строку:* `/setrole Ты — эксперт...`\n"
        "• `/getrole` — посмотреть текущую роль.\n\n"
        "🔹 **Температура генерации (креативность):**\n"
        "• `/settemp 0.8` — задать температуру (0.1 — строгие и точные ответы, 0.7-0.8 — живая и естественная речь, 1.0+ — максимальная фантазия).\n"
        "• `/gettemp` — посмотреть текущую температуру.\n\n"
        "🔹 **Управление памятью:**\n"
        "• `/clear` — очистить контекст диалога.\n"
        "• `/reset` — полный сброс на стандартного ассистента."
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("settemp", "temp", "temperature"))
async def cmd_settemp(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current_temp = await database.get_user_temperature(message.from_user.id)
        await message.answer(
            f"🌡️ **Текущая температура:** `{current_temp}`\n\n"
            f"Чтобы изменить, укажите значение от `0.0` до `2.0`:\n"
            f"Пример: `/settemp 0.8` (рекомендуется 0.7 – 0.8 для естественной речи)",
            parse_mode="Markdown",
        )
        return

    try:
        new_temp = float(args[1].strip().replace(",", "."))
        if not (0.0 <= new_temp <= 2.0):
            raise ValueError()
    except ValueError:
        await message.answer("❌ Пожалуйста, укажите число от `0.0` до `2.0`. Пример: `/settemp 0.8`", parse_mode="Markdown")
        return

    await database.set_user_temperature(message.from_user.id, new_temp)
    await message.answer(f"✅ **Температура генерации установлена на:** `{new_temp}` 🌡️", parse_mode="Markdown")


@router.message(Command("gettemp"))
async def cmd_gettemp(message: types.Message):
    current_temp = await database.get_user_temperature(message.from_user.id)
    await message.answer(f"🌡️ **Текущая температура генерации:** `{current_temp}`", parse_mode="Markdown")


@router.message(Command("setrole", "setprompt"))
async def cmd_setrole(message: types.Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].strip():
        new_prompt = args[1].strip()
        await database.set_user_prompt(message.from_user.id, new_prompt)
        await database.clear_chat_history(message.from_user.id)
        await message.answer(
            f"✅ **Роль успешно обновлена!**\n\n"
            f"📋 *Текущий промпт:*\n`{new_prompt}`\n\n"
            f"История диалога очищена. Начните общение!",
            parse_mode="Markdown",
        )
        return

    await state.set_state(RoleStates.waiting_for_prompt)
    await message.answer(
        "📝 **Отправьте текст системного промпта (роли) следующим сообщением:**\n\n"
        "Вы можете написать подробные инструкции, характер, тон общения и правила.\n"
        "Для отмены отправьте `/cancel`.",
        parse_mode="Markdown",
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного действия для отмены.")
        return

    await state.clear()
    await message.answer("❌ Настройка роли отменена.")


@router.message(RoleStates.waiting_for_prompt)
async def process_new_role(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое описание роли.")
        return

    new_prompt = message.text.strip()
    await database.set_user_prompt(message.from_user.id, new_prompt)
    await database.clear_chat_history(message.from_user.id)
    await state.clear()

    await message.answer(
        f"✅ **Новая роль успешно сохранена!**\n\n"
        f"📋 *Промпт:*\n`{new_prompt}`\n\n"
        f"История диалога сброшена для нового контекста. Задайте ваш вопрос!",
        parse_mode="Markdown",
    )


@router.message(Command("getrole", "getprompt"))
async def cmd_getrole(message: types.Message):
    prompt = await database.get_user_prompt(message.from_user.id)
    await message.answer(
        f"🎭 **Ваша текущая роль / системный промпт:**\n\n"
        f"`{prompt}`\n\n"
        f"Чтобы изменить, используйте `/setrole`.",
        parse_mode="Markdown",
    )


@router.message(Command("clear"))
async def cmd_clear(message: types.Message):
    await database.clear_chat_history(message.from_user.id)
    await message.answer("🧹 **История текущего диалога очищена!** Роль сохранена.")


@router.message(Command("reset"))
async def cmd_reset(message: types.Message, state: FSMContext):
    await state.clear()
    await database.reset_user_prompt(message.from_user.id)
    await database.clear_chat_history(message.from_user.id)
    await message.answer(
        "🔄 **Все настройки сброшены!**\n"
        "Установлена стандартная роль ассистента, температура 0.8, память очищена.",
        parse_mode="Markdown",
    )


@router.message(F.text)
async def handle_user_query(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text.strip()

    if not user_text:
        return

    # Получаем промпт, температуру и контекст
    system_prompt = await database.get_user_prompt(user_id)
    temperature = await database.get_user_temperature(user_id)
    history = await database.get_chat_history(user_id)

    # Отображаем статус «печатает...»
    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        reply_text = await llm_service.generate_response(
            system_prompt=system_prompt,
            history=history,
            user_message=user_text,
            temperature=temperature
        )

    # Сохраняем сообщения в базу данных
    await database.add_message(user_id, "user", user_text)
    await database.add_message(user_id, "assistant", reply_text)

    # Отправляем ответ
    chunks = split_text(reply_text)
    for chunk in chunks:
        await message.answer(chunk)
