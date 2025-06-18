import json
from . import config

# Load the JSON file
with open(f'src/res/locale/{config.config.lang}.json', 'r', encoding='utf-8') as f:
    strings = json.load(f)
