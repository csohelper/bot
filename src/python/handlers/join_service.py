from aiogram import Router
from aiogram.types import ChatJoinRequest


router = Router()


@router.chat_join_request()
async def join_request(update: ChatJoinRequest):
    pass
