from dataclasses import dataclass
from typing import Optional

from aiogram.dispatcher.middlewares import data

from python.logger import logger
from python.storage import database


async def init_database_module() -> None:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                CREATE TABLE IF NOT EXISTS services (
                    id SERIAL PRIMARY KEY,
                    directory TEXT NOT NULL DEFAULT '/',
                    name TEXT NOT NULL,
                    cost NUMERIC(10, 2) NOT NULL,
                    cost_per TEXT NOT NULL,
                    description TEXT DEFAULT NULL,
                    owner BIGINT NOT NULL,
                    image TEXT DEFAULT NULL,
                    status TEXT DEFAULT 'moderation'
                )
            """
            logger.debug_db(query)
            await cur.execute(query)
            await conn.commit()


@dataclass(frozen=True)
class ServiceItem:
    name: str
    is_folder: bool
    service_id: int | None = None
    folder_dest: str | None = None
    cost: float | None = None
    cost_per: str | None = None
    owner: int | None = None


async def get_service_list(path: str = "/") -> list[ServiceItem]:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            # Get all services directly in the current path
            query = """
                SELECT id, name, cost, cost_per, owner
                FROM services
                WHERE directory = %s AND status = 'published'
            """
            values = (path,)
            logger.debug_db(query, values)
            await cur.execute(query, values)
            service_rows = await cur.fetchall()

            services = [
                ServiceItem(
                    name=row[1],
                    is_folder=False,
                    service_id=row[0],
                    cost=row[2],
                    cost_per=row[3],
                    owner=row[4]
                )
                for row in service_rows
            ]

            # Construct the LIKE pattern and regex pattern in Python
            # This ensures psycopg handles placeholders correctly and avoids '%' issues
            like_pattern = f"{path}%"  # No need to add '/' if we use `LIKE`
            if path == "/":
                regex_pattern_current_level = r'^/[^/]+(/.*)?$'
            else:
                # Escape path for regex if it contains special characters, though '/' is fine
                escaped_path = path.replace('.', r'\.')  # Example: escape dot if your paths use it
                regex_pattern_current_level = rf'^{escaped_path}/[^/]+(/.*)?$'

            # Get all unique immediate subfolders
            query = """
                SELECT DISTINCT
                    SPLIT_PART(
                        SUBSTRING(s.directory, LENGTH(%s) + CASE WHEN %s = '/' THEN 1 ELSE 2 END),
                        '/',
                        1
                    )
                FROM services s
                WHERE s.directory LIKE %s -- Use the Python-constructed pattern
                  AND s.directory != %s
                  AND s.directory ~ %s -- Use the Python-constructed regex pattern
            """ # Parameters must match placeholders
            values = (path, path, like_pattern, path, regex_pattern_current_level)

            logger.debug_db(query, values)

            await cur.execute(query, values)

            folder_rows = await cur.fetchall()

            folders = []
            for row in folder_rows:
                folder_name = row[0]
                if folder_name:  # Filter NULL/empty
                    # Construct the full path for the subfolder
                    folder_dest = f"{path.rstrip('/')}/{folder_name}" if path != "/" else f"/{folder_name}"
                    folders.append(
                        ServiceItem(
                            name=folder_name,
                            is_folder=True,
                            folder_dest=folder_dest
                        )
                    )

            return folders + services


@dataclass(frozen=True)
class Service:
    id: int | None
    directory: str
    name: str
    cost: float
    cost_per: str
    description: str | None
    owner: int
    image: str | None
    status: str


async def find_service(service_id: int) -> Service | None:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                SELECT id, directory, name, cost, cost_per, description, owner, image, status
                FROM services
                WHERE id = %s
            """
            values = (service_id,)
            logger.debug_db(query, values)
            await cur.execute(query, values)
            row = await cur.fetchone()

            if row is None:
                return None

            return Service(
                id=row[0],
                directory=row[1],
                name=row[2],
                cost=float(row[3]),
                cost_per=row[4],
                description=row[5],
                owner=row[6],
                image=row[7],
                status=row[8],
            )


async def create_service(service: Service) -> int | None:
    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            query = """
                INSERT INTO services (
                    directory, name, cost, cost_per, 
                    description, owner, image, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            values = (
                service.directory,
                service.name,
                service.cost,
                service.cost_per,
                service.description,
                service.owner,
                service.image,
                service.status
            )
            logger.debug_db(query, values)
            await cur.execute(query, values)
            new_id_row = await cur.fetchone()
            await conn.commit()
            return new_id_row[0] if new_id_row else None


ALLOWED_FIELDS = {
    "directory",
    "name",
    "cost",
    "cost_per",
    "description",
    "owner",
    "image",
    "status"
}


async def update_service_fields(service_id: int, **fields) -> Service | None:
    updates = {k: v for k, v in fields.items() if k in ALLOWED_FIELDS}
    if not updates:
        return None

    set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
    values = list(updates.values())
    values.append(service_id)

    query = f"""
        UPDATE services
        SET {set_clause}
        WHERE id = %s
        RETURNING id, directory, name, cost, cost_per,
                  description, owner, image, status
    """
    logger.debug_db(query, values)

    async with database.get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, values)
            row = await cur.fetchone()
            await conn.commit()

            if row:
                return Service(
                    id=row[0],
                    directory=row[1],
                    name=row[2],
                    cost=float(row[3]),
                    cost_per=row[4],
                    description=row[5],
                    owner=row[6],
                    image=row[7],
                    status=row[8]
                )
            return None
