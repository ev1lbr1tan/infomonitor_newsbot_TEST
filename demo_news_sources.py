"""
Демонстрация работы с Telegram источниками новостей
"""

import asyncio
import os
from news_sources_config import NewsSourcesConfig
from telegram_news_collector import TelegramNewsCollector

async def demo_telegram_news():
    """Демонстрация возможностей Telegram источников"""
    
    print("🚀 ДЕМОНСТРАЦИЯ TELEGRAM ИСТОЧНИКОВ НОВОСТЕЙ\n")
    
    # 1. Показываем информацию о текущем источнике
    current_source = NewsSourcesConfig.get_current_source_type()
    print(f"📱 Текущий источник: {current_source}")
    
    info = NewsSourcesConfig.get_source_info(current_source)
    print(f"📋 Описание: {info.get('description', 'Нет описания')}")
    
    # 2. Показываем каналы для каждой категории
    print("\n📊 Каналы по категориям:")
    categories = NewsSourcesConfig.get_supported_categories()
    
    for category in categories:
        channels = NewsSourcesConfig.get_sources_for_category(category)
        print(f"   🏷️ {category.upper()}:")
        for channel in channels:
            print(f"      • {channel}")
        print()
    
    # 3. Показываем настройки режима
    print("⚙️ Настройки Telegram режима:")
    settings = {
        'update_interval': '15 минут',
        'max_news_per_request': '15 новостей',
        'translation_required': 'Нет (все на русском)',
        'realtime': 'Да',
        'sources_count': sum(len(NewsSourcesConfig.get_sources_for_category(cat)) for cat in categories)
    }
    
    for key, value in settings.items():
        print(f"   • {key.replace('_', ' ').title()}: {value}")
    
    print("\n🎉 Демонстрация завершена!")
    print("\n💡 Особенности системы:")
    print("   ✅ Новости в реальном времени из редакций СМИ")
    print("   ✅ Автоматическая категоризация по содержанию")
    print("   ✅ Умная фильтрация релевантных сообщений")
    print("   ✅ Fallback-механизмы при ошибках")
    print("   ✅ Извлечение ссылок из сообщений")
    
    print("\n🚀 Готово к работе! Ваш бот получает самые свежие новости.")

if __name__ == "__main__":
    # Устанавливаем переменную окружения для демо
    os.environ['NEWS_SOURCE_TYPE'] = 'telegram'
    
    # Запускаем демонстрацию
    asyncio.run(demo_telegram_news())