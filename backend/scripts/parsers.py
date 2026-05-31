# scripts/parsers.py

import xml.etree.ElementTree as ET
from scripts.dto import ProductRecord, StockRecordData

class ProductDataBuilder:
    """Строитель, который собирает объекты из одного элемента <Предложение>."""
    def __init__(self, offer_element):
        self.offer = offer_element

    def get_upc(self):
        link = self.offer.find('СсылкаНаТовар')
        return link.get('ИдентификаторВКаталоге') if link is not None else None

    def get_title(self):
        for prop in self.offer.findall('ЗначениеСвойства'):
            if prop.get('ИдентификаторСвойства') == 'ПолноеНаименование':
                return prop.get('Значение')
        return "Товар без названия"

    def get_price(self):
        return self.offer.get('Цена', '0')

    def get_quantity(self):
        return self.offer.get('Количество', '0')

    def build(self):
        """Собирает и возвращает готовые объекты данных."""
        upc = self.get_upc()
        if not upc:
            return None, None # Пропускаем, если нет ID

        product_record = ProductRecord(upc=upc, title=self.get_title())
        stock_data = StockRecordData(
            partner_sku=upc,
            price=self.get_price(),
            num_in_stock=self.get_quantity()
        )
        return product_record, stock_data


class OfferParser:
    """Фабрика, которая управляет процессом парсинга всего файла."""
    def __init__(self, xml_path):
        self.xml_path = xml_path

    def parse(self):
        """
        Парсит файл и ВОЗВРАЩАЕТ СПИСОК кортежей [(ProductRecord, StockRecordData), ...]
        Это нужно для оптимизации, чтобы работать с данными как с единым блоком.
        """
        print("=== ЭТАП 8: ПАРСИНГ ДЛЯ МАССОВОЙ ЗАПИСИ ===\n")
        data_list = []

        try:
            tree = ET.parse(self.xml_path)
            root = tree.getroot()
            offers_block = root.find('ПакетПредложений')

            if offers_block is None:
                print("❌ Блок <ПакетПредложений> не найден.")
                return None

            for offer_element in offers_block.findall('Предложение'):
                builder = ProductDataBuilder(offer_element)
                product_record, stock_data = builder.build()

                if product_record and stock_data:
                    data_list.append((product_record, stock_data))

            print(f"📂 Успешно спаршено записей: {len(data_list)}")
            return data_list # Возвращаем список

        except FileNotFoundError:
            print(f"❌ Файл '{self.xml_path}' не найден.")
            return None