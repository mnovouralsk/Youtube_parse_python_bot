from typing import List, Dict

from aiogram import Router, types, Bot
from aiogram.filters import Command

from bot.keyboards import ModerationAction, moderation_keyboard, moderate_keyboard
from core.yt_parser.video_storage import load_json, save_json
from core.llm.chatgpt import generate_post
from core.llm.prompts import generate_post_prompt
from core.logger import logger
from core.tag_validator import is_only_allowed_tags, clean_html_for_telegram
from config import Config

router = Router()
config = Config()

PENDING_POSTS_JSON = config.pending_posts_json
# Попытаемся взять путь к файлу удалённых ID из конфига, иначе — дефолт
DELETED_VIDEOS_JSON = getattr(config, "deleted_videos_json", "deleted_videos.json")
# Путь к файлу с маппингом жанр -> канал (username или id)
CHANNELS_JSON = getattr(config, "channels_json", None)

# Максимум попыток регенерации чтобы убрать запрещённые теги
MAX_REGEN_ATTEMPTS = 5


# -------------------- вспомогательные функции --------------------
def ensure_deleted_file_format():
    """Убедиться, что файл deleted_videos.json существует и в правильном формате."""
    try:
        data = load_json(DELETED_VIDEOS_JSON)
        if (
            not isinstance(data, dict)
            or "deleted" not in data
            or not isinstance(data["deleted"], list)
        ):
            logger.warning(
                f"{DELETED_VIDEOS_JSON} в неверном формате — сбрасываем в {{'deleted': []}}"
            )
            save_json(DELETED_VIDEOS_JSON, {"deleted": []})
    except Exception:
        # Если файл не существует или повреждён — создаём корректный
        save_json(DELETED_VIDEOS_JSON, {"deleted": []})


def load_deleted_list() -> List[str]:
    """Возвращает список удалённых videoId (строки)."""
    ensure_deleted_file_format()
    data = load_json(DELETED_VIDEOS_JSON)
    deleted = data.get("deleted", []) if isinstance(data, dict) else []
    return deleted


def add_deleted_video(video_id: str):
    """Добавить video_id в deleted_videos.json если ещё нет."""
    ensure_deleted_file_format()
    data = load_json(DELETED_VIDEOS_JSON)
    if not isinstance(data, dict):
        data = {"deleted": []}
    deleted = data.get("deleted", [])
    if video_id not in deleted:
        deleted.append(video_id)
        data["deleted"] = deleted
        save_json(DELETED_VIDEOS_JSON, data)
        logger.info(f"Video {video_id} добавлен в {DELETED_VIDEOS_JSON}")


async def ensure_post_has_only_allowed_tags(post: Dict) -> None:
    """
    Проверка-с циклом: регенерируем post['generated_post'] пока не останутся только <b> и <i>
    Если после MAX_REGEN_ATTEMPTS всё ещё есть некорректные теги — вырезаем их.
    Меняет post in-place.
    """
    text = post.get("generated_post", "") or ""
    if is_only_allowed_tags(text):
        return

    title = post.get("title", "")
    description = post.get("description", "")

    for attempt in range(1, MAX_REGEN_ATTEMPTS + 1):
        try:
            logger.info(
                f"Попытка регенерации ({attempt}/{MAX_REGEN_ATTEMPTS}) для видео {post.get('videoId')}"
            )
            prompt = generate_post_prompt(title, description)
            new_text = await generate_post(prompt)
            if not new_text:
                logger.warning(
                    f"Пустой ответ от LLM при регенерации (попытка {attempt})"
                )
                continue

            post["generated_post"] = new_text
            if is_only_allowed_tags(new_text):
                logger.info(f"Успешно очищено от лишних тегов на попытке {attempt}")
                return
        except Exception as e:
            logger.error(f"Ошибка регенерации на попытке {attempt}: {e}")

    # Если до сих пор есть запрещённые теги — вырезаем их
    cleaned = clean_html_for_telegram(post.get("generated_post", ""))
    post["generated_post"] = cleaned
    logger.warning(
        f"После {MAX_REGEN_ATTEMPTS} попыток — удалены все запрещённые теги для видео {post.get('videoId')}"
    )


# ------------------ Отображение поста -------------------
async def show_post(bot: Bot, chat_id: int, index: int):
    """Показывает пост для модерации по индексу"""
    posts = load_json(PENDING_POSTS_JSON)
    if not isinstance(posts, list):
        logger.warning(
            f"{PENDING_POSTS_JSON} ожидается список, но получен другой тип — сбрасываем."
        )
        posts = []

    if not posts or index >= len(posts):
        await bot.send_message(chat_id, "Больше постов для модерации нет ✅")
        return

    post = posts[index]

    caption = (
        f"<b>{post.get('channel_name', post.get('title', 'Без названия'))}</b>\n\n"
        f"{post.get('generated_post', 'Нет текста поста')}\n\n"
        f"<b>Жанр:</b> {post.get('genre', 'Неизвестно')}\n"
        f"<a href='https://youtu.be/{post.get('videoId', '')}'>🎬 Смотреть видео</a>"
    )

    # Сохраняем часть данных отдельно (если нужно для публикации)
    # но не используем глобальные переменные без необходимости

    try:
        await bot.send_photo(
            chat_id=chat_id,
            photo=post.get("thumbnail_url", ""),
            caption=caption,
            parse_mode="HTML",
            reply_markup=moderation_keyboard(index),
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке поста '{post.get('title')}': {e}")
        # fallback — отправляем текст
        await bot.send_message(
            chat_id,
            f"⚠️ Не удалось отправить фото. Вот сам пост:\n\n{caption}",
            parse_mode="HTML",
            reply_markup=moderation_keyboard(index),
        )


# ------------------ Callback Handler -------------------
@router.callback_query(ModerationAction.filter())
async def handle_callback(query: types.CallbackQuery, callback_data: ModerationAction):
    """Обработка действий модератора"""
    bot: Bot = query.bot
    posts = load_json(PENDING_POSTS_JSON)
    if not isinstance(posts, list):
        posts = []

    index = callback_data.post_index
    chat_id = query.message.chat.id

    if index >= len(posts):
        await query.answer("Пост не найден ❌", show_alert=True)
        return

    post = posts[index]

    # --- Одобрение ---
    if callback_data.action == "approve":
        # Перед публикацией убедимся, что в посте нет запрещённых тегов:
        try:
            await ensure_post_has_only_allowed_tags(post)
        except Exception as e:
            logger.error(f"Ошибка при проверке тегов перед публикацией: {e}")

        post["status"] = "approved"
        await query.answer("✅ Пост одобрен")

        target_channel = config.channel_id
        if not target_channel:
            logger.error(
                "Канал для жанра не найден; использование chat модерации в качестве fallback."
            )
            target_channel = chat_id

        try:
            await bot.send_photo(
                chat_id=target_channel,
                photo=post.get("thumbnail_url", ""),
                caption=f"<b>{post.get('channel_name', '')}</b>\n\n{post.get('generated_post', '')}\n\n"
                f"<b>Жанр:</b> {post.get('genre', 'Неизвестно')}\n"
                f"<a href='https://youtu.be/{post.get('videoId', '')}'>🎬 Смотреть видео</a>",
                parse_mode="HTML",
            )
            logger.info(f"Пост '{post.get('title')}' опубликован в {target_channel}")
        except Exception as e:
            logger.error(
                f"Ошибка публикации поста '{post.get('title')}' в {target_channel}: {e}"
            )
            await bot.send_message(chat_id, f"⚠️ Ошибка публикации: {e}")

    # --- Перегенерация ---
    elif callback_data.action == "revise":
        await query.answer("♻️ Генерируется новый вариант...")
        try:
            prompt = generate_post_prompt(
                post.get("title", ""), post.get("description", "")
            )
            new_text = await generate_post(prompt)
            post["generated_post"] = new_text or post.get("generated_post", "")
            post["status"] = "pending"

            # Применяем проверку тегов после регенерации
            await ensure_post_has_only_allowed_tags(post)
            await query.message.reply("Новый вариант сгенерирован и проверен.")
        except Exception as e:
            logger.error(f"Ошибка при регенерации поста '{post.get('title')}': {e}")
            await bot.send_message(chat_id, f"⚠️ Ошибка генерации поста: {e}")

    # --- Удаление ---
    elif callback_data.action == "delete":
        # Добавляем videoId в список удалённых, чтобы никогда не возвращаться к нему
        vid = post.get("videoId")
        if vid:
            try:
                add_deleted_video(vid)
            except Exception as e:
                logger.error(f"Не удалось пометить видео {vid} как удалённое: {e}")

        # Удаляем сам пост из списка
        try:
            posts.pop(index)
            save_json(PENDING_POSTS_JSON, posts)
            await query.answer("🗑 Пост удалён")
        except Exception as e:
            logger.error(f"Ошибка при удалении поста index={index}: {e}")
            await query.answer("⚠️ Не удалось удалить пост", show_alert=True)
            return

        # Показываем следующий пост (тот же индекс теперь указывает на следующий элемент)
        if index < len(posts):
            await show_post(bot, chat_id, index)
        else:
            await bot.send_message(chat_id, "Постов больше нет для модерации ✅")
        return

    # --- Следующий пост ---
    elif callback_data.action == "next":
        await query.answer("⏭ Следующий пост")
        index += 1

    # Сохраняем изменения (approve/revise/next)
    save_json(PENDING_POSTS_JSON, posts)
    # Показываем (возможно обновлённый) пост
    await show_post(bot, chat_id, index)


# ------------------ Команда /moderate -------------------
@router.message(Command("moderate"))
async def cmd_moderate(message: types.Message):
    """Запуск модерации"""
    bot: Bot = message.bot
    posts = load_json(PENDING_POSTS_JSON)
    if not isinstance(posts, list):
        posts = []

    pending_indices = [i for i, p in enumerate(posts) if p.get("status") == "pending"]
    if not pending_indices:
        await message.reply("Нет постов для модерации ✅")
        return

    await show_post(bot, message.chat.id, pending_indices[0])


# ------------------ Команда /start ------------------
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Приветствие и показ кнопки /moderate только модераторам"""
    user_id = message.from_user.id
    if user_id in config.moderator_chat_id:
        await message.answer(
            "Привет! Для запуска модерации нажмите кнопку ниже:",
            reply_markup=moderate_keyboard,
        )
    else:
        await message.answer("Привет! У вас нет доступа к модерации.")
