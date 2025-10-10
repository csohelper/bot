from mailbox import Message

from python.logger import logger
from python.storage import database


async def init_database_module() -> None:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                CREATE TABLE IF NOT EXISTS hype_forms (
                    id SERIAL PRIMARY KEY,
                    userid BIGINT NOT NULL,
                    username TEXT,
                    phone TEXT,
                    vcard TEXT,
                    fullname TEXT NOT NULL,
                    description TEXT
                );
            """
            logger.debug_db(query)
            await cur.execute(query)
            query = """
                CREATE TABLE IF NOT EXISTS hype_photos (
                    id SERIAL PRIMARY KEY,
                    form_id INT NOT NULL REFERENCES hype_forms(id) ON DELETE CASCADE,
                    media TEXT NOT NULL,
                    mime TEXT NOT NULL
                );
            """
            logger.debug_db(query)
            await cur.execute(query)
            await conn.commit()


async def insert_form(
        userid: int,
        username: str | None,
        phone: str | None,
        vcard: str | None,
        fullname: str,
        photos_b64: list[str],
        photo_mime: str,
        video_b64: str | None,
        video_mime: str | None,
        description: str | None
) -> int:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query_form = """
                INSERT INTO hype_forms (userid, username, phone, vcard, fullname, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            values = (userid, username, phone, vcard, fullname, description)
            logger.debug_db(query_form, values)
            await cur.execute(query_form, values)
            form_id_row = await cur.fetchone()
            form_id = form_id_row[0]

            query_photo = """
                INSERT INTO hype_photos (form_id, media, mime)
                VALUES (%s, %s, %s)
            """
            for photo_b64 in photos_b64:
                values = (form_id, photo_b64, photo_mime)
                logger.debug_db(query_photo, values)
                await cur.execute(query_photo, values)

            if video_b64 and video_mime:
                values = (form_id, video_b64, video_mime)
                logger.debug_db(query_photo, values)
                await cur.execute(query_photo, values)

            await conn.commit()
            return form_id
