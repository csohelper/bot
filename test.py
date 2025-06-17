multi_line_text = """<b>Прачка</b>
Вся информация про стиральные машины и их режимы/методы работы: https://mcgrp.ru/files/viewer/321649/9"""

import json
json_safe_string = json.dumps(multi_line_text)
print(json_safe_string) 