from aiogram import Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender

import database
import llm_service
from config import DEFAULT_SYSTEM_PROMPT

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
    current_prompt = await database.get_user_prompt(message.from_user.id)
    
    text = (
        "👋 **Добро пожаловать в бота с настраиваемыми ролями!**\n\n"
        "Вы можете задать любую роль или инструкцию (системный промпт), "
        "и бот будет отвечать строго по вашей схеме.\n\n"
        "📌 **Основные команды:**\n"
        "• `/setrole` — Задать новую роль (промпт)\n"
        "• `/getrole` — Посмотреть текущую роль\n"
        "• `/clear` — Очистить историю диалога (роль сохранится)\n"
        "• `/reset` — Сбросить роль на стандартную и очистить память\n"
        "• `/help` — Справка и примеры промптов\n\n"
        "💬 *Просто напишите сообщение, чтобы начать диалог!*"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "📖 **Справка по использованию бота**\n\n"
        "🔹 **Как задать роль:**\n"
        "1. Напишите команду `/setrole` и отправьте текст промпта в ответ.\n"
        "   *Или в одну строку:* `/setrole Ты — эксперт по Python...`\n\n"
        "🔹 **Примеры ролей:**\n"
        "• `Ты — опытный репетитор английского языка. Исправляй мои ошибки и объясняй грамматику.`\n"
        "• `Ты — персонаж детективной игры 1930-х годов в стиле нуар. Отвечай загадочно и атмосферно.`\n"
        "• `Ты — строгий критик кода. Анализируй код и давай рекомендации по оптимизации.`\n\n"
        "🔹 **Управление памятью:**\n"
        "• `/clear` — стирает контекст текущего разговора, если бот начал путаться.\n"
        "• `/reset` — возвращает исходного ассистента."
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("setrole", "setprompt"))
async def cmd_setrole(message: types.Message, state: FSMContext):
    # Проверяем, передан ли промпт прямо в команде (например, "/setrole Текст...")
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

    # Если аргумент не передан, переводим пользователя в режим ожидания текста
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
        "Установлена стандартная роль ассистента, память очищена.",
        parse_mode="Markdown",
    )


@router.message(F.text)
async def handle_user_query(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text.strip()

    if not user_text:
        return

    # Получаем промпт и контекст
    system_prompt = await database.get_user_prompt(user_id)
    history = await database.get_chat_history(user_id)

    # Отображаем статус «печатает...»
    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        reply_text = await llm_service.generate_response(
            system_prompt=system_prompt,
            history=history,
            user_message=user_text
        )

    # Сохраняем сообщения в базу данных
    await database.add_message(user_id, "user", user_text)
    await database.add_message(user_id, "assistant", reply_text)

    # Отправляем ответ (с разбивкой на части, если ответ очень длинный)
    chunks = split_text(reply_text)
    for chunk in chunks:
        await message.answer(chunk)
