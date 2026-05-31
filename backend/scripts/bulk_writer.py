# scripts/bulk_writer.py - ФИНАЛЬНАЯ ВЕРСИЯ

from django.db import transaction
from oscar.apps.catalogue.models import Product, ProductClass
from oscar.apps.partner.models import Partner, StockRecord

from scripts.validators import ProductValidator


class BulkDBWriter:
    """
    Оптимизированный писатель, который корректно работает как на CREATE,
    так и на UPDATE, решая проблему связи OneToMany.
    """
    def __init__(self):
        self.partner, _ = Partner.objects.get_or_create(name='Основной склад')
        self.product_class, _ = ProductClass.objects.get_or_create(name='Товар')
        
        # Списки для товаров
        self.products_to_create = []
        self.products_to_update = []
        self.existing_products_map = {}

        # Списки для стоков
        self.stocks_to_create = []   # Новые записи о ценах
        self.stocks_to_update = []   # Существующие записи, которые нужно обновить
        self.existing_stocks_map = {} # Кэш: {upc: stock_record_object}

    def prepare(self, data_list):
        """Готовит данные для записи."""
        print("🗃️ Подготовка данных для массовой записи...")

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
                prod = Product(
                    upc=product_record.upc,
                    title=product_record.title,
                    product_class=self.product_class,
                    is_public=is_public
                )
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

        print("\n🚀 Этап 1: Работа с товарами...")
        if self.products_to_create:
            Product.objects.bulk_create(self.products_to_create)
            print(f"✅ Создано новых товаров: {stats['products_created']}")
        
        if self.products_to_update:
            Product.objects.bulk_update(self.products_to_update, ['title', 'is_public'])
            print(f"🔄 Обновлено товаров: {stats['products_updated']}")

        # Обновляем карту продуктов после создания новых, чтобы получить их ID
        if self.products_to_create:
            new_products = Product.objects.filter(upc__in=[p.upc for p in self.products_to_create]).only('upc', 'id')
            for item in new_products:
                self.existing_products_map[item.upc] = item

        print("\n🚀 Этап 2: Работа с ценами и остатками...")
        stocks_batch = []

        # 1. Сначала обрабатываем обновления (UPDATE)
        if self.stocks_to_update:
            StockRecord.objects.bulk_update(self.stocks_to_update, ['price', 'num_in_stock'])
            print(f"💾 Обновлено записей о ценах/остатках: {stats['stocks_updated']}")

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

        if stocks_batch:
            StockRecord.objects.bulk_create(stocks_batch)
            print(f"➕ Создано записей о ценах/остатках: {stats['stocks_created']}")

        print("🏁 Массовая синхронизация завершена.")
        return stats