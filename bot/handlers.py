# bot/handlers/moderation.py
from aiogram import Router, types, Bot, F
from aiogram.filters.callback_data import CallbackData

from bot.keyboards import ModerationAction, moderation_keyboard
from core.yt_parser.video_storage import load_json, save_json
from core.llm.chatgpt import generate_post, generate_genre
from core.llm.prompts import generate_post_prompt, generate_genre_prompt
from core.logger import logger
from config import Config

router = Router()
config = Config()
PENDING_POSTS_JSON = config.pending_posts_json

active_post_data = ""


# ------------------ Отображение поста -------------------
async def show_post(bot: Bot, chat_id: int, index: int):
    """Показывает пост для модерации по индексу"""
    posts = load_json(PENDING_POSTS_JSON)

    if not posts or index >= len(posts):
        await bot.send_message(chat_id, "Больше постов для модерации нет ✅")
        return

    post = posts[index]
    caption = (
        # f"<b>{post.get('title', 'Без названия')}</b>\n\n"
        f"{post.get('channel_name', 'Нет текста поста')}\n\n"
        f"{post.get('generated_post', 'Нет текста поста')}\n\n"
        f"<b>Жанр:</b> {post.get('genre', 'Неизвестно')}\n"
        f"<a href='https://youtu.be/{post.get('videoId', '')}'>🎬 Смотреть видео</a>"
    )

    global active_post_data
    active_post_data = (
        "\n\n"
        f"<b>Жанр:</b> {post.get('genre', 'Неизвестно')}\n"
        f"<a href='https://youtu.be/{post.get('videoId', '')}'>🎬 Смотреть видео</a>"
    )

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
    bot = query.bot
    posts = load_json(PENDING_POSTS_JSON)
    index = callback_data.post_index
    chat_id = query.message.chat.id

    if index >= len(posts):
        await query.answer("Пост не найден ❌", show_alert=True)
        return

    post = posts[index]

    if callback_data.action == "approve":
        post["status"] = "approved"
        await query.answer("✅ Пост одобрен")

        # ID канала, куда публикуем
        channel_id = config.groups_by_genre.get(post["genre"])
        try:
            await query.bot.send_photo(
                chat_id=channel_id,  # теперь пост идёт в канал
                photo=post["thumbnail_url"],
                caption=post["generated_post"] + active_post_data,
                parse_mode="HTML",
            )
            logger.info(f"Пост '{post['title']}' опубликован в канал {channel_id}")
        except Exception as e:
            logger.error(f"Ошибка публикации поста '{post['title']}' в канал: {e}")
            await query.bot.send_message(
                query.message.chat.id, f"⚠️ Ошибка публикации: {e}"
            )

    elif callback_data.action == "revise":
        await query.answer("♻️ Генерируется новый вариант...")
        try:
            prompt = generate_post_prompt(post["title"], post["description"])
            post["generated_post"] = await generate_post(prompt)
            post["status"] = "pending"
        except Exception as e:
            logger.error(f"Ошибка при регенерации поста '{post['title']}': {e}")
            await bot.send_message(chat_id, f"⚠️ Ошибка генерации поста: {e}")

    elif callback_data.action == "next":
        await query.answer("⏭ Следующий пост")
        index += 1

    save_json(PENDING_POSTS_JSON, posts)
    await show_post(bot, chat_id, index)


# # ------------------ Команда /moderate -------------------
# @router.message(F.text == "/moderate")
# async def start_moderation(message: types.Message):
#     """Запуск модерации"""
#     bot = message.bot
#     posts = load_json(PENDING_POSTS_JSON)
#     pending_indices = [i for i, p in enumerate(posts) if p.get("status") == "pending"]

#     if not pending_indices:
#         await message.reply("Нет постов для модерации ✅")
#         return

#     await show_post(bot, message.chat.id, pending_indices[0])
