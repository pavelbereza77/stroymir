# scripts/singleton_default_image.py

class DefaultImageManager:
    """Singleton для управления дефолтным изображением"""

    _instance = None

    def __new__(cls):
        """Гарантирует создание только одного экземпляра"""
        if cls._instance is None:
            cls._instance = super(DefaultImageManager, cls).__new__(cls)
            # Инициализация дефолтного изображения
            cls._instance.initialize_default_image()
        return cls._instance

    def initialize_default_image(self):
        """Инициализация дефолтного изображения"""
        # Путь к дефолтному изображению
        self.default_image_path = 'path/to/default/image.jpg'
        # Можно добавить логику загрузки изображения, если оно хранится в облачном хранилище или CDN

    def get_default_image_path(self):
        """Возвращает путь к дефолтному изображению"""
        return self.default_image_path