# core/yt_parser/youtube_checker_full.py
import asyncio
from datetime import datetime
from core.logger import logger
from core.yt_parser.ytube_parser import YouTubeParser
from core.llm.prompts import generate_post_prompt, generate_genre_prompt
from core.llm.chatgpt import generate_post, generate_genre
from core.yt_parser.video_storage import load_json, save_json
from config import Config

config = Config()
CHECK_INTERVAL_HOURS = config.check_interval_hours
PENDING_POSTS_JSON = config.pending_posts_json


class YouTubeChecker:
    """Полный цикл проверки YouTube → генерация поста → очередь модерации → публикация"""

    def __init__(self):
        self.parser = YouTubeParser()

    async def check_and_generate_posts(self):
        """Проверка каналов и генерация постов"""
        try:
            new_videos = self.parser.check_for_new_videos()
        except Exception as e:
            logger.error(f"Ошибка при проверке новых видео: {e}", exc_info=True)
            return

        if not new_videos:
            logger.info("Новых видео не найдено.")
            return

        pending_posts = load_json(PENDING_POSTS_JSON)
        if not isinstance(pending_posts, list):
            pending_posts = []

        for video in new_videos:
            try:
                # Генерация текста поста
                post_prompt = generate_post_prompt(video["title"], video["description"])
                genre_prompt = generate_genre_prompt(video["title"], video["description"])

                generated_post = await generate_post(post_prompt)
                genre = await generate_genre(genre_prompt)

                pending_posts.append({
                    "videoId": video["video_id"],
                    "title": video["title"],
                    "description": video["description"],
                    "thumbnail_url": video["thumbnail"],
                    "generated_post": generated_post,
                    "genre": genre,
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat()
                })

                logger.info(f"💾 Пост для видео '{video['title']}' добавлен на модерацию")

            except Exception as llm_error:
                logger.error(f"Ошибка генерации поста для {video['title']}: {llm_error}", exc_info=True)
                continue  # пропускаем проблемное видео

        save_json(PENDING_POSTS_JSON, pending_posts)
        logger.info(f"✅ Всего новых постов на модерацию: {len(new_videos)}")

    async def start_periodic_check(self):
        """Фоновый цикл проверки с интервалом CHECK_INTERVAL_HOURS"""
        while True:
            await self.check_and_generate_posts()
            logger.info(f"⏳ Следующая проверка через {CHECK_INTERVAL_HOURS} часа(ов)...")
            await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
