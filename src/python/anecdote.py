import aiohttp
import asyncio
from bs4 import BeautifulSoup
import pymorphy2
import random

# Инициализация анализатора один раз для экономии ресурсов
morph = pymorphy2.MorphAnalyzer()

# Замены
CHARACTER_REPLACEMENTS = ['мэишник', 'мтусишник', 'цсошник', 'общажник']
PLACE_REPLACEMENT = 'МЭИ'

async def download_anekdot():
    url = 'https://www.anekdot.ru/random/anekdot/'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=5) as response:
                response.raise_for_status()
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                text_block = soup.select_one('.text')
                if text_block:
                    # Используем separator='\n' для сохранения переносов строк
                    text = text_block.get_text(separator='\n', strip=True)
                    # Удаляем лишние пустые строки и нормализуем пробелы
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    result = ' '.join(lines)
                    if not (100 < len(result) < 600):
                        return None
                    return result
                return None
    except (aiohttp.ClientError, ValueError) as e:
        print(f"Ошибка при загрузке: {e}")
        return None

def get_main_characters_and_places(text):
    words = text.split()
    char = None
    place = None
    
    for word in words:
        # Пропускаем короткие слова и слова с пунктуацией
        if len(word) < 2 or not word.isalpha():
            continue
        parsed = morph.parse(word)[0]
        base = parsed.normal_form
        
        # Проверяем действующее лицо: первое одушевлённое существительное мужского рода в единственном числе и именительном падеже
        if not char and 'NOUN' in parsed.tag and 'nomn' in parsed.tag and 'anim' in parsed.tag and 'masc' in parsed.tag and 'sing' in parsed.tag:
            char = (base, word, parsed.tag.grammemes)
        
        # Проверяем место: первое неодушевлённое существительное в именительном падеже
        elif not place and 'NOUN' in parsed.tag and 'nomn' in parsed.tag and 'anim' not in parsed.tag:
            place = (base, word, parsed.tag.grammemes)
        
        # Прерываем цикл, если нашли и персонажа, и место
        if char and place:
            break
    
    return char, place

def apply_case(original, replacement):
    """
    Применяет регистр исходного слова к замене.
    """
    if original.isupper():
        return replacement.upper()
    elif original[0].isupper() and len(original) > 1:
        return replacement.capitalize()
    else:
        return replacement.lower()

def replace_characters_and_places(text, char, place):
    if not char:  # Нужно хотя бы одно действующее лицо
        return text, False
    
    base_char_to_replace = char[0] if char else None
    base_place_to_replace = place[0] if place else None
    
    # Разбиваем текст на слова, сохраняя переносы строк
    lines = text.split('\n')
    new_lines = []
    replaced = False
    
    for line in lines:
        words = line.split()
        new_words = []
        
        for word in words:
            parsed = morph.parse(word)[0]
            base = parsed.normal_form
            
            # Замена действующего лица
            if base_char_to_replace and base == base_char_to_replace:
                character_replacement = random.choice(CHARACTER_REPLACEMENTS)
                inflected = morph.parse(character_replacement)[0].inflect(parsed.tag.grammemes)
                replacement = inflected.word if inflected else character_replacement
                replacement = apply_case(word, replacement)
                new_words.append(replacement)
                replaced = True
            
            # # Замена места
            # elif base_place_to_replace and base == base_place_to_replace:
            #     inflected = morph.parse(PLACE_REPLACEMENT)[0].inflect(parsed.tag.grammemes)
            #     replacement = inflected.word if inflected else PLACE_REPLACEMENT
            #     new_words.append(replacement.upper())
            #     replaced = True
            
            else:
                new_words.append(word)
        
        new_lines.append(' '.join(new_words))
    
    return '\n'.join(new_lines), replaced

async def generate_anekdot():
    """
    Асинхронно генерирует один анекдот с заменой действующего лица на 'МЭИшник' и места на 'МЭИ'.
    Возвращает кортеж (оригинал, текст_с_заменой) или (None, None) в случае неудачи.
    """
    text = await download_anekdot()
    if not text:
        return None, None
    
    char, place = get_main_characters_and_places(text)
    if not char:
        return None, None
    
    result, replaced = replace_characters_and_places(text, char, place)
    if not replaced:
        return None, None
    
    return text, result

