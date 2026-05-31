# backend/scripts/utils.py
from oscar.apps.catalogue.categories import create_from_breadcrumbs

class BaseCatalogueInstaller:
    """
    Класс-установщик базовой структуры каталога.
    Реализует логику одиночки (синглтона) на уровне бизнес-логики,
    гарантируя однократное создание базовых категорий.
    """
    _has_run = False  # Флаг класса, чтобы отследить выполнение

    @classmethod
    def install(cls):
        """
        Публичный метод для запуска установки.
        """
        if cls._has_run:
            print("ℹ️ Базовый каталог уже был установлен ранее.")
            return

        print("=== ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ ===\n")
        print("🌳 Установка базового каталога...")
        
        try:
            # Список путей, которые должны существовать
            base_paths = (
                'Все товары',
                'Все товары > Прочее',
            )
            
            created_count = 0
            for path in base_paths:
                category = create_from_breadcrumbs(path)
                if hasattr(category, '_created') and category._created:
                    print(f"   ✅ Создан путь: {path}")
                    created_count += 1
                else:
                    print(f"   ℹ️ Путь уже существует: {path}")

            print("\n--- РЕЗУЛЬТАТ УСТАНОВКИ ---")
            print("Базовая структура каталога успешно установлена.")
            print(f"Новых категорий создано: {created_count}.")

            # Устанавливаем флаг, что установка завершена
            cls._has_run = True

        except Exception as e:
            print(f"\n⚠️ Ошибка при установке базы данных: {e}")