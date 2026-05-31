# scripts/dto.py

class ProductRecord:
    """Хранит данные о товаре: название и уникальный ID."""
    def __init__(self, upc, title):
        self.upc = upc
        self.title = title

    def __str__(self):
        return f"Product(upc={self.upc}, title='{self.title}')"

class StockRecordData:
    """Хранит данные о ценах и остатках."""
    def __init__(self, partner_sku, price, num_in_stock, currency='RUB'):
        self.partner_sku = partner_sku
        self.price = float(price)
        self.num_in_stock = int(num_in_stock)
        self.currency = currency

    def __str__(self):
        return f"Stock(sku={self.partner_sku}, price={self.price}, qty={self.num_in_stock})"
    
class ImageRecord:
    """Хранит данные об изображении товара."""
    def __init__(self, url, caption="", order=0):
        self.url = url  # URL изображения
        self.caption = caption  # Описание изображения
        self.order = order  # Порядок следования (если нужно)

    def __str__(self):
        return f"Image(url='{self.url}', caption='{self.caption}', order={self.order})"