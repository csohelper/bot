from dataclasses import dataclass
from aiogram.dispatcher.middlewares import data
from python.storage import database

async def init_database_module() -> None:
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
                    description TEXT DEFAULT NULL,
                    onwer INTEGER NOT NULL,
                    image TEXT DEFAULT NULL
                )
            """)
            await conn.commit()


@dataclass(frozen=True)
class ServiceItem:
    name: str
    is_folder: bool
    service_id: int | None = None
    folder_dest: str | None = None


async def get_service_list(path: str = "/") -> list[ServiceItem]:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            # Получаем все сервисы, которые находятся в текущем пути
            await cur.execute("""
                SELECT id, name
                FROM services
                WHERE directory = %s
            """, (path,))
            service_rows = await cur.fetchall()

            services = [
                ServiceItem(
                    name=row[1],
                    is_folder=False,
                    service_id=row[0]
                )
                for row in service_rows
            ]

            # Получаем все уникальные подпапки в текущем пути
            await cur.execute("""
                SELECT DISTINCT
                    SUBSTRING(directory FROM LENGTH(%s) + 2 FOR POSITION('/' IN SUBSTRING(directory FROM LENGTH(%s) + 2)) - 1)
                FROM services
                WHERE directory LIKE %s AND directory != %s
            """, (path, path, f"{path}%", path))
            folder_rows = await cur.fetchall()

            folders = []
            for row in folder_rows:
                folder_name = row[0]
                if folder_name:  # фильтруем NULL/пустые
                    folders.append(
                        ServiceItem(
                            name=folder_name,
                            is_folder=True,
                            folder_dest=path.rstrip("/") + "/" + folder_name
                        )
                    )

            return folders + services
        

@dataclass(frozen=True)
class Service:
    id: int
    directory: str
    name: str
    cost: float
    cost_per: str
    username: str
    description: str | None
    onwer: int
    image: str | None


async def find_service(service_id: int) -> Service | None:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT id, directory, name, cost, cost_per, username, description, onwer, image
                FROM services
                WHERE id = %s
            """, (service_id,))
            row = await cur.fetchone()

            if row is None:
                return None

            return Service(
                id=row[0],
                directory=row[1],
                name=row[2],
                cost=float(row[3]),
                cost_per=row[4],
                username=row[5],
                description=row[6],
                onwer=row[7],
                image=row[8]
            )