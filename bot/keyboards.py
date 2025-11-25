from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData


class ModerationAction(CallbackData, prefix="mod"):
    """
    CallbackData для кнопок модерации.
    action: "approve" | "revise" | "next" | "delete" | "finish"
    post_index: индекс поста в pending_posts.json
    """

    action: str
    post_index: int


def moderation_keyboard(index: int, total_posts: int) -> InlineKeyboardMarkup:
    """
    Создает Inline-кнопки для модерации одного поста.
    :param index: индекс текущего поста (начиная с 0)
    :param total_posts: общее количество постов в очереди
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=ModerationAction(action="approve", post_index=index).pack(),
        ),
        InlineKeyboardButton(
            text="🔄 Предложить варианты",
            callback_data=ModerationAction(action="revise", post_index=index).pack(),
        ),
    )

    # --- Динамическая строка навигации ---
    if index < total_posts - 1:
        # Если есть следующий пост, показываем "Следующий"
        next_button = InlineKeyboardButton(
            text="⏭ Следующий",
            callback_data=ModerationAction(
                action="next", post_index=index + 1
            ).pack(),  # <--- Используем index + 1
        )
    else:
        # Если это последний пост, показываем "Завершить" или "В начало"
        next_button = InlineKeyboardButton(
            text="🏁 Завершить модерацию",
            callback_data=ModerationAction(action="finish", post_index=index).pack(),
        )

    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=ModerationAction(action="delete", post_index=index).pack(),
        ),
        next_button,  # Используем динамическую кнопку
    )
    return builder.as_markup()


# ------------------ Клавиатура для запуска модерации ------------------
moderate_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="/moderate")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)
