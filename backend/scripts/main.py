# scripts/main.py
#!/usr/bin/env python3
"""
Главный скрипт для импорта данных из XML в Django Oscar.
Параметры запуска:
  --xml-path=<путь_к_xml>  - обязательный параметр, путь к XML-файлу
"""

import os
import sys
import argparse
import logging
import django

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger(__name__)

def setup_django():
    """Настраивает окружение Django."""
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

def main():
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description="Импорт данных из XML в Django Oscar")
    parser.add_argument("--xml-path", required=True, help="Путь к XML-файлу")
    args = parser.parse_args()

    xml_path = args.xml_path

    # Начало логирования процесса
    logger.info("Начало импорта данных")
    logger.info(f"Параметры запуска: XML-путь={xml_path}")

    # Импортируем необходимые классы после настройки Django
    from scripts.parsers import OfferParser
    from scripts.bulk_writer import BulkDBWriter

    # 1. Парсинг XML
    parser = OfferParser(xml_path)
    parsed_data_list = parser.parse()

    if not parsed_data_list:
        logger.warning("Нет данных для обработки.")
        return

    # 2. Пишем в БД
    writer = BulkDBWriter()
    writer.prepare(parsed_data_list)
    
    # --- ВОТ ГЛАВНАЯ СТРОКА ---
    stats = writer.commit() # Получаем словарь со статистикой

    # 3. Используем полученные данные для финального отчета
    total_processed = stats.get('products_created', 0) + \
                      stats.get('products_updated', 0) + \
                      stats.get('stocks_updated', 0) + \
                      stats.get('stocks_created', 0)

    logger.info("\n📊 ФИНАЛЬНЫЙ ОТЧЕТ:")
    logger.info(f"   Обработано записей: {total_processed}")
    logger.info(f"   🆕 Новых товаров создано: {stats.get('products_created', 0)}")
    logger.info(f"   🔄 Существующих товаров обновлено: {stats.get('products_updated', 0)}")
    logger.info(f"   💾 Записей о ценах/остатках обновлено: {stats.get('stocks_updated', 0)}")
    logger.info(f"   ➕ Новых записей о ценах/остатках создано: {stats.get('stocks_created', 0)}")

    logger.info("Импорт данных завершен")

if __name__ == '__main__':
    setup_django()
    main()