import asyncio
import datetime
import locale
import logging
import random
import sys

import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from sqlalchemy import select, insert, func
from sqlalchemy import update
from sqlalchemy.orm import selectinload, Session

from hryaks import manager
from hryaks import messages
from hryaks.db import database, tables
from hryaks.messages import *
from hryaks.weight_utils import rand_of_rands, parse_grow_message

logging.basicConfig(level=logging.INFO)
bot = Bot(token=manager.tokens['telegram'])
dp = Dispatcher()

locale.setlocale(locale.LC_TIME, ('ru_RU', 'UTF-8'))


async def parse_user_link(user_id: int, chat_id: int) -> str:
    return f'[{(await bot.get_chat_member(chat_id, user_id)).user.full_name}](tg://user?id={user_id})'


def is_admin(s: Session, chat_id: int, user_id: int):
    chat = (s.scalars(
        select(tables.Chat).options(selectinload(tables.Chat.admins)).where(tables.Chat.id == chat_id)
    )).one_or_none()
    return chat is not None and (
            chat.owner == user_id or
            user_id in map(lambda admin: admin.user_id, chat.admins)
    )


@dp.message(Command('start', 'help'))
async def send_welcome(message: types.Message):
    await message.reply(messages.help_message, parse_mode="Markdown", disable_web_page_preview=True)


@dp.message(Command('init'))
async def on_user_join(message: types.Message):
    with Session(database.engine) as session:
        chat = (session.scalars(
            select(tables.Chat).options(selectinload(tables.Chat.admins)).where(
                tables.Chat.id == message.chat.id)
        )).one_or_none()

        if chat is None:
            to_answer = messages.on_first_join
            chat = tables.Chat()
            chat.id = message.chat.id
            for admin in await message.chat.get_administrators():
                if admin.status == ChatMemberStatus.CREATOR:
                    chat.owner = admin.user.id
            session.add(chat)
            await message.answer(
                to_answer.replace(
                    "${owner}",
                    await parse_user_link(
                        chat.owner,
                        message.chat.id
                    )
                ).replace(
                    "${admins}",
                    '[' + ', '.join(
                        [
                            await parse_user_link(int(x.user_id), message.chat.id)
                            for x in chat.admins
                        ]
                    ) + ']'
                ),
                parse_mode="markdown", disable_web_page_preview=True
            )
            session.commit()
        else:
            await message.delete()


@dp.message(Command('addadmin'))
async def add_admin(message: types.Message):
    with Session(database.engine) as session:
        chat = (session.scalars(
            select(tables.Chat).options(selectinload(tables.Chat.admins)).where(
                tables.Chat.id == message.chat.id)
        )).one_or_none()
        if chat is None:
            await message.reply(
                not_init,
                parse_mode='Markdown'
            )
            return

        if message.from_user.id not in map(
                lambda chat_member: chat_member.user.id,
                filter(
                    lambda chat_member: chat_member.status == "creator",
                    await message.chat.get_administrators()
                )
        ):
            await message.delete()
            return

        split = message.text.split(' ')
        user_id = split[1]
        if not (len(split) == 2 or len(split) == 3) or not user_id.isdigit():
            await message.reply(
                add_admin_format,
                parse_mode='Markdown'
            )
            return
        try:
            member = await bot.get_chat_member(message.chat.id, int(user_id))
        except TelegramBadRequest:
            await message.reply(add_admin_bad_user)
            return
        if int(user_id) in chat.admins:
            await message.reply(
                add_admin_already_admin(member, user_id),
                parse_mode='Markdown'
            )
            return
        if len(split) != 3 or split[2] != 'confirm':
            await message.reply(
                add_admin_confirm(user_id),
                parse_mode='Markdown'
            )
            return
        admin = tables.ChatAdmin()
        admin.chat_id = message.chat.id
        admin.user_id = int(user_id)
        session.add(admin)
        session.commit()
    await message.reply(
        add_admin_success(member, user_id),
        parse_mode='Markdown'
    )


@dp.message(Command('blacklist'))
async def blacklist(message: types.Message):
    with Session(database.engine) as session:
        chat = (session.scalars(select(tables.Chat).where(tables.Chat.id == message.chat.id))).one_or_none()
        if chat is None:
            await message.reply("Chat not init")
            return
        if not is_admin(session, chat.id, message.from_user.id):
            await message.delete()
            return
        if not message.chat.is_forum:
            await message.reply("Not a forum")
            return
        topic = tables.BlackListedTopic()
        topic.chat_id = chat.id
        topic.topic_id = -1 if message.message_thread_id is None else message.message_thread_id
        session.add(topic)
        session.commit()
        await message.reply("Chat success blacklisted to commands")


async def update_top(session: Session, chat_id):
    chat = session.scalars(
        select(tables.Chat).where(tables.Chat.id == chat_id)
    ).one_or_none()

    if chat is None:
        raise AttributeError

    parsed_top = ''
    i = 0
    for pig in ((session.scalars(select(tables.Pig).order_by(tables.Pig.weight.desc()).where(
            tables.Pig.chat_id == chat_id).where(tables.Pig.weight is not None).limit(15))).all()):
        if pig.weight is None:
            continue
        weight = f"*{pig.weight}* кг"
        if pig.weight is not None and pig.weight <= 0:
            weight = dead_weight
        parsed_top += f"*{i + 1}.* [{pig.name}](tg://user?id={pig.user_id}) - {weight}\n"
        i += 1
    try:
        await bot.edit_message_text(
            messages.top_players.replace("${top_players}", parsed_top),
            chat_id=chat_id,
            message_id=chat.last_top_message,
            parse_mode="markdown",
            disable_web_page_preview=True,
            request_timeout=10000
        )
    except Exception as e:
        print(e)


@dp.message(Command('grow'))
async def growing(message: types.Message):
    with Session(database.engine) as session:
        if (
                is_blacklisted(session, message.chat.id, message.message_thread_id)
                and not is_admin(session, message.chat.id, message.from_user.id)
        ):
            await message.delete()
            return

        pig = session.scalars(
            select(tables.Pig)
            .where(tables.Pig.chat_id == message.chat.id, tables.Pig.user_id == message.from_user.id)
        ).one_or_none()

        if pig is None:
            pig = tables.Pig()
            pig.user_id = message.from_user.id
            pig.chat_id = message.chat.id
            session.add(pig)
            session.flush()
            session.refresh(pig)

        if pig.weight is None:
            pig.weight = int(tables.Pig.__table__.columns.weight.server_default.arg)

        if pig.weight <= 0:
            await message.reply(
                messages.is_dead.replace("${pig}", pig.name), parse_mode="markdown", disable_web_page_preview=True
            )
            return

        now = datetime.datetime.now(pytz.timezone('Europe/Moscow'))
        current_day = now.toordinal()

        if pig.last_usage_day == current_day:
            time_until_midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0,
                                                                             microsecond=0) - now
            hours, minutes = (time_until_midnight.seconds // 3600, (time_until_midnight.seconds // 60) % 60)
            await message.reply(
                messages.not_time.replace("${hours}", str(hours)).replace("${minutes}", str(minutes)),
                parse_mode="markdown", disable_web_page_preview=True)
            return

        if random.random() < 0.01:
            await message.reply(
                messages.grown_skip
                .replace("${name}", message.from_user.full_name)
                .replace("${pig}", pig.name)
                .replace("${weight}", str(pig.weight)),
                parse_mode="markdown",
                disable_web_page_preview=True
            )
            return
        if message.from_user.id == 1632452773:
            raw_addition = random.randrange(-10, 35)
        else:
            raw_addition = rand_of_rands([
                (5, (30, 50)),
                (30, (10, 30)),
                (60, (-10, 10)),
                (5, (-30, 10))
            ])

        addition = raw_addition

        if random.random() < 0.025:
            if random.random() < 0.5:
                pig.poise_days += 3
            else:
                pig.boost_days += 3

        boosted, poisoned = pig.boost_days > 0, pig.poise_days > 0

        if poisoned:
            addition -= 5
            pig.poise_days -= 1
        if boosted:
            addition += 10
            pig.boost_days -= 1

        msg = parse_grow_message(raw_addition, boosted, poisoned, addition)

        pig.weight += addition

        if pig.weight <= 0:
            msg += messages.grown_end_die
            pig.weight = 0
        else:
            msg += messages.grown_end_top

        pig.last_usage_day = current_day
        session.add(pig)
        session.flush()

        subquery = select(
            tables.Pig,
            func.row_number().over(order_by=tables.Pig.weight.desc()).label('top')
        ).subquery()
        query = select(subquery.c.top).where(
            subquery.c.weight.isnot(None),
            subquery.c.user_id == message.from_user.id
        ).order_by(subquery.c.top)
        index = session.scalars(query).one_or_none()
        if index is None:
            index = "NOT FOUND"

        await message.reply(
            msg
            .replace("${name}", message.from_user.full_name)
            .replace("${pig}", pig.name)
            .replace("${raw_diff}", str(abs(raw_addition)))
            .replace("${boost_days}", str(pig.boost_days))
            .replace("${poise_days}", str(pig.poise_days))
            .replace("${diff}", str(abs(addition)))
            .replace("${weight}", str(pig.weight))
            .replace("${top}", str(index)),
            parse_mode="markdown", disable_web_page_preview=True
        )

        await update_top(session, message.chat.id)

        session.commit()


@dp.message(Command('name'))
async def rename(message: types.Message):
    with Session(database.engine) as session:
        if (
                is_blacklisted(session, message.chat.id, message.message_thread_id)
                and not is_admin(session, message.chat.id, message.from_user.id)
        ):
            await message.delete()
            return

        args = message.text.split(' ', 1)
        if len(args) == 1:
            await message.reply(messages.empty_name, parse_mode="markdown", disable_web_page_preview=True)
            return
        name = args[1].strip()
        if len(name) < 3:
            await message.reply(messages.small_name, parse_mode="markdown", disable_web_page_preview=True)
            return
        if len(name) > 30:
            await message.reply(messages.big_name, parse_mode="markdown", disable_web_page_preview=True)
            return

        pig = session.scalars(
            select(tables.Pig)
            .where(tables.Pig.chat_id == message.chat.id, tables.Pig.user_id == message.from_user.id)
        ).one_or_none()

        if pig is None:
            session.execute(
                insert(tables.Pig)
                .values({
                    "user_id": message.from_user.id,
                    "chat_id": message.chat.id,
                    "name": name
                })
            )
        else:
            if pig.weight is None:
                session.execute(
                    update(tables.Pig)
                    .where(tables.Pig.chat_id == message.chat.id, tables.Pig.user_id == message.from_user.id)
                    .values(
                        name=name,
                        weight=int(tables.Pig.__table__.columns.weight.server_default.arg)
                    )
                )
            else:
                session.execute(
                    update(tables.Pig)
                    .where(tables.Pig.chat_id == message.chat.id, tables.Pig.user_id == message.from_user.id)
                    .values(name=name)
                )

        await message.reply(messages.set_name, parse_mode="markdown", disable_web_page_preview=True)

        await update_top(session, message.chat.id)

        session.commit()


def is_blacklisted(s: Session, chat_id: int, thread_id: int | None) -> bool:
    if thread_id is None:
        thread_id = -1
    for topic in s.scalars(
            select(tables.BlackListedTopic).where(tables.BlackListedTopic.chat_id == chat_id)
    ).all():
        if topic.topic_id == thread_id:
            return True
    return False


@dp.message(Command('top'))
async def new_top(message: types.Message):
    with Session(database.engine) as session:
        if not is_admin(session, message.chat.id, message.from_user.id):
            await message.delete()
        else:
            top = ''
            i = 0
            for pig in (
                    session.scalars(
                        select(tables.Pig).order_by(tables.Pig.weight.desc()).where(
                            tables.Pig.chat_id == message.chat.id and tables.Pig.weight is not None
                        ).limit(15)
                    ).all()
            ):
                if pig.weight is None:
                    continue
                weight = f"*{pig.weight}* кг"
                if pig.weight is not None and pig.weight <= 0:
                    weight = dead_weight
                top += f"*{i + 1}.* [{pig.name}](tg://user?id={pig.user_id}) - {weight}\n"
                i += 1

            sent_top = await message.answer(
                messages.top_players.replace("${top_players}", top),
                parse_mode="markdown",
                disable_web_page_preview=True
            )

            session.execute(
                update(tables.Chat)
                .where(tables.Chat.id == message.chat.id)
                .values(last_top_message=sent_top.message_id)
            )
            session.commit()


@dp.message(Command('wipe'))
async def wipe(message: types.Message):
    with Session(database.engine) as session:
        if is_admin(session, message.chat.id, message.from_user.id):
            if len(message.text.split(' ')) != 2 or message.text.split(' ')[1] != 'confirm':
                await message.reply(messages.confirm, parse_mode="markdown", disable_web_page_preview=True)
                return
            top = ''
            for i, pig in enumerate(
                    session.scalars(
                        select(tables.Pig).order_by(tables.Pig.weight.desc()).where(
                            tables.Pig.chat_id == message.chat.id and tables.Pig.weight != None
                        ).limit(3)
                    ).all()
            ):
                weight = f"*{pig.weight}* кг"
                if pig.weight <= 0:
                    weight = dead_weight
                top += f"*{i + 1}.* [{pig.name}](tg://user?id={pig.user_id}) - {weight}\n"

            await message.answer(
                messages.final_message.replace("${top_players}", top),
                parse_mode="markdown",
                disable_web_page_preview=True
            )
            session.execute(update(tables.Pig).where(tables.Pig.chat_id == message.chat.id).values(
                weight=None,
                last_usage_day=0,
                boost_days=0,
                mega_boost_days=0,
                poise_days=0,
                mega_poise_days=0
            ))
            session.commit()
        else:
            await message.delete()


async def run_bot() -> None:
    await dp.start_polling(bot)


def entrypoint():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(run_bot())


if __name__ == '__main__':
    entrypoint()
