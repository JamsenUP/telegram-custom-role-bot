from typing import List, Dict
from openai import AsyncOpenAI
import config

# Инициализируем клиент OpenAI (или любого совместимого сервиса)
client = AsyncOpenAI(
    api_key=config.OPENAI_API_KEY,
    base_url=config.OPENAI_BASE_URL
)


async def generate_response(
    system_prompt: str,
    history: List[Dict[str, str]],
    user_message: str,
    temperature: float = 0.8
) -> str:
    """Генерация ответа модели на основе системного промпта, истории, сообщения и температуры."""
    if not config.OPENAI_API_KEY:
        return (
            "⚠️ Ошибка: API ключ модели не настроен. "
            "Пожалуйста, укажите `OPENAI_API_KEY` в переменных окружения."
        )

    # Собираем сообщения: Системный промпт + Предыдущая история + Новое сообщение
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        completion = await client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=temperature,
        )
        response_text = completion.choices[0].message.content
        return response_text or "..."
    except Exception as exc:
        return f"⚠️ Произошла ошибка при обращении к языковой модели: {str(exc)}"
