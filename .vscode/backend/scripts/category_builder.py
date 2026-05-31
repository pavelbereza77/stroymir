# Файл: backend/scripts/category_builder.py

from lxml import etree
from typing import Dict, List, Tuple, Optional

class CategoryTreeBuilder:
    """
    Парсит XML-файл и строит дерево категорий.
    НЕ записывает ничего в БД.
    Возвращает кортеж: (categories_map, orphaned_goods_ids).
    """
    def __init__(self):
        self.root_category_name = 'Все товары'
        self.others_category_name = 'Прочие товары'

    def build_tree(self, xml_tree) -> Tuple[Dict[str, int], List[str]]:
        """
        Парсит XML и возвращает структуру данных для записи в БД.
        """
        print("🏗️ СТАРТ: Анализ структуры категорий из XML...")
        root = xml_tree.getroot()
        
        categories_map = {'': None} # В парсере это просто справочник ID
        group_elems = root.findall('.//Группа')
        
        # Буфер для товаров, ждущих родителей
        goods_buffer = []
        orphaned_goods_ids = []

        # 1. Собираем товары в буфер или сразу в "сироты"
        for good_elem in root.findall('.//Товар'):
            good_id = good_elem.get('Идентификатор')
            parent_id_1c = good_elem.get('Родитель', '')
            
            if parent_id_1c and parent_id_1c not in categories_map:
                goods_buffer.append((good_id, parent_id_1c))
            else:
                orphaned_goods_ids.append(good_id)

        # 2. Строим дерево категорий (без записи в БД)
        unresolved = set([g.get('Идентификатор') for g in group_elems])
        
        while unresolved:
            made_progress = False
            for group in group_elems:
                id_1c = group.get('Идентификатор')
                if id_1c not in unresolved:
                    continue

                parent_id_1c = group.get('Родитель', '')
                name = group.get('Наименование', '').strip()
                
                if not name or parent_id_1c not in categories_map and parent_id_1c != '':
                    continue # Пропускаем, если родитель еще не обработан (кроме корня)

                categories_map[id_1c] = {
                    'name': name,
                    'parent_id_1c': parent_id_1c,
                    'slug': name.lower().replace(' ', '-').replace('/', '-')
                }
                unresolved.remove(id_1c)
                made_progress = True

            if not made_progress:
                break # Защита от зацикливания

        # 3. Обрабатываем буфер товаров (теперь все категории должны быть в словаре)
        for good_id, parent_id_1c in goods_buffer:
            if parent_id_1c in categories_map:
                orphaned_goods_ids.append(good_id)
            else:
                orphaned_goods_ids.append(good_id) # Все, у кого нет категории, идут в "Прочие"

        print("🏗️ ЗАВЕРШЕНО: Структура категорий проанализирована.")
        return categories_map, orphaned_goods_ids