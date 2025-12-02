#!/usr/bin/env python3
"""
Скрипт для тестирования функциональности бота локально
"""

import os
import sys
from news_collector import NewsCollector

def test_news_collector():
    """Тестирование модуля сбора новостей"""
    print("🧪 Тестирование модуля сбора новостей...")
    
    try:
        collector = NewsCollector()
        news_list = collector.get_latest_news(limit=5)
        
        print(f"✅ Успешно получено {len(news_list)} новостей")
        
        # Выводим первые 2 новости для проверки
        for i, news in enumerate(news_list[:2], 1):
            print(f"\n📰 Новость {i}:")
            print(f"   Заголовок: {news['title'][:80]}...")
            print(f"   Источник: {news['source']}")
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

def test_env_setup():
    """Тестирование настройки переменных окружения"""
    print("\n🔧 Тестирование переменных окружения...")
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if token:
        print(f"✅ Токен бота установлен (длина: {len(token)} символов)")
        return True
    else:
        print("⚠️  TELEGRAM_BOT_TOKEN не установлен")
        print("💡 Установите токен командой:")
        print("   Windows: set TELEGRAM_BOT_TOKEN=ваш_токен")
        print("   Linux/Mac: export TELEGRAM_BOT_TOKEN=ваш_токен")
        return False

def test_dependencies():
    """Тестирование зависимостей"""
    print("\n📦 Проверка зависимостей...")
    
    required_modules = [
        'feedparser',
        'requests', 
        'telegram',
        'apscheduler'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - не установлен")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n💡 Установите недостающие модули:")
        print(f"   pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Главная функция тестирования"""
    print("🤖 ИнфоМонитор - Тестирование")
    print("=" * 50)
    
    results = []
    
    # Тест зависимостей
    results.append(test_dependencies())
    
    # Тест переменных окружения  
    results.append(test_env_setup())
    
    # Тест сбора новостей
    results.append(test_news_collector())
    
    # Результат
    print("\n" + "=" * 50)
    passed_tests = sum(results)
    total_tests = len(results)
    
    if passed_tests == total_tests:
        print(f"🎉 Все тесты пройдены ({passed_tests}/{total_tests})")
        print("🚀 Бот готов к запуску!")
        return True
    else:
        print(f"⚠️  Пройдено тестов: {passed_tests}/{total_tests}")
        print("🔧 Исправьте проблемы перед запуском")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)