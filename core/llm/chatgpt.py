# core/llm/chatgpt.py
import asyncio
import re
from g4f.client import Client
import g4f
from core.logger import logger

def is_russian_text(text: str) -> bool:
    """Проверяет, что в тексте нет китайских иероглифов."""
    return not re.search(r"[\u4e00-\u9fff]", text)

async def get_gpt_response(client: Client, prompt: str) -> str:
    """
    Асинхронно отправляет текст в GPT и проверяет, содержит ли он только русские буквы.
    Делает до 20 попыток.
    """
    max_attempts = 20
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Запрос к GPT, попытка {attempt}...")
            response = client.chat.completions.create(
                model=g4f.models.gpt_4_1_mini,
                provider=g4f.Provider.OIVSCodeSer0501,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )

            result_text = ""
            for message in response:
                if message.choices and message.choices[0].delta:
                    content = message.choices[0].delta.content
                    if content:
                        result_text += content

            result_text = result_text.strip()
            if is_russian_text(result_text):
                logger.info("Ответ GPT содержит только русские буквы.")
                return result_text
            else:
                logger.warning("Ответ GPT содержит нерусские символы, повторяем запрос...")
                await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Ошибка при запросе к GPT: {e}")
            await asyncio.sleep(5)

    logger.error("Не удалось получить корректный ответ от GPT после нескольких попыток.")
    return ""

async def generate_text_with_gpt(prompt: str) -> str:
    """
    Отправляет текст в GPT, разбивая на чанки по 1000 слов.
    Возвращает объединённый результат.
    """
    if not prompt.strip():
        logger.warning("Передан пустой текст для генерации GPT.")
        return ""

    client = Client()
    words = prompt.split()
    chunks = [" ".join(words[i:i + 1000]) for i in range(0, len(words), 1000)]

    tasks = [asyncio.create_task(get_gpt_response(client, chunk)) for chunk in chunks]
    results = await asyncio.gather(*tasks)

    return "\n".join(filter(None, results)).strip()

async def generate_post(prompt: str, retries: int = 3) -> str:
    """Генерация Telegram-поста через g4f с повторными попытками"""
    for attempt in range(1, retries + 1):
        try:
            response = await generate_text_with_gpt(prompt)
            if response:
                return response
        except Exception as e:
            logger.error(f"Ошибка генерации поста (попытка {attempt}): {e}")
        await asyncio.sleep(2)
    return "Ошибка генерации поста."

async def generate_genre(prompt: str, retries: int = 3) -> str:
    """Определение жанра фильма через g4f с повторными попытками"""
    for attempt in range(1, retries + 1):
        try:
            genre = await generate_text_with_gpt(prompt)
            if genre:
                return genre.strip()
        except Exception as e:
            logger.error(f"Ошибка определения жанра (попытка {attempt}): {e}")
        await asyncio.sleep(1)
    return "Unknown"
