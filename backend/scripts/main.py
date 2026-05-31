# scripts/main.py

import os
import sys
import django

def setup_django():
    """Настраивает окружение Django."""
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

def main():
    from parsers import OfferParser
    from bulk_writer import BulkDBWriter

    xml_path = 'import.xml'

    print("=== ЗАПУСК СКРИПТА ИМПОРТА ===\n")

    # 1. Парсим XML
    parser = OfferParser(xml_path)
    parsed_data_list = parser.parse()

    if not parsed_data_list:
        print("❌ Нет данных для обработки.")
        return 

    # 2. Пишем в БД
    writer = BulkDBWriter()
    writer.prepare(parsed_data_list)
    
    # --- ВОТ ГЛАВНАЯ СТРОКА ---
    stats = writer.commit() # Получаем словарь со статистикой

    # 3. Используем полученные данные для финального отчета
    total_processed = stats.get('products_updated', 0) + stats.get('stocks_updated', 0) + stats.get('stocks_created', 0)
    print("\n📊 ФИНАЛЬНЫЙ ОТЧЕТ:")
    print(f"   Обработано записей: {total_processed}")
    print(f"   🆕 Новых товаров создано: {stats.get('products_created', 0)}")
    print(f"   🔄 Существующих товаров обновлено: {stats.get('products_updated', 0)}")
    print(f"   💾 Записей о ценах/остатках обновлено: {stats.get('stocks_updated', 0)}")
    print(f"   ➕ Новых записей о ценах/остатках создано: {stats.get('stocks_created', 0)}")

if __name__ == '__main__':
    setup_django()
    main()