# coordinator/import_coordinator.py

import logging
# from typing import List, Tuple

# Импортируем наши сервисы
from services.xml_parser_service import XmlParserService
from services.validation_service import ValidationService
from services.db_service import DbService
# from services.dto import ProductRecord, StockRecordData

from services.default_entities_manager import DefaultEntitiesManager

# Настроим логгер
logger = logging.getLogger(__name__)


class ImportCoordinator:
    def __init__(self, xml_path: str):
        """
        Инициализация оркестратора.

        :param xml_path: Путь к XML-файлу.
        """
        self.xml_path = xml_path

        # Получаем или создаём одиночные сущности
        self.partner = DefaultEntitiesManager.get_partner()
        self.product_class = DefaultEntitiesManager.get_product_class()

        # Создаем экземпляры сервисов
        self.parser = XmlParserService(xml_path)  # Используем переданный путь
        self.validator = ValidationService()
        self.db_service = DbService(self.partner, self.product_class)


    def run_import(self):
        """
        Запускает процесс импорта данных.

        Этапы:
        1. Парсинг XML.
        2. Запись в базу данных.
        3. Логирование итогов.
        """
        logger.info("*** НАЧАЛО ПРОЦЕССА ИМПОРТА ***")

        # Этап 1: Парсинг XML
        raw_data_generator = self.parser.parse()
       

        # Этап 2: Сборка валидных данных
        valid_data = []
        
        for product_record, stock_data in raw_data_generator:
            
            # Включение валидации
            is_valid, validation_message, is_public = self.validator.validate(product_record, stock_data)
            product_record.is_public = is_public
            valid_data.append((product_record, stock_data))


        # Этап 3: Запись в базу данных
        if valid_data:
            result = self.db_service.process(valid_data)
            logger.info("Данные успешно записаны в базу!")
        else:
            result = {"error": "Нет валидных данных для записи"}

        # Этап 4: Итоговый отчет
        logger.info("*** ОКОНЧАНИЕ ПРОЦЕССА ИМПОРТА ***")
        logger.info("ИТОГОВАЯ СТАТИСТИКА:")
        # logger.info("- Всего предложений: %d", len(valid_data))
        logger.info("- Товары: создано=%d, обновлено=%d", 
                   result.get("created_products", 0), result.get("updated_products", 0))
        logger.info("- Запасы: создано=%d, обновлено=%d", 
                   result.get("created_stocks", 0), result.get("updated_stocks", 0))

        return result