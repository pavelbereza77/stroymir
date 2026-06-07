# services/db_service.py

import os
from typing import List, Set, Tuple
from django.db import transaction
from django.core.files import File
from django.conf import settings
from services.default_entities_manager import DefaultEntitiesManager  # Импортируем менеджер

# Импортируем модели Django Oscar
from oscar.apps.catalogue.models import (
    Product, ProductClass, ProductImage
)
from oscar.apps.partner.models import Partner, StockRecord

# Импортируем наши DTO-классы
from services.dto import ProductRecord, StockRecordData

# Настройка логгера
import logging
logger = logging.getLogger(__name__)


class DbService:
    """
    Сервис для управления операциями с базой данных.
    """

    def __init__(self, partner: Partner, product_class: ProductClass):
        """
        Инициализация сервиса.

        :param partner: Поставщик (партнер), от имени которого ведутся операции.
        :param product_class: Класс товара (например, "Строительные материалы").
        """
        self.partner = partner
        self.product_class = product_class

        # Подготовим кэш существующих товаров и запасов для оптимизации
        self._load_existing_entities()

    def _load_existing_entities(self):
        """
        Внутренний метод для предварительной загрузки сущностей из БД.
        Это ускоряет последующие операции, позволяя проверять существование товаров и запасов без запросов.
        """
        # Кэш продуктов по UPC
        self.existing_products_map = {
            p.upc: p for p in Product.objects.filter(upc__isnull=False)
        }

        # Кэш запасов по UPC продукта
        self.existing_stocks_map = {
            sr.product.upc: sr for sr in StockRecord.objects.select_related('product').all()
        }

    
    def _process_new_products(self, products_instances: List[Product]):
        """
        Обрабатывает новые товары: привязывает к категории и прикрепляет изображение.
        """
        # Получаем корневую категорию через менеджер
        root_category = DefaultEntitiesManager.get_root_category()

        # Получаем путь к дефолтному изображению из настроек
        default_image_path = settings.DEFAULT_PRODUCT_IMAGE_PATH

        # Открываем файл изображения
        with open(default_image_path, 'rb') as img_file:
            # Обрабатываем каждый новый товар
            for product in products_instances:
                # Привязываем товар к категории
                product.categories.add(root_category)

                # Прикрепляем дефолтное изображение
                image_obj = ProductImage(
                    product=product,
                    display_order=0,
                    caption=f"Дефолтное изображение для {product.title}",
                    original=File(img_file, name=os.path.basename(default_image_path))
                )
                image_obj.save()

                # Сохраняем изменения в базе данных
                product.save()

        logger.info("Товары успешно обработаны: привязаны к категории и добавлено изображение")
        
    def _process_upc_sets(self, current_upcs: Set[str], all_upcs: Set[str]) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Обрабатывает два множества UPC и возвращает наборы данных для разных сценариев.

        :param current_upcs: UPC товаров из нового XML-файла.
        :param all_upcs: UPC всех товаров в базе данных.
        :return: (matching_upcs, missing_upcs, new_upcs)
        """
        # Совпадающие UPC (есть и в базе, и в новом файле)
        matching_upcs = current_upcs.intersection(all_upcs)

        # Отсутствующие UPC (есть в базе, но отсутствуют в новом файле)
        missing_upcs = all_upcs.difference(current_upcs)

        # Новые UPC (есть в новом файле, но отсутствуют в базе)
        new_upcs = current_upcs.difference(all_upcs)

        return matching_upcs, missing_upcs, new_upcs
    
    def _prepare_new_products(self, new_upcs: Set[str], data_list: List[Tuple[ProductRecord, StockRecordData]]) -> Tuple[List[Product], List[StockRecord]]:
        """
        Подготавливает данные для создания новых товаров.

        :param new_upcs: Mножество UPC новых товаров.
        :param data_list: Список валидных данных о товарах и запасах.
        :return: (products_to_create, stocks_to_create) - списки объектов для создания.
        """
        products_to_create = []
        stocks_to_create = []

        # Находим все предложения из data_list, чьи UPC входят в new_upcs
        for product_rec, stock_rec in data_list:
            if product_rec.upc in new_upcs:
                # Создаем новый товар
                new_product = Product(
                    structure=Product.STANDALONE,
                    upc=product_rec.upc,
                    title=product_rec.title,
                    product_class=self.product_class,
                    is_discountable=True,
                    is_public=product_rec.is_public,
                )
                products_to_create.append(new_product)

                # Создаем временный StockRecord для нового товара
                new_stock = StockRecord(
                    product=new_product,
                    partner=self.partner,
                    partner_sku=product_rec.upc,
                    price=stock_rec.price,
                    num_in_stock=stock_rec.num_in_stock
                )
                stocks_to_create.append(new_stock)

        return products_to_create, stocks_to_create
    
    def _process_missing_products(self, missing_upcs: Set[str]) -> Tuple[List[Product], List[StockRecord]]:
        """
        Обрабатывает товары, которые отсутствуют в новом XML-файле.

        Для каждого товара:
        - Устанавливает остаток в 0.
        - Скрывает товар от публикации (is_public=False).

        :param missing_upcs: Mножество UPC отсутствующих товаров.
        :return: (products_to_update, stocks_to_update) - списки объектов для массового обновления.
        """
        products_to_update = []
        stocks_to_update = []

        # Находим все товары с такими UPC
        for upc in missing_upcs:
            product = self.existing_products_map.get(upc)
            if product:
                # Скрываем товар от публикации
                product.is_public = False
                products_to_update.append(product)

                # Находим все запасы этого товара
                for stock in product.stockrecords.all():
                    # Устанавливаем остаток в 0
                    stock.num_in_stock = 0
                    stocks_to_update.append(stock)

        return products_to_update, stocks_to_update
    
    def _process_matching_products(self, matching_upcs: Set[str], data_list: List[Tuple[ProductRecord, StockRecordData]]) -> Tuple[List[Product], List[StockRecord]]:
        """
        Обрабатывает товары, которые есть и в базе данных, и в новом XML-файле.

        Для каждого товара проверяет, есть ли изменения в данных, и готовит списки для обновления.

        :param matching_upcs: Mножество UPC существующих товаров.
        :param data_list: Список валидных данных о товарах и запасах.
        :return: (products_to_update, stocks_to_update) - списки объектов для массового обновления.
        """
        products_to_update = []
        stocks_to_update = []

        # Находим все предложения из data_list, чьи UPC входят в matching_upcs
        for product_rec, stock_rec in data_list:
            if product_rec.upc in matching_upcs:
                existing_product = self.existing_products_map.get(product_rec.upc)
                existing_stock = self.existing_stocks_map.get(product_rec.upc)

                if existing_product and existing_stock:
                    # Проверяем, есть ли изменения
                    if (existing_product.title != product_rec.title or
                        existing_product.is_public != product_rec.is_public or
                        existing_stock.price != stock_rec.price or
                        existing_stock.num_in_stock != stock_rec.num_in_stock):
                        # Готовим товар к обновлению
                        existing_product.title = product_rec.title
                        existing_product.is_public = product_rec.is_public
                        products_to_update.append(existing_product)

                        # Готовим запас к обновлению
                        existing_stock.price = stock_rec.price
                        existing_stock.num_in_stock = stock_rec.num_in_stock
                        stocks_to_update.append(existing_stock)

        return products_to_update, stocks_to_update
    
    @transaction.atomic
    def process(self, data_list: List[Tuple[ProductRecord, StockRecordData]]) -> dict:
        # Получаем множество UPC из нового XML-файла
        current_upcs = {rec.upc for rec, _ in data_list}

        # Получаем множество UPC всех товаров в базе данных
        all_upcs = set(self.existing_products_map.keys())

        # Обрабатываем множества UPC
        matching_upcs, missing_upcs, new_upcs = self._process_upc_sets(current_upcs, all_upcs)

        # Этап 0: Синхронизация отсутствующих товаров
        # Находим товары, которые есть в базе, но отсутствуют в новом файле
        products_to_update_hidden, stocks_to_update_hidden = self._process_missing_products(missing_upcs)

        # Массовое обновление статуса публикации для скрытых товаров
        Product.objects.bulk_update(products_to_update_hidden, fields=["is_public"])

        # Массовое обновление остатков для скрытых товаров
        StockRecord.objects.bulk_update(stocks_to_update_hidden, fields=["num_in_stock"])

        # Этап 1: Обработка новых товаров
        # Подготавливаем данные для создания новых товаров
        products_to_create, stocks_to_create = self._prepare_new_products(new_upcs, data_list)

        # Массовые операции с товарами и запасами
        created_products = Product.objects.bulk_create(products_to_create)
        created_stocks = StockRecord.objects.bulk_create(stocks_to_create)

        # Обрабатываем новые товары: привязываем к категории и добавляем изображение
        self._process_new_products(created_products)

        # Этап 2: Обработка существующих товаров
        # Подготавливаем данные для обновления существующих товаров
        products_to_update_existing, stocks_to_update_existing = self._process_matching_products(matching_upcs, data_list)

        # Обновляем существующие товары и запасы
        Product.objects.bulk_update(products_to_update_existing, fields=["title", "is_public"])

        # ВНИМАНИЕ: Убираем избыточный код
        # StockRecord.objects.bulk_update(updated_stocks, fields=["price", "num_in_stock"])

        # Используем список, который вернулся из метода _process_matching_products
        StockRecord.objects.bulk_update(stocks_to_update_existing, fields=["price", "num_in_stock"])

        # Формируем итоговую статистику
        result = {
            "created_products": len(created_products),
            "updated_products": len(products_to_update_hidden) + len(products_to_update_existing),
            "created_stocks": len(created_stocks),
            "updated_stocks": len(stocks_to_update_hidden) + len(stocks_to_update_existing),
            "hidden_products": len(missing_upcs),  # Статистика по скрытым товарам
        }

        logger.info("Операция завершена: %s", result)
        return result