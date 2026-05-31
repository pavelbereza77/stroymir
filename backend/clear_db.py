# Файл: backend/clear_db.py

import os
import django

def main():
    # Настраиваем Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    from oscar.apps.catalogue.models import Product, Category, ProductCategory
    from oscar.apps.partner.models import StockRecord

    print("--- Очистка базы данных (Товары, Категории, Цены) ---")
    
    try:
        # Удаляем связи товар-категория
        print("Удаление связей товар-категория...")
        ProductCategory.objects.all().delete()
        
        # Удаляем цены и остатки
        print("Удаление цен и остатков...")
        StockRecord.objects.all().delete()
        
        # Удаляем товары
        print("Удаление товаров...")
        Product.objects.all().delete()
        
        # *Опционально*: Удаляем категории, КРОМЕ корневой "Все товары"
        print("Удаление категорий (кроме 'Все товары')...")
        from oscar.apps.catalogue.models import Category
        Category.objects.exclude(name='Все товары').delete()

        print("✅ База данных очищена.")

    except Exception as e:
        print(f"❌ Ошибка при очистке: {e}")

if __name__ == "__main__":
    main()