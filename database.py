import aiosqlite
from typing import List, Dict, Optional
from config import DB_PATH, DEFAULT_SYSTEM_PROMPT, MAX_HISTORY_MESSAGES, DEFAULT_TEMPERATURE, LLM_MODEL


async def init_db():
    """Инициализация базы данных и создание таблиц."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                system_prompt TEXT NOT NULL,
                temperature REAL DEFAULT 0.8,
                model TEXT DEFAULT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Безопасно добавляем новые колонки при обновлении схемы
        for col_def in [
            "ALTER TABLE users ADD COLUMN temperature REAL DEFAULT 0.8",
            "ALTER TABLE users ADD COLUMN model TEXT DEFAULT NULL",
        ]:
            try:
                await db.execute(col_def)
            except Exception:
                pass

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


async def get_user_prompt(user_id: int) -> str:
    """Получить текущий системный промпт пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT system_prompt FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
            return DEFAULT_SYSTEM_PROMPT


async def get_user_temperature(user_id: int) -> float:
    """Получить текущую температуру генерации пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT temperature FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] is not None:
                return float(row[0])
            return DEFAULT_TEMPERATURE


async def get_user_model(user_id: int) -> str:
    """Получить активную модель пользователя (или дефолтную из настроек)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT model FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
            return LLM_MODEL


async def set_user_prompt(user_id: int, prompt: str) -> None:
    """Установить или обновить системный промпт пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, system_prompt, temperature, model, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                system_prompt = excluded.system_prompt,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, prompt, DEFAULT_TEMPERATURE, LLM_MODEL),
        )
        await db.commit()


async def set_user_temperature(user_id: int, temperature: float) -> None:
    """Установить температуру генерации для пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, system_prompt, temperature, model, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                temperature = excluded.temperature,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, DEFAULT_SYSTEM_PROMPT, temperature, LLM_MODEL),
        )
        await db.commit()


async def set_user_model(user_id: int, model: str) -> None:
    """Установить модель для пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, system_prompt, temperature, model, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                model = excluded.model,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, DEFAULT_SYSTEM_PROMPT, DEFAULT_TEMPERATURE, model),
        )
        await db.commit()


async def reset_user_prompt(user_id: int) -> None:
    """Сбросить настройки пользователя на дефолтные."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, system_prompt, temperature, model, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                system_prompt = excluded.system_prompt,
                temperature = ?,
                model = ?,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, DEFAULT_SYSTEM_PROMPT, DEFAULT_TEMPERATURE, LLM_MODEL, DEFAULT_TEMPERATURE, LLM_MODEL),
        )
        await db.commit()


async def add_message(user_id: int, role: str, content: str) -> None:
    """Добавить сообщение в историю диалога."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        await db.commit()


async def get_chat_history(user_id: int, limit: int = MAX_HISTORY_MESSAGES) -> List[Dict[str, str]]:
    """Получить последние сообщения пользователя для контекста."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT role, content FROM (
                SELECT id, role, content FROM messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
            """,
            (user_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [{"role": row[0], "content": row[1]} for row in rows]


async def clear_chat_history(user_id: int) -> None:
    """Очистить историю сообщений конкретного пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        await db.commit()
