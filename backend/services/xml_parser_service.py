# services/xml_parser_service.py

import xml.etree.ElementTree as ET
from typing import Iterator, Tuple
import logging
from decimal import Decimal

# Импортируем DTO-классы
from services.dto import ProductRecord, StockRecordData

# Настройка логгера
logger = logging.getLogger(__name__)


class XmlParserService:
    """
    Сервис для потокового парсинга XML-файлов от 1С.
    """

    def __init__(self, xml_path: str):
        """
        Инициализация сервиса.

        Args:
            xml_path: Путь к XML-файлу на диске.
        """
        self.xml_path = xml_path

    def parse(self) -> Iterator[Tuple[ProductRecord, StockRecordData]]:
        """
        Главный метод парсинга.

        Генерирует кортежи (ProductRecord, StockRecordData) для каждого валидного <Предложение>.
        Используется как генератор (yield), что позволяет обрабатывать данные по мере их поступления.

        Yields:
            Кортеж из объекта товара и данных о запасах.
        """
        logger.info("Начало парсинга XML-файла: %s", self.xml_path)

        processed_count = 0
        skipped_count = 0

        try:
            # Открываем файл с нужной кодировкой
            with open(self.xml_path, "rb") as f:
                # Читаем первые байты файла
                first_bytes = f.read(100)
                logger.debug("Первые байты файла: %s", first_bytes.decode(errors="replace"))

                # Устанавливаем позицию обратно в начало файла
                f.seek(0)

                # Создаем контекстный парсер, передавая открытый файл
                context = ET.iterparse(f, events=("start", "end"))

                # Пропускаем корневой элемент документа (<КоммерческаяИнформация>)
                _, root = next(context)

                for event, elem in context:
                    # Логируем каждый встретившийся тег
                    # logger.debug("Встречен тег: %s", elem.tag)

                    if event == "end" and elem.tag == "Предложение":
                        processed_count += 1

                        # Извлекаем UPC товара
                        link_tag = elem.find("./СсылкаНаТовар")
                        if link_tag is None:
                            logger.warning("Предложение №%d: отсутствует ссылка на товар", processed_count)
                            continue

                        upc = link_tag.get("ИдентификаторВКаталоге")
                        if not upc:
                            logger.warning("Предложение №%d: отсутствует UPC", processed_count)
                            continue

                        # Извлекаем название товара
                        title_tag = elem.find(".//ЗначениеСвойства[@ИдентификаторСвойства='ПолноеНаименование']")
                        if title_tag is None:
                            logger.warning("Предложение №%d: отсутствует название товара", processed_count)
                            continue

                        title = title_tag.get("Значение")
                        if not title:
                            logger.warning("Предложение №%d: пустое название товара", processed_count)
                            continue

                        # Извлекаем цену и количество
                        try:
                            price = Decimal(elem.get("Цена", "0"))
                            
                            # price = Decimal(elem.get("Цена", "0")) 
                            quantity = int(elem.get("Количество", 0))
                        except ValueError:
                            logger.warning("Предложение №%d: некорректные данные о цене или количестве", processed_count)
                            continue

                        # Создаем объекты DTO
                        product_record = ProductRecord(upc=upc, title=title)
                        stock_data = StockRecordData(product_upc=upc, price=price, num_in_stock=quantity)

                        yield product_record, stock_data

                        # Очищаем элемент для экономии памяти
                        elem.clear()

                    # Периодический отчет о прогрессе
                    # if processed_count % 500 == 0:
                    #     logger.info("Прогресс: обработано %d предложений", processed_count)

                # Очистка корня дерева после завершения цикла
                root.clear()

                logger.info("Завершение парсинга XML-файла: %s", self.xml_path)
                logger.info("Итог парсинга: всего предложений — %d, пропущено — %d", processed_count, skipped_count)

        except FileNotFoundError:
            logger.error("Файл '%s' не найден.", self.xml_path)
            raise

        except ET.ParseError as e:
            logger.error("Ошибка парсинга XML: %s", e)
        except Exception as e:
            logger.exception("Неожиданная ошибка при парсинге XML: %s", e)
            raise
    
        # for event, elem in context:
        #     # Логируем каждый встретившийся тег
        #     # logger.debug("Встречен тег: %s", elem.tag)

        #     if event == "end" and elem.tag == "Предложение":
        #         processed_count += 1

        #         # Извлекаем UPC товара
        #         link_tag = elem.find("./СсылкаНаТовар")
        #         if link_tag is None:
        #             logger.warning("Предложение №%d: отсутствует ссылка на товар", processed_count)
        #             continue

        #         upc = link_tag.get("ИдентификаторВКаталоге")
        #         if not upc:
        #             logger.warning("Предложение №%d: отсутствует UPC", processed_count)
        #             continue

        #         # Извлекаем название товара
        #         title_tag = elem.find(".//ЗначениеСвойства[@ИдентификаторСвойства='ПолноеНаименование']")
        #         if title_tag is None:
        #             logger.warning("Предложение №%d: отсутствует название товара", processed_count)
        #             continue

        #         title = title_tag.get("Значение")
        #         if not title:
        #             logger.warning("Предложение №%d: пустое название товара", processed_count)
        #             continue

        #         # Извлекаем цену и количество
        #         try:
        #             price = float(elem.get("Цена", 0))
        #             quantity = int(elem.get("Количество", 0))
        #         except ValueError:
        #             logger.warning("Предложение №%d: некорректные данные о цене или количестве", processed_count)
        #             continue

        #         # Создаем объекты DTO
        #         product_record = ProductRecord(upc=upc, title=title)
        #         stock_data = StockRecordData(product_upc=upc, price=price, num_in_stock=quantity)

        #         # ВЫВОДИМ СЫРЫЕ ДАННЫЕ В КОНСОЛЬ (временный код)
        #         print("---- Сырые данные ----")
        #         print("ProductRecord:", product_record)
        #         print("StockRecordData:", stock_data)
        #         print("---------------------\n")