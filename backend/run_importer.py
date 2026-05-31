# Файл: backend/run_importer.py

import os
import django
from django.db import transaction

def main():
    """Точка входа для всего процесса импорта."""
    print("=== ЗАПУСК ИМПОРТЕРА КАТАЛОГА ===")
    
    # --- 1. Настройка Django ---
    print("🛠️  Настройка среды Django...")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    try:
        django.setup()
        print("✅ Среда Django настроена.")
    except Exception as e:
        print(f"❌ Критическая ошибка при настройке Django: {e}")
        return

    # --- 2. Импортируем модули ---
    try:
        from scripts.parser_1c import parse_xml_to_dict
        from scripts.db_writer import save_dict_to_db # Этот модуль теперь проще!
    except ImportError as e:
        print(f"❌ Ошибка импорта модулей: {e}")
        return

    # --- 3. Запускаем импорт в одной транзакции ---
    try:
        with transaction.atomic():
            print("\n--- ЭТАП 1+2+3 (Парсинг + Категории + Товары) ---\n")
            
            data_dict = parse_xml_to_dict()
            
            if not data_dict:
                raise RuntimeError("Ошибка на этапе парсинга или нет данных.")
                
            success = save_dict_to_db(data_dict)
            
            if not success:
                raise RuntimeError("Ошибка на этапе записи в БД.")
                
    except Exception as e:
        # Если возникла любая ошибка, транзакция откатится автоматически!
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print("⚠️ Транзакция отменена. В БД не внесено никаких изменений.")
        return

if __name__ == "__main__":
    main()