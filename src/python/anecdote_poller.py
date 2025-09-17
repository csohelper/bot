import asyncio

import aiohttp
import yaml
from bs4 import BeautifulSoup

from .logger import logger
from .storage.config import config
from .storage.repository import anecdotes_repository
from .storage.repository.anecdotes_repository import AnecdoteItem
from .utils import await_and_run

with open(
        f'src/res/locale/anecdote_prompt.yaml', 'r', encoding='utf-8'
) as f:
    prompt = yaml.safe_load(f)


async def get_anecdote() -> AnecdoteItem:
    return await anecdotes_repository.poll_anecdote()


def parse_payload(original_text: str) -> dict:
    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt[0]['text']
                    }
                ]
            },
            {
                "role": "model",
                "parts": [
                    {
                        "text": prompt[1]['text']
                    }
                ]
            },
            {
                "role": "user",
                "parts": [
                    {
                        "text": original_text
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 1.0,
            "topP": 0.8,
            "topK": 10,
            "thinkingConfig": {
                "thinkingBudget": 0
            }
        }
    }


gemini_url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'


async def process_anecdote(original: str) -> str | None:
    payload: dict = parse_payload(original)
    headers: dict = {
        'x-goog-api-key': config.anecdote.gemini_token,
        'Content-Type': 'application/json'
    }
    for _ in range(10):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(gemini_url, json=payload, headers=headers) as response:
                    if response.status == 429:
                        await asyncio.sleep(5)
                        continue

                    response.raise_for_status()  # Вызовет исключение для статусов 4xx/5xx
                    content = await response.json()
                    logger.debug(f"Anecdote poller: Response content: {content}")  # Log the full content

                    text = content['candidates'][0]['content']['parts'][0]['text']

                    if len(text) < 100:
                        logger.info(
                            f"Anecdote poller: Result text is too small (l={len(text)}). Perhabs proccess error. Input: {original} Output: {text}")
                        return None

                    return text

            except aiohttp.ClientError as e:
                logger.error(f"Anecdote poller: Error process text: {e}")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Anecdote poller: Unknown error process text: {e}")
                await asyncio.sleep(1)
    return None


anecdotes_url = 'https://baneks.ru/random'


async def get_original() -> tuple[int, str] | None:
    for _ in range(10):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(anecdotes_url) as response:
                    response.raise_for_status()

                    # конечный URL после редиректа
                    final_url = str(response.url)
                    # ID — это последняя часть пути
                    anecdote_id = int(final_url.rsplit('/', 1)[-1])

                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Анекдот находится внутри <article><p>
                    anecdote_tag = soup.find('article').find('p')  # type: ignore

                    if anecdote_tag:
                        anekdot_text = anecdote_tag.get_text(strip=True)  # type: ignore
                        return anecdote_id, anekdot_text

            except aiohttp.ClientError as e:
                logger.error(f"Anecdote poller: Error access page: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Anecdote poller: Error loading page: {e}")
                await asyncio.sleep(2)
    return None


async def anecdote_loop_check() -> None:
    logger.debug("Anecdote poller: Check loop")
    need = config.anecdote.buffer_size - (await anecdotes_repository.count_unused_anecdotes())
    if need > 0:
        logger.info(f"Anecdote poller: Need {need} anecdotes, loading")

        i = 0
        while i < need:
            logger.debug(f"Anecdote poller: Proccessing {i}")
            resp = await get_original()
            if resp is None:
                logger.debug("Anecdote poller: Anecdote is None")
                continue
            anecdote_id, original_text = resp
            l = len(original_text)
            if l < 200:
                logger.debug(f"Anecdote poller: Anecdote l={l} is too small")
                continue
            if l > 1000:
                logger.debug(f"Anecdote poller: Anecdote l={l} is too big")
                continue
            processed_text = await process_anecdote(original_text)

            if processed_text is None:
                logger.debug("Anecdote poller: Anecdote is None")
                continue
            else:
                logger.debug(f"Anecdote poller: {original_text}\nProcessed: {processed_text}")
                await anecdotes_repository.insert_anecdote(anecdote_id, original_text, processed_text)

            await asyncio.sleep(5)
            i += 1
        logger.info("Anecdote poller: Load complete")

    asyncio.create_task(await_and_run(config.anecdote.buffer_check_time, anecdote_loop_check))
