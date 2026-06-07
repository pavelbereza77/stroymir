# services/validation_service.py

from typing import Tuple
from services.dto import ProductRecord, StockRecordData

# Настройка логгера
import logging
logger = logging.getLogger(__name__)


class ValidationService:
    """
    Сервис для валидации данных перед сохранением в базу.
    """

    def validate(self, product_record: ProductRecord, stock_data: StockRecordData) -> Tuple[bool, str, bool]:
        """
        Валидация данных о товаре и запасах.

        :param product_record: Данные о товаре.
        :param stock_data: Данные о запасах.
        :return: (is_valid, message, is_public) - валидны ли данные, сообщение об ошибке и статус публикации.
        """
        
        # Проверка обязательных полей товара
        if not product_record.upc:
            return False, "Отсутствует UPC товара", False

        if not product_record.title or product_record.title.strip() == "":
            return False, "Отсутствует название товара", False

        # Проверка цены и остатка
        # if stock_data.price is None or stock_data.price == 0:
        #     return False, "Некорректная цена товара", False
        
        if stock_data.price is None or stock_data.price <= 0:
        # Если цена <= 0, товар считается невалидным и скрывается
            return False, "Некорректная цена товара", False

        if stock_data.num_in_stock is None or stock_data.num_in_stock <= 0:
            return False, "Некорректное количество на складе", False
        

        # Если все проверки пройдены, возвращаем True и статус публикации
        return True, "", True



# services/validation_service.py

# from typing import Tuple
# from services.dto import ProductRecord, StockRecordData

# # Настройка логгера
# import logging
# logger = logging.getLogger(__name__)


# class ValidationService:
#     """
#     Сервис для валидации данных перед сохранением в базу.
#     """

#     def validate(self, product_record: ProductRecord, stock_data: StockRecordData) -> Tuple[bool, str]:
#         """
#         Валидация данных о товаре и запасах.

#         :param product_record: Данные о товаре.
#         :param stock_data: Данные о запасах.
#         :return: (is_valid, message) - валидны ли данные и сообщение об ошибке (если есть).
#         """
#         # Проверка обязательных полей товара
#         if not product_record.upc:
#             return False, "Отсутствует UPC товара"

#         if not product_record.title:
#             return False, "Отсутствует название товара"

#         # Проверка цены и остатка
#         if stock_data.price is None or stock_data.price <= 0:
#             stock_data.price = 0  # Устанавливаем цену в 0
#             product_record.is_public = False  # Отключаем публикацию

#         if stock_data.num_in_stock is None or stock_data.num_in_stock < 0:
#             stock_data.num_in_stock = 0  # Устанавливаем остаток в 0
#             product_record.is_public = False  # Отключаем публикацию

#         return True, ""
    
# class ProductValidator:
#     """
#     Содержит бизнес-правила для определения видимости товара.
#     Принимает DTO-объекты.
#     """
#     @staticmethod
#     def is_valid_for_publication(product_record: ProductRecord, stock_data: StockRecordData) -> bool:
#         """
#         Определяет, подходит ли товар для публикации.

#         :return: True, если товар подходит для публикации, False - иначе.
#         """
#         # Проверка обязательных полей товара
#         if not product_record.upc:
#             return False

#         if not product_record.title or product_record.title.strip() == "":
#             return False

#         # Проверка цены и остатка
#         if stock_data.price is None or stock_data.price <= 0:
#             return False

#         if stock_data.num_in_stock is None or stock_data.num_in_stock < 0:
#             return False

#         # Если все проверки пройдены, возвращаем True
#         return True