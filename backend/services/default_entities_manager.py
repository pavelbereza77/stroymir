# services/default_entities_manager.py

from typing import Optional
# from django.db.models import Model
from oscar.apps.partner.models import Partner
from oscar.apps.catalogue.models import ProductClass, Category

# Настройка логгера
import logging
logger = logging.getLogger(__name__)


class DefaultEntitiesManager:
    """
    Менеджер для управления одиночными сущностями (Singleton).
    Гарантирует, что партнёр и класс товара создаются только один раз.
    """

    _partner: Optional[Partner] = None
    _product_class: Optional[ProductClass] = None

    @classmethod
    def get_partner(cls) -> Partner:
        """
        Возвращает или создаёт партнёра "Строймир".
        """
        if cls._partner is None:
            cls._partner = Partner.objects.get_or_create(name="Строймир")[0]
            logger.info("Партнёр 'Строймир' получен или создан.")
        return cls._partner

    @classmethod
    def get_product_class(cls) -> ProductClass:
        """
        Возвращает или создаёт класс товара "Товар".
        """
        if cls._product_class is None:
            cls._product_class = ProductClass.objects.get_or_create(name="Товар")[0]
            logger.info("Класс товара 'Товар' получен или создан.")
        return cls._product_class
    
    @classmethod
    def get_root_category(cls) -> Category:
        """
        Возвращает или создаёт корневую категорию "Все товары".
        """
        root_category, created = Category.objects.get_or_create(
            path="0001", defaults={"depth": 1, "name": "Все товары"}
        )
        if created:
            logger.info("Корневая категория 'Все товары' создана.")
        return root_category