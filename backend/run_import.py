# run_import.py

import os
import sys
import logging
# Настраиваем Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
# Импортируем координатор импорта
from coordinator.import_coordinator import ImportCoordinator

# Абсолютный путь к корню проекта
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, PROJECT_ROOT)

# Настраиваем логирование
logging.basicConfig(level=logging.DEBUG)





# Путь к XML-файлу
xml_path = "import.xml"

# Создаем координатор и запускаем импорт
coordinator = ImportCoordinator(xml_path)
result = coordinator.run_import()

print(result)