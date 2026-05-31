# scripts/parsers.py

import xml.etree.ElementTree as ET
from typing import Iterator, Tuple, Optional
import logging

from scripts.dto import ProductRecord, StockRecordData

# Настройка логгирования
logger = logging.getLogger(__name__)

class ProductDataBuilder:
    """Строитель, который собирает объекты из одного элемента <Предложение>."""

    def __init__(self, offer_element: ET.Element) -> None:
        self.offer = offer_element

    def get_upc(self) -> Optional[str]:
        """Получает уникальный идентификатор товара (UPC)"""
        link = self.offer.find('СсылкаНаТовар')
        return link.get('ИдентификаторВКаталоге') if link is not None else None

    def get_title(self) -> str:
        """Получает название товара"""
        for prop in self.offer.findall('ЗначениеСвойства'):
            if prop.get('ИдентификаторСвойства') == 'ПолноеНаименование':
                return prop.get('Значение')
        return "Товар без названия"

    def get_price(self) -> str:
        """Получает цену товара"""
        return self.offer.get('Цена', '0')

    def get_quantity(self) -> str:
        """Получает количество товара на складе"""
        return self.offer.get('Количество', '0')

    def build(self) -> Tuple[Optional[ProductRecord], Optional[StockRecordData]]:
        """Собирает и возвращает готовые объекты данных."""
        upc = self.get_upc()
        if not upc:
            return None, None  # Пропускаем, если нет UPC

        return (
            ProductRecord(upc=upc, title=self.get_title()),
            StockRecordData(partner_sku=upc, price=self.get_price(), num_in_stock=self.get_quantity())
        )


class OfferParser:
    """Фабрика, которая управляет процессом парсинга всего файла."""

    def __init__(self, xml_path: str) -> None:
        self.xml_path = xml_path

    def parse(self) -> Iterator[Tuple[ProductRecord, StockRecordData]]:
        """
        Генерирует кортежи (ProductRecord, StockRecordData) по мере парсинга XML.
        Используется потоковая обработка для экономии памяти.
        """
        logger.info("Начало парсинга XML-файла: %s", self.xml_path)

        try:
            context = ET.iterparse(self.xml_path, events=("start", "end"))
            # Пропускаем первый элемент (корень дерева)
            _, root = next(context)

            # Начинаем парсинг
            processed_count = 0
            skipped_count = 0

            for event, elem in context:
                if event == "end" and elem.tag == "Предложение":
                    processed_count += 1

                    # Строим объекты данных
                    builder = ProductDataBuilder(elem)
                    product_record, stock_data = builder.build()

                    if product_record and stock_data:
                        yield product_record, stock_data
                    else:
                        skipped_count += 1

                    # Освобождаем память, очищая обработанный элемент
                    elem.clear()

                    # Периодический отчет о прогрессе
                    if processed_count % 1000 == 0:
                        logger.info("Обработано предложений: %d, пропущено: %d", processed_count, skipped_count)

            # Удаляем корень дерева, чтобы освободить память
            root.clear()

            logger.info("Завершение парсинга XML-файла: %s", self.xml_path)
            logger.info("Всего предложений: %d, пропущено: %d", processed_count, skipped_count)

        except FileNotFoundError:
            logger.error("Файл '%s' не найден.", self.xml_path)
            raise
        except ET.ParseError as e:
            logger.error("Ошибка парсинга XML: %s", e)
            raise
        except Exception as e:
            logger.exception("Неожиданная ошибка при парсинге XML: %s", e)
            raise