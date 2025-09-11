from aiogram import Router
from aiogram.types import ChatJoinRequest

router = Router()

# Обработчик события "подача заявки"
@dp.chat_join_request_handler()
async def join_request(update: ChatJoinRequest):
    user = update.from_user

    # пример логирования
    print(f"Заявка от {user.full_name} (@{user.username})")

    # можно сразу одобрить
    await update.approve()

    # или отклонить:
    # await update.decline()

    # или отправить пользователю сообщение в личку
    try:
        await bot.send_message(user.id, "Спасибо за заявку! Админ рассмотрит её в ближайшее время.")
    except:
        pass