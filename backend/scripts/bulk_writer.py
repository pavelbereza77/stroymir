# scripts/bulk_writer.py

import logging
import os
from typing import List, Dict, Any
from django.db import transaction
from django.db.utils import IntegrityError
from django.conf import settings
from django.core.files import File
from oscar.apps.catalogue.models import Category, Product, ProductClass, ProductImage
from oscar.apps.partner.models import Partner, StockRecord

from scripts.validators import ProductValidator

# Настройка логгирования
logger = logging.getLogger(__name__)

class BulkDBWriter:
    # Кэшируем сущности на уровне класса
    _partner_cache = None
    _product_class_cache = None

    def __init__(self):
        # Получаем кэшированные сущности
        self.partner = self._get_partner()
        self.product_class = self._get_product_class()
        
        # Списки для товаров
        self.products_to_create = []
        self.products_to_update = []
        self.existing_products_map = {}

        # Списки для стоков
        self.stocks_to_create = []   # Новые записи о ценах
        self.stocks_to_update = []   # Существующие записи, которые нужно обновить
        self.existing_stocks_map = {} # Кэш: {upc: stock_record_object}

    @classmethod
    def _get_partner(cls):
        """Возвращает кэшированную сущность партнёра"""
        if cls._partner_cache is None:
            # Получаем или создаём партнёра один раз
            cls._partner_cache, _ = Partner.objects.get_or_create(name='Основной склад')
        return cls._partner_cache

    @classmethod
    def _get_product_class(cls):
        """Возвращает кэшированную сущность категории товаров"""
        if cls._product_class_cache is None:
            # Получаем или создаём категорию один раз
            cls._product_class_cache, _ = ProductClass.objects.get_or_create(name='Товар')
        return cls._product_class_cache

    def prepare(self, data_generator):
        """
        Подготовительный этап: превращаем генератор в список,
        чтобы сохранить всю существующую функциональность.
        """
        # Преобразуем генератор в список
        data_list = list(data_generator)

        # Теперь работаем с data_list точно так же, как раньше
        if not data_list:
            return

        upcs = [data[0].upc for data in data_list]

        # --- ПОДГОТОВКА ДАННЫХ О ТОВАРАХ ---
        existing_products = Product.objects.filter(upc__in=upcs).only('id', 'upc', 'title', 'is_public')
        self.existing_products_map = {p.upc: p for p in existing_products}

        for product_record, stock_data in data_list:
            is_public = ProductValidator.is_valid_for_publication(product_record, stock_data)

            if product_record.upc in self.existing_products_map:
                prod = self.existing_products_map[product_record.upc]
                prod.title = product_record.title
                prod.is_public = is_public
                self.products_to_update.append(prod)
            else:
                default_image_path = getattr(settings, 'DEFAULT_PRODUCT_IMAGE_PATH', None)
                prod = Product(
                    upc=product_record.upc,
                    title=product_record.title,
                    product_class=self.product_class,
                    is_public=is_public
                )
                prod.default_image_path = default_image_path 
                self.products_to_create.append(prod)

        # --- ПОДГОТОВКА ДАННЫХ О СТОКАХ ---
        # Находим ВСЕ существующие стоки по нашему партнеру и артикулам
        existing_stocks = StockRecord.objects.filter(
            partner=self.partner,
            partner_sku__in=upcs
        ).select_related('product').only('id', 'price', 'num_in_stock', 'product__upc')

        self.existing_stocks_map = {s.product.upc: s for s in existing_stocks}

        for product_record, stock_data in data_list:
            sku = product_record.upc
            price = float(stock_data.price)
            qty = int(stock_data.num_in_stock)

            if sku in self.existing_stocks_map:
                # ЕСЛИ ЗАПИСЬ ЕСТЬ -> готовим к ОБНОВЛЕНИЮ
                stock_rec = self.existing_stocks_map[sku]
                # Проверяем, изменились ли данные, чтобы не делать лишних save()
                if stock_rec.price != price or stock_rec.num_in_stock != qty:
                    stock_rec.price = price
                    stock_rec.num_in_stock = qty
                    self.stocks_to_update.append(stock_rec)
            else:
                # ЕСЛИ ЗАПИСИ НЕТ -> готовим к СОЗДАНИЮ
                # Мы свяжем её с товаром позже, используя карту продуктов
                self.stocks_to_create.append({
                    'product_upc': sku,
                    'price': price,
                    'num_in_stock': qty
                })

    @transaction.atomic
    def commit(self):
        """Выполняет массовую запись в правильном порядке."""
        stats = {
            'products_created': len(self.products_to_create),
            'products_updated': len(self.products_to_update),
            'stocks_created': len(self.stocks_to_create),
            'stocks_updated': len(self.stocks_to_update)
        }

        # Логируем начало этапа
        logger.info("🚀 Этап 1: Работа с товарами...")

        # Пакетная вставка товаров (batch_size=1000)
        if self.products_to_create:
            try:
                products_instances = Product.objects.bulk_create(self.products_to_create, batch_size=1000)
                logger.info(f"✅ Создано новых товаров: {stats['products_created']}")
                
                # Привязываем товары к активной категории "Все товары"
                self._assign_to_active_category(products_instances)

                
                # Загружаем дефолтные изображения
                self._load_default_images(products_instances)

            except IntegrityError as e:
                logger.error(f"Ошибка при создании товаров: {e}")
                raise

        # Массивное обновление товаров
        if self.products_to_update:
            try:
                Product.objects.bulk_update(self.products_to_update, ['title', 'is_public'], batch_size=1000)
                logger.info(f"🔄 Обновлено товаров: {stats['products_updated']}")
            except IntegrityError as e:
                logger.error(f"Ошибка при обновлении товаров: {e}")
                raise

        # Обновляем карту продуктов после создания новых, чтобы получить их ID
        if self.products_to_create:
            new_products = Product.objects.filter(upc__in=[p.upc for p in self.products_to_create]).only('upc', 'id')
            for item in new_products:
                self.existing_products_map[item.upc] = item

        # Логируем начало следующего этапа
        logger.info("\n🚀 Этап 2: Работа с ценами и остатками...")

        # Пакетная обработка стоков
        stocks_batch = []

        # 1. Сначала обрабатываем обновления (UPDATE)
        if self.stocks_to_update:
            try:
                StockRecord.objects.bulk_update(self.stocks_to_update, ['price', 'num_in_stock'], batch_size=1000)
                logger.info(f"💾 Обновлено записей о ценах/остатках: {stats['stocks_updated']}")
            except IntegrityError as e:
                logger.error(f"Ошибка при обновлении стоков: {e}")
                raise

        # 2. Затем создаем новые записи (CREATE)
        for info in self.stocks_to_create:
            product = self.existing_products_map[info['product_upc']]
            stock = StockRecord(
                partner=self.partner,
                price=info['price'],
                num_in_stock=info['num_in_stock'],
                price_currency='RUB',
                partner_sku=info['product_upc'],
                product_id=product.id
            )
            stocks_batch.append(stock)

        # Пакетная вставка стоков (batch_size=1000)
        if stocks_batch:
            try:
                StockRecord.objects.bulk_create(stocks_batch, batch_size=1000)
                logger.info(f"➕ Создано записей о ценах/остатках: {stats['stocks_created']}")
            except IntegrityError as e:
                logger.error(f"Ошибка при создании стоков: {e}")
                raise

        logger.info("🏁 Массовая синхронизация завершена.")
        return stats

    def _load_default_images(self, products_instances):
        """Загружает дефолтные изображения для новых товаров"""
        for product_instance, product_record in zip(products_instances, self.products_to_create):
            if hasattr(product_record, 'default_image_path') and product_record.default_image_path and os.path.exists(product_record.default_image_path):
                # Читаем файл изображения
                with open(product_record.default_image_path, 'rb') as img_file:
                    # Создаем объект изображения
                    image_obj = ProductImage(
                        product=product_instance,
                        original=File(img_file, name='default_image.webp'),
                        caption=f"Дефолтное изображение для {product_record.title}"
                    )
                    
                    # Сохраняем изображение в базе данных
                    image_obj.save()
                    logger.info(f"📸 Загружено дефолтное изображение для товара: {product_record.title}")
            else:
                logger.warning(f"❗ Изображение не найдено для товара: {product_record.title}")
    
    def _assign_to_active_category(self, products_instances):
        """Присваивает товары активной категории 'Все товары'"""
        # Находим или создаём активную категорию "Все товары"
        category_name = 'Все товары'
        category, created = Category.objects.get_or_create(name=category_name)

        # Привязываем товары к категории и сохраняем изменения
        for product_instance in products_instances:
            product_instance.categories.add(category)
            product_instance.save()  # Важно! Сохраняем изменения в базе данных

        logger.info(f"Товары успешно привязаны к категории '{category_name}'")