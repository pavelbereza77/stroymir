# scripts/validators.py

from scripts.dto import ProductRecord, StockRecordData

class ProductValidator:
    """
    Содержит бизнес-правила для определения видимости товара.
    Принимает DTO-объекты.
    """
    @staticmethod
    def is_valid_for_publication(product_record: ProductRecord, stock_data: StockRecordData) -> bool:
        if not product_record.title or product_record.title == "Товар без названия":
            return False
        if stock_data.price <= 0 or stock_data.num_in_stock <= 0:
            return False
        return True