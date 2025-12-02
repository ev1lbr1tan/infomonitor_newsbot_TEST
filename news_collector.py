import feedparser
import requests
from datetime import datetime, timedelta
import re
from typing import List, Dict

class NewsCollector:
    """Класс для сбора новостей из RSS источников"""
    
    def __init__(self):
        self.news_sources = {
            'ria': 'https://ria.ru/export/rss2/news/index.xml',
            'tass': 'https://tass.ru/rss/v2.xml',
            'lenta': 'https://lenta.ru/rss/news',
            'vedomosti': 'https://www.vedomosti.ru/rss/news.xml',
            'rbc': 'https://rssexport.rbc.ru/news/20/5001001/full.rss'
        }
    
    def clean_text(self, text: str, max_length: int = 200) -> str:
        """Очистка текста от HTML тегов и ограничение длины"""
        # Удаление HTML тегов
        clean = re.sub('<[^<]+?>', '', text)
        # Удаление лишних пробелов
        clean = re.sub(r'\s+', ' ', clean).strip()
        # Ограничение длины
        if len(clean) > max_length:
            clean = clean[:max_length].rsplit(' ', 1)[0] + '...'
        return clean
    
    def get_latest_news(self, limit: int = 10) -> List[Dict]:
        """Получение последних новостей из всех источников"""
        all_news = []
        
        for source_name, url in self.news_sources.items():
            try:
                feed = feedparser.parse(url)
                if feed.bozo == 0 and feed.entries:
                    for entry in feed.entries[:3]:  # Берем по 3 новости с каждого источника
                        news_item = {
                            'title': self.clean_text(entry.get('title', 'Без заголовка')),
                            'description': self.clean_text(entry.get('description', 'Описание отсутствует')),
                            'link': entry.get('link', ''),
                            'source': source_name.upper(),
                            'published': entry.get('published', ''),
                            'published_parsed': entry.get('published_parsed', None)
                        }
                        all_news.append(news_item)
            except Exception as e:
                print(f"Ошибка при получении новостей из {source_name}: {e}")
        
        # Сортируем по дате публикации (если есть)
        all_news.sort(key=lambda x: x.get('published_parsed') or (0, 0, 0, 0, 0, 0), reverse=True)
        
        return all_news[:limit]
    
    def format_news_message(self, news_list: List[Dict]) -> str:
        """Форматирование новостей для отправки в Telegram"""
        if not news_list:
            return "😔 К сожалению, не удалось получить новости. Попробуйте позже."
        
        message = "📰 *ТОП НОВОСТИ*\n\n"
        
        for i, news in enumerate(news_list, 1):
            message += f"*{i}. {news['title']}*\n"
            message += f"📝 {news['description']}\n"
            message += f"🔗 [Читать полностью]({news['link']})\n"
            message += f"📰 Источник: {news['source']}\n"
            if news['published']:
                message += f"🕐 {news['published']}\n"
            message += "\n" + "─" * 50 + "\n\n"
        
        message += f"📊 Показано новостей: {len(news_list)}"
        return message