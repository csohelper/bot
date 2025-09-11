from python.storage import database


async def init_database_module() -> None:
    pass
    # async with database.get_db_connection() as conn:
    #     async with conn.cursor() as cur:
    #         await cur.execute("""
    #             CREATE TABLE IF NOT EXISTS users (
    #                 id SERIAL PRIMARY KEY,
    #                 user_id INTEGER NOT NULL,
    #                 room INTEGER,
    #                 username TEXT NOT NULL,
    #                 fullname TEXT NOT NULL,
    #                 status TEXT DEFAULT 'waiting'
    #             )
    #         """)
    #         await conn.commit()
