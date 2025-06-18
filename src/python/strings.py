import json
from .config import config

with open(
    f'src/res/locale/{config.lang}.json', 'r', encoding='utf-8'
) as f:
    strings = json.load(f)
