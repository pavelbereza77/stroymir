# services/dto.py
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class ProductRecord:
    """
    Хранилище данных о товаре.
    """
    upc: str              # Уникальный идентификатор товара
    title: str            # Название товара
    is_public: bool = True    # Статус публикации (по умолчанию True)


@dataclass
class StockRecordData:
    """
    Хранилище данных о запасах.
    """
    product_upc: str      # UPC товара, к которому относится запас
    price: Decimal          # Цена за единицу
    num_in_stock: int     # Количество на складе
    currency: str = 'RUB' # Валюта цены, по умолчанию рубли