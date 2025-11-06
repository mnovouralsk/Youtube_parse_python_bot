# bot/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

class ModerationAction(CallbackData, prefix="mod"):
    """
    CallbackData для кнопок модерации.
    action: "approve" | "revise" | "next"
    post_index: индекс поста в pending_posts.json
    """
    action: str
    post_index: int


def moderation_keyboard(index: int) -> InlineKeyboardMarkup:
    """
    Создает Inline-кнопки для модерации одного поста.
    :param index: индекс поста
    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=ModerationAction(action="approve", post_index=index).pack()
        ),
        InlineKeyboardButton(
            text="🔄 Предложить варианты",
            callback_data=ModerationAction(action="revise", post_index=index).pack()
        ),
        InlineKeyboardButton(
            text="⏭ Следующий",
            callback_data=ModerationAction(action="next", post_index=index).pack()
        )
    )

    return builder.as_markup()
