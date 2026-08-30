from aiogram import Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender

import database
import llm_service
from config import DEFAULT_SYSTEM_PROMPT, DEFAULT_TEMPERATURE, LLM_MODEL

router = Router()


class RoleStates(StatesGroup):
    waiting_for_prompt = State()


class PlanStates(StatesGroup):
    waiting_for_plan_prompt = State()


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
        "👋 **Добро пожаловать в бота с настраиваемыми ролями и генератором планов!**\n\n"
        "📌 **Основные команды:**\n"
        "• `/plan` — 📅 **Сгенерировать новый план на день / эфир**\n"
        "• `/setplanprompt` — Настроить шаблон/инструкции для генератора планов\n"
        "• `/getplanprompt` — Посмотреть текущий шаблон плана\n\n"
        "🎭 **Настройки общения:**\n"
        "• `/setrole` — Задать роль (системный промпт)\n"
        "• `/getrole` — Посмотреть текущую роль\n"
        "• `/setmodel` — Выбрать модель нейросети\n"
        "• `/settemp` — Настроить креативность (температуру)\n"
        "• `/clear` — Очистить историю диалога\n"
        "• `/help` — Подробная справка\n\n"
        "💬 *Отправьте команду `/plan` для генерации сценария или просто напишите сообщение!*"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "📖 **Справка по командам бота**\n\n"
        "📅 **Генератор планов:**\n"
        "• `/plan` — мгновенно создает новый план по вашему шаблону.\n"
        "  *Можно с уточнениями:* `/plan добавь больше интерактива в 3-й час`\n"
        "• `/setplanprompt` — задать ваши собственные правила и структуру для генерации планов.\n"
        "• `/getplanprompt` — посмотреть текущую инструкцию для планов.\n\n"
        "🎭 **Ролевой чат:**\n"
        "• `/setrole` — настроить характер и роль собеседника.\n"
        "• `/getrole` — посмотреть текущую роль.\n"
        "• `/setmodel <название>` — сменить модель (например, `meta-llama/llama-3.3-70b-instruct`).\n"
        "• `/settemp <0.0-2.0>` — настроить температуру (0.8 — живая речь).\n"
        "• `/clear` — очистить историю диалога."
    )
    await message.answer(text, parse_mode="Markdown")


# ==========================================
#     ГЕНЕРАЦИЯ И НАСТРОЙКА ПЛАНОВ
# ==========================================

@router.message(Command("plan", "makeplan", "dailyplan"))
async def cmd_generate_plan(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    extra_wishes = args[1].strip() if len(args) > 1 else ""

    # Получаем шаблон плана и системные настройки
    base_plan_prompt = await database.get_user_plan_prompt(user_id)
    user_role = await database.get_user_prompt(user_id)
    temperature = await database.get_user_temperature(user_id)
    model = await database.get_user_model(user_id)

    full_plan_request = base_plan_prompt
    if extra_wishes:
        full_plan_request += f"\n\nДополнительные пожелания к этому плану:\n{extra_wishes}"

    system_instruction = (
        f"{user_role}\n\n"
        "Ты также составляешь четкие, профессиональные, поминутно структурированные планы и сценарии "
        "в точном соответствии с инструкцией пользователя."
    )

    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        reply_text = await llm_service.generate_response(
            system_prompt=system_instruction,
            history=[],
            user_message=full_plan_request,
            temperature=temperature,
            model=model
        )

    # Сохраняем генерацию в историю
    await database.add_message(user_id, "user", f"/plan {extra_wishes}".strip())
    await database.add_message(user_id, "assistant", reply_text)

    chunks = split_text(reply_text)
    for chunk in chunks:
        await message.answer(chunk)


@router.message(Command("setplanprompt"))
async def cmd_setplanprompt(message: types.Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].strip():
        new_prompt = args[1].strip()
        await database.set_user_plan_prompt(message.from_user.id, new_prompt)
        await message.answer(
            f"✅ **Инструкция для команды `/plan` успешно сохранена!**\n\n"
            f"📋 *Ваш шаблон плана:*\n`{new_prompt}`\n\n"
            f"Теперь отправьте `/plan`, чтобы сгенерировать план по этой схеме.",
            parse_mode="Markdown",
        )
        return

    await state.set_state(PlanStates.waiting_for_plan_prompt)
    await message.answer(
        "📝 **Отправьте текст инструкции (промпта) для генератора плана следующим сообщением:**\n\n"
        "Опишите, как именно бот должен составлять план, на сколько часов разбивать, какие блоки и активности включать.\n"
        "Для отмены отправьте `/cancel`.",
        parse_mode="Markdown",
    )


@router.message(PlanStates.waiting_for_plan_prompt)
async def process_new_plan_prompt(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое описание для плана.")
        return

    new_prompt = message.text.strip()
    await database.set_user_plan_prompt(message.from_user.id, new_prompt)
    await state.clear()

    await message.answer(
        f"✅ **Шаблон для генератора планов сохранен!**\n\n"
        f"📋 *Ваш промпт плана:*\n`{new_prompt}`\n\n"
        f"🚀 Чтобы получить готовый сценарий, отправьте команду `/plan`!",
        parse_mode="Markdown",
    )


@router.message(Command("getplanprompt"))
async def cmd_getplanprompt(message: types.Message):
    plan_prompt = await database.get_user_plan_prompt(message.from_user.id)
    await message.answer(
        f"📅 **Текущий шаблон для команды `/plan`:**\n\n"
        f"`{plan_prompt}`\n\n"
        f"Чтобы изменить шаблон, используйте `/setplanprompt`.",
        parse_mode="Markdown",
    )


# ==========================================
#     НАСТРОЙКИ МОДЕЛИ И РОЛЕЙ
# ==========================================

@router.message(Command("setmodel", "model"))
async def cmd_setmodel(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        current_model = await database.get_user_model(message.from_user.id)
        await message.answer(
            f"🤖 **Текущая модель:** `{current_model}`\n\n"
            f"Чтобы сменить модель, укажите её название:\n"
            f"• `/setmodel meta-llama/llama-3.3-70b-instruct` (Рекомендуется 🔥)\n"
            f"• `/setmodel deepseek/deepseek-chat`\n"
            f"• `/setmodel google/gemini-2.0-flash-001`\n"
            f"• `/setmodel qwen/qwen-2.5-72b-instruct`\n"
            f"• `/setmodel meta-llama/llama-3.1-8b-instruct:free` (Бесплатная)",
            parse_mode="Markdown",
        )
        return

    new_model = args[1].strip()
    await database.set_user_model(message.from_user.id, new_model)
    await message.answer(
        f"✅ **Модель успешно изменена на:**\n`{new_model}` 🚀",
        parse_mode="Markdown",
    )


@router.message(Command("getmodel"))
async def cmd_getmodel(message: types.Message):
    current_model = await database.get_user_model(message.from_user.id)
    await message.answer(f"🤖 **Текущая модель:** `{current_model}`", parse_mode="Markdown")


@router.message(Command("settemp", "temp", "temperature"))
async def cmd_settemp(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current_temp = await database.get_user_temperature(message.from_user.id)
        await message.answer(
            f"🌡️ **Текущая температура:** `{current_temp}`\n\n"
            f"Чтобы изменить, укажите значение от `0.0` до `2.0`:\n"
            f"Пример: `/settemp 0.8`",
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
    await message.answer("❌ Действие отменено.")


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
        "Установлена стандартная роль ассистента, температура 0.8, модель по умолчанию, память очищена.",
        parse_mode="Markdown",
    )


@router.message(F.text)
async def handle_user_query(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text.strip()

    if not user_text:
        return

    # Получаем промпт, температуру, модель и контекст
    system_prompt = await database.get_user_prompt(user_id)
    temperature = await database.get_user_temperature(user_id)
    model = await database.get_user_model(user_id)
    history = await database.get_chat_history(user_id)

    # Отображаем статус «печатает...»
    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        reply_text = await llm_service.generate_response(
            system_prompt=system_prompt,
            history=history,
            user_message=user_text,
            temperature=temperature,
            model=model
        )

    # Сохраняем сообщения в базу данных
    await database.add_message(user_id, "user", user_text)
    await database.add_message(user_id, "assistant", reply_text)

    # Отправляем ответ
    chunks = split_text(reply_text)
    for chunk in chunks:
        await message.answer(chunk)
