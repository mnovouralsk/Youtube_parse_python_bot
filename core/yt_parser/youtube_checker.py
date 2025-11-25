# core/yt_parser/youtube_checker.py
import asyncio
from datetime import datetime, timezone

from core.logger import logger
from core.yt_parser.ytube_parser import YouTubeParser
from core.llm.prompts import generate_post_prompt, generate_genre_prompt
from core.llm.chatgpt import generate_post, generate_genre
from core.yt_parser.video_storage import load_json, save_json
from core.tag_validator import is_only_allowed_tags, clean_html_for_telegram
from config import Config

config = Config()
CHECK_INTERVAL_HOURS = config.check_interval_hours
PENDING_POSTS_JSON = config.pending_posts_json


class YouTubeChecker:
    """Полный цикл проверки YouTube → генерация постов → очередь модерации → публикация"""

    def __init__(self):
        self.parser = YouTubeParser()

    async def check_and_generate_posts(self):
        """Проверка каналов YouTube и генерация постов"""
        posts_added_count = 0

        try:
            new_videos = self.parser.check_for_new_videos()
        except Exception as e:
            logger.error(f"Ошибка при проверке новых видео: {e}", exc_info=True)
            return

        if not new_videos:
            logger.info("Новых видео не найдено.")
            return

        pending_posts = await asyncio.to_thread(load_json, PENDING_POSTS_JSON)
        if not isinstance(pending_posts, list):
            pending_posts = []

        for video in new_videos:
            try:
                posts_added_count += 1

                # Генерация текста поста
                post_prompt = generate_post_prompt(video["title"], video["description"])
                genre_prompt = generate_genre_prompt(
                    video["title"],
                    video["description", f"https://youtu.be/{video['videoId']}"],
                )

                generated_post = await self._regenerate_until_valid(
                    generate_post, post_prompt, 5
                )

                if generated_post is None:
                    logger.error(
                        f"Не удалось сгенерировать пост без запрещённых тегов для видео '{video['title']}'. Пропускаю это видео."
                    )
                    continue

                generated_post = clean_html_for_telegram(generated_post)

                genre = await self._regenerate_until_valid(
                    generate_genre, genre_prompt, 5
                )
                # Проверка на разрешённые теги generated_post
                if genre is not None:
                    genre = clean_html_for_telegram(genre)
                else:
                    genre = ""

                pending_posts.append(
                    {
                        "videoId": video["video_id"],
                        "channel_name": video["channel_name"],
                        "title": video["title"],
                        "description": video["description"],
                        "thumbnail_url": video["thumbnail"],
                        "generated_post": generated_post,
                        "genre": genre,
                        "status": "pending",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

                logger.info(
                    f"💾 Пост для видео '{video['title']}' добавлен на модерацию"
                )

            except Exception as llm_error:
                logger.error(
                    f"Ошибка генерации поста для {video['title']}: {llm_error}",
                    exc_info=True,
                )
                continue

        await asyncio.to_thread(save_json, PENDING_POSTS_JSON, pending_posts)
        logger.info(f"✅ Всего новых постов на модерацию: {posts_added_count}")

    async def start_periodic_check(self):
        """Фоновый цикл периодической проверки"""
        while True:
            await self.check_and_generate_posts()
            logger.info(
                f"⏳ Следующая проверка через {CHECK_INTERVAL_HOURS} часа(ов)..."
            )
            await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)

    async def _regenerate_until_valid(self, prompt_func, prompt, attempts=5):
        """Пытается сгенерировать контент до attempts раз, пока не пройдут проверку тегов."""

        # Первая попытка (внешняя)
        content = await prompt_func(prompt)
        if is_only_allowed_tags(content):
            return content

        # Цикл регенерации
        for i in range(attempts):
            try:
                content = await prompt_func(prompt)
                if is_only_allowed_tags(content):
                    return content
            except Exception as e:
                logger.warning(f"Ошибка LLM при регенерации ({i+1}/{attempts}): {e}")
                await asyncio.sleep(1)

        # Если все попытки провалены, возвращаем None
        logger.error(f"Провал генерации контента после {attempts + 1} попыток.")
        return None
