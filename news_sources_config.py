"""
Конфигурация источников новостей
Telegram каналы для сбора новостей
"""

import os
from typing import Dict, List

class NewsSourcesConfig:
    """Конфигурация источников новостей"""
    
    # Конфигурация источников (только Telegram каналы)
    SOURCES_CONFIG = {
        'telegram': {
            'enabled': True,
            'description': 'Новости из Telegram каналов крупных СМИ',
            'sources': {
                'политика': [
                    '@rian_ru',
                    '@tass_agency', 
                    '@vedomosti',
                    '@kremlinru'
                ],
                'экономика': [
                    '@rbc_news',
                    '@tass_agency',
                    '@vbrr'
                ],
                'спорт': [
                    '@rsport_ria',
                    '@matchtv',
                    '@sportsru'
                ],
                'технологии': [
                    '@vc_ru',
                    '@tjournal',
                    '@habr_com',
                    '@datais'
                ],
                'разное': [
                    '@hypewave',
                    '@dtfbest'
                ],
                'мировые': [
                    '@rtnews',
                    '@bbcrussian',
                    '@reuters_russian',
                    '@dw_russian'
                ]
            }
        }
    }
    
    @classmethod
    def get_current_source_type(cls) -> str:
        """Получить текущий тип источника новостей"""
        return os.getenv('NEWS_SOURCE_TYPE', 'telegram')  # По умолчанию Telegram
    
    @classmethod
    def set_source_type(cls, source_type: str):
        """Установить тип источника новостей"""
        if source_type in cls.SOURCES_CONFIG:
            os.environ['NEWS_SOURCE_TYPE'] = source_type
            return True
        return False
    
    @classmethod
    def get_sources_for_category(cls, category: str) -> List[str]:
        """Получить источники для конкретной категории"""
        current_source = cls.get_current_source_type()
        config = cls.SOURCES_CONFIG.get(current_source, {})
        
        # Возвращаем список Telegram каналов для категории
        return config.get('sources', {}).get(category, [])
    
    @classmethod
    def is_source_enabled(cls, source_type: str = None) -> bool:
        """Проверить, включен ли источник"""
        if source_type is None:
            source_type = cls.get_current_source_type()
            
        config = cls.SOURCES_CONFIG.get(source_type, {})
        return config.get('enabled', False)
    
    @classmethod
    def get_available_sources(cls) -> List[str]:
        """Получить список доступных типов источников"""
        return [
            source_type for source_type, config in cls.SOURCES_CONFIG.items()
            if config.get('enabled', False)
        ]
    
    @classmethod
    def get_source_info(cls, source_type: str = None) -> Dict:
        """Получить информацию о типе источника"""
        if source_type is None:
            source_type = cls.get_current_source_type()
            
        return cls.SOURCES_CONFIG.get(source_type, {})
    
    @classmethod
    def get_supported_categories(cls) -> List[str]:
        """Получить список поддерживаемых категорий"""
        return ['политика', 'экономика', 'спорт', 'технологии', 'разное', 'мировые']

# Настройки для Telegram режима
NEWS_MODE_SETTINGS = {
    'telegram': {
        'update_interval': 15,  # минут
        'max_news_per_request': 15,
        'require_translation': False  # Telegram каналы уже на русском
    }
}

def get_mode_settings(source_type: str = None) -> Dict:
    """Получить настройки для текущего режима"""
    if source_type is None:
        source_type = NewsSourcesConfig.get_current_source_type()
    
    return NEWS_MODE_SETTINGS.get(source_type, NEWS_MODE_SETTINGS['telegram'])

# Пример использования:
"""
# Переключение на Telegram источники
NewsSourcesConfig.set_source_type('telegram')

# Получение источников для категории
sources = NewsSourcesConfig.get_sources_for_category('политика')
# Результат: ['@rian_ru', '@tass_agency', '@vedomosti']

# Проверка доступности источника
if NewsSourcesConfig.is_source_enabled('telegram'):
    print("Telegram источники включены")

# Получение настроек режима
settings = get_mode_settings()
print(f"Интервал обновления: {settings['update_interval']} минут")
"""