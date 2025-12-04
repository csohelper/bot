from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from python import internet_graph
from python.storage import config
from python.storage.strings import get_string

router = Router()


class InternetChoseHandler(CallbackData, prefix="services.buttons"):
    original: int
    is_total: bool = False
    is_summary: bool = False
    room: str | None = None


@router.message(Command("internet"))
@router.message(lambda message: message.text and message.text.lower() in [
    "интернет", "мегафон", "контора пидорасов"
])
async def command_internet_handler(message: Message) -> None:
    """
    Handler for the /internet command or specific text messages.
    Fetches available rooms and builds an inline keyboard for user selection.

    :param message: The incoming message object.
    """
    rooms = await internet_graph.fetch_rooms()
    builder = InlineKeyboardBuilder()
    for room in rooms:
        builder.row(InlineKeyboardButton(
            text=get_string(message.from_user.language_code, "internet.room", room=room),
            callback_data=InternetChoseHandler(original=message.message_id, room=room).pack()
        ))

    builder.row(InlineKeyboardButton(
        text=get_string(message.from_user.language_code, "internet.total"),
        callback_data=InternetChoseHandler(original=message.message_id, is_total=True).pack()
    ))
    builder.row(InlineKeyboardButton(
        text=get_string(message.from_user.language_code, "internet.summary"),
        callback_data=InternetChoseHandler(original=message.message_id, is_summary=True).pack()
    ))

    await message.reply(
        get_string(
            message.from_user.language_code,
            'internet.choose'
        ),
        reply_markup=builder.as_markup()
    )


@router.callback_query(InternetChoseHandler.filter())
async def on_selected_room(
        callback: CallbackQuery,
        callback_data: InternetChoseHandler
) -> None:
    """
    Callback handler for room selection.
    Deletes the selection message, generates and sends a graph based on the chosen option.

    :param callback: The callback query object.
    :param callback_data: The callback data containing selection details.
    """
    await callback.message.delete()
    await callback.bot.send_chat_action(
        chat_id=callback.message.chat.id,
        action=ChatAction.UPLOAD_PHOTO
    )
    if callback_data.is_summary:
        rooms = ['summary']
    elif callback_data.is_total:
        rooms = ['total']
    else:
        rooms = [callback_data.room]
    graph_bytes = await generate_graph(rooms)
    await callback.bot.send_photo(
        chat_id=callback.message.chat.id,
        reply_to_message_id=callback_data.original,
        photo=BufferedInputFile(
            graph_bytes,
            filename="internet_graph.png"
        )
    )


async def generate_graph(rooms: list[str]) -> bytes:
    """
    :param rooms: List of rooms to generate graph for.
    :return: PNG image bytes of the generated graph.
    """
    start, end = get_time_range(hours_back=config.config.monitoring.back_hours)

    graph_data = await internet_graph.fetch_graph_data(start, end, rooms)

    return await internet_graph.render_graph(
        graph_data,
        config.config.monitoring.back_hours,
        config.config.monitoring.interval_minutes
    )


def get_time_range(hours_back: int):
    """
    :param hours_back: Number of hours back from now to start the time range.
    :return: Tuple of start and end time strings in format "%Y-%m-%d %H:%M".
    """
    msk = ZoneInfo("Europe/Moscow")
    now = datetime.now(msk)

    start_time = now - timedelta(hours=hours_back)
    end_time = now

    return (
        start_time.strftime("%Y-%m-%d %H:%M"),
        end_time.strftime("%Y-%m-%d %H:%M"),
    )
