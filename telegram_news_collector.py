"""
Модуль для сбора новостей из Telegram каналов
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re
import json

from telegram import Bot
from database import Database

logger = logging.getLogger(__name__)

class TelegramNewsCollector:
    """Сборщик новостей из Telegram каналов"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token)
        self.database = Database()
        
        # Список популярных новостных каналов (можно настроить)
        self.news_channels = {
            'РИА_Новости': '@rian_ru',
            'ТАСС': '@tass_agency', 
            'RT': '@rtnews',
            'РБК': '@rbc_news',
            'Ведомости': '@vedomosti',
            'Лента_ру': '@lentaru',
            'Эхо_Москвы': '@echomsk',
            'BBC_Russian': '@bbcrussian',
            'CNN_Russian': '@cnn_ru',
            'Reuters_Russian': '@reuters_russian',
            'DataIS': '@datais',
            'Hypewave': '@hypewave',
            'DTF_Best': '@dtfbest'
        }
        
        # Настройки фильтрации
        self.min_message_length = 50  # Минимальная длина сообщения
        self.max_message_length = 1000  # Максимальная длина сообщения
        self.filter_keywords = [
            'новость', 'сообщает', 'заявил', 'сообщил', 'объявил',
            'news', 'report', 'according', 'reported', 'announced'
        ]
        
    def categorize_message(self, text: str, channel_name: str) -> str:
        """Автоматическая категоризация сообщения по тексту"""
        text_lower = text.lower()
        
        # Политические ключевые слова
        if any(word in text_lower for word in [
            'президент', 'правительство', 'дума', 'сенат', 'выборы', 
            'политика', 'закон', 'указ', 'постановление',
            'gоvernment', 'president', 'election', 'law', 'policy'
        ]):
            return 'политика'
            
        # Экономические ключевые слова
        if any(word in text_lower for word in [
            'экономика', 'бизнес', 'рубль', 'доллар', 'акции', 'рынок',
            'банк', 'кредит', 'инвестиции', 'производство',
            'economy', 'business', 'market', 'bank', 'investment'
        ]):
            return 'экономика'
            
        # Спортивные ключевые слова
        if any(word in text_lower for word in [
            'спорт', 'футбол', 'хоккей', 'теннис', 'олимпиада', 'чемпионат',
            'игра', 'матч', 'команда', 'спортсмен',
            'sport', 'football', 'olympics', 'game', 'team'
        ]):
            return 'спорт'
            
        # Технологические ключевые слова
        if any(word in text_lower for word in [
            'технологии', 'IT', 'гаджет', 'приложение', 'интернет',
            'смартфон', 'компьютер', 'программа', 'робот', 'AI',
            'technology', 'tech', 'digital', 'ai', 'software'
        ]):
            return 'технологии'
            
        # По умолчанию - разное
        return 'разное'
        
    def is_relevant_news(self, message_text: str) -> bool:
        """Проверка, является ли сообщение релевантной новостью"""
        if not message_text:
            return False
            
        # Проверка длины
        if len(message_text) < self.min_message_length:
            return False
            
        if len(message_text) > self.max_message_length:
            return False
            
        # Проверка на наличие ключевых слов
        text_lower = message_text.lower()
        return any(keyword in text_lower for keyword in self.filter_keywords)
        
    def extract_links(self, message_text: str) -> List[str]:
        """Извлечение ссылок из сообщения"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(url_pattern, message_text)
        
    async def get_channel_messages(self, channel_username: str, limit: int = 50) -> List[Dict]:
        """Получение сообщений из канала"""
        try:
            # Получаем информацию о канале
            chat = await self.bot.get_chat(chat_id=channel_username)
            
            # Получаем последние сообщения
            messages = await self.bot.get_chat_messages(
                chat_id=channel_username, 
                limit=limit
            )
            
            processed_messages = []
            
            for message in messages:
                if not message.text or not message.text.strip():
                    continue
                    
                message_text = message.text.strip()
                
                # Проверяем, является ли это новостью
                if not self.is_relevant_news(message_text):
                    continue
                    
                # Извлекаем ссылку (первая найденная)
                links = self.extract_links(message_text)
                link = links[0] if links else ""
                
                # Категоризируем сообщение
                category = self.categorize_message(message_text, chat.title)
                
                processed_message = {
                    'title': message_text[:100] + "..." if len(message_text) > 100 else message_text,
                    'text': message_text,
                    'link': link,
                    'source': chat.title,
                    'channel_username': channel_username,
                    'category': category,
                    'published': message.date.strftime('%Y-%m-%d %H:%M') if message.date else "",
                    'original_language': 'ru',
                    'image_url': ""
                }
                
                processed_messages.append(processed_message)
                
            logger.info(f"Обработано {len(processed_messages)} новостей из канала {channel_username}")
            return processed_messages
            
        except Exception as e:
            logger.error(f"Ошибка при получении сообщений из канала {channel_username}: {e}")
            return []
            
    async def get_telegram_news_by_category(self, categories: List[str], limit: int = 10) -> List[Dict]:
        """Получение новостей из Telegram по категориям"""
        all_news = []
        
        for channel_name, channel_username in self.news_channels.items():
            try:
                # Получаем сообщения из канала
                channel_messages = await self.get_channel_messages(channel_username, limit=20)
                
                # Фильтруем по нужным категориям
                for message in channel_messages:
                    if message['category'] in categories:
                        all_news.append(message)
                        
                # Небольшая задержка между запросами
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Ошибка при обработке канала {channel_name}: {e}")
                continue
                
        # Сортируем по времени публикации
        all_news.sort(key=lambda x: x['published'], reverse=True)
        
        # Возвращаем ограниченное количество
        return all_news[:limit]
        
    async def get_all_telegram_news(self, limit: int = 10) -> List[Dict]:
        """Получение всех новостей из Telegram каналов"""
        all_news = []
        
        for channel_name, channel_username in self.news_channels.items():
            try:
                channel_messages = await self.get_channel_messages(channel_username, limit=5)
                all_news.extend(channel_messages)
                await asyncio.sleep(0.5)  # Задержка между запросами
                
            except Exception as e:
                logger.error(f"Ошибка при обработке канала {channel_name}: {e}")
                continue
                
        # Сортируем и ограничиваем
        all_news.sort(key=lambda x: x['published'], reverse=True)
        return all_news[:limit]
        
    def get_category_emoji(self, category: str) -> str:
        """Получение эмодзи для категории"""
        emoji_map = {
            'политика': '🏛️',
            'экономика': '💰', 
            'спорт': '⚽',
            'технологии': '💻',
            'разное': '📝',
            'мировые': '🌍'
        }
        return emoji_map.get(category, '📰')

    async def search_telegram_channels(self, query: str, limit: int = 10) -> List[Dict]:
        """Поиск релевантных Telegram каналов по запросу (через публичный поиск)"""
        # Примечание: это упрощенная реализация
        # В реальном приложении можно использовать @tgchannels bot или другие API
        relevant_channels = []
        
        # Простой фильтр по названию
        for channel_name, channel_username in self.news_channels.items():
            if query.lower() in channel_name.lower():
                relevant_channels.append({
                    'name': channel_name,
                    'username': channel_username,
                    'description': f"Новостной канал: {channel_name}",
                    'subscribers': 'Неизвестно',
                    'language': 'ru'
                })
                
        return relevant_channels[:limit]