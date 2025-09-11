from aiogram import Router
from aiogram.types import ChatJoinRequest

from python.main import dp

router = Router()


@dp.chat_join_request()
async def join_request(update: ChatJoinRequest):
    pass
