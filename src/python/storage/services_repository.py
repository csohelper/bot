from aiogram.dispatcher.middlewares import data
from python.storage import database

async def init_database_module():
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id SERIAL PRIMARY KEY,
                    directory TEXT NOT NULL DEFAULT '/',
                    name TEXT NOT NULL,
                    cost NUMERIC(10, 2) NOT NULL,
                    cost_per TEXT NOT NULL,
                    username TEXT NOT NULL,
                    description TEXT DEFAULT NULL
                )
            """)
            await conn.commit()