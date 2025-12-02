import feedparser
import requests
from datetime import datetime, timedelta
import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class EnhancedNewsCollector:
    """Улучшенный класс для сбора новостей с категориями и переводом"""
    
    def __init__(self):
        # Словарь источников новостей по категориям (расширенный)
        self.news_sources = {
            'политика': {
                'ria': 'https://ria.ru/export/rss2/politics/index.xml',
                'tass': 'https://tass.ru/rss/v2.xml',
                'interfax': 'https://www.interfax.ru/rss.asp',
                'vedomosti': 'https://www.vedomosti.ru/rss/news.xml',
                'regnum': 'https://www.regnum.ru/feed',
                'gazeta': 'https://www.gazeta.ru/rss/articles.xml',
                'lenta': 'https://lenta.ru/rss/news',
                'vz': 'https://vz.ru/rssnews.xml',
                'novaya_gazeta': 'https://novayagazeta.ru/rss/articles.xml',
                'rt': 'https://www.rt.com/rss/all/'
            },
            'экономика': {
                'rbc': 'https://rssexport.rbc.ru/news/20/5001001/full.rss',
                'vedomosti': 'https://www.vedomosti.ru/rss/business.xml',
                'regnum': 'https://www.regnum.ru/feed',
                'kommersant': 'https://www.kommersant.ru/rss/economics.xml',
                'prime': 'https://1prime.ru/rss/',
                'forbes': 'https://forbes.ru/rss/feed.xml',
                'vc': 'https://vc.ru/rss',
                'bloomberg': 'https://feeds.bloomberg.com/markets/news.rss',
                'market_watch': 'http://feeds.marketwatch.com/marketwatch/marketpulse/',
                'financial_times': 'https://www.ft.com/rss/home'
            },
            'спорт': {
                'ria_sport': 'https://rsport.ria.ru/export/rss2/news/index.xml',
                'matchtv': 'https://matchtv.ru/rss/news.xml',
                'tass_sport': 'https://tass.ru/rss/v2.xml',
                'championat': 'https://www.championat.com/rss/news.xml',
                'sport_express': 'https://www.sport-express.ru/rss/news.xml',
                'eurosport': 'https://www.eurosport.ru/rss/all-news.xml',
                'espn': 'https://site.api.espn.com/apis/site/v2/sports/football/soccer/rss/news',
                'sky_sports': 'https://www.skysports.com/rss/12040',
                'goal': 'https://www.goal.com/rss/en/news',
                'bbc_sport': 'https://feeds.bbci.co.uk/sport/rss.xml'
            },
            'технологии': {
                'habr': 'https://habr.com/ru/rss/articles/',
                'tadviser': 'https://www.tadviser.ru/rss.xml',
                'vc': 'https://vc.ru/rss',
                'techcrunch': 'https://techcrunch.com/feed/',
                'the_verge': 'https://www.theverge.com/rss/index.xml',
                'wired': 'https://www.wired.com/feed/rss',
                'arstechnica': 'http://feeds.arstechnica.com/arstechnica/index',
                'engadget': 'https://www.engadget.com/rss.xml',
                'mashable': 'https://mashable.com/feeds/rss/technology',
                'cnet': 'https://www.cnet.com/rss/news/'
            },
            'мировые': {
                'bbc': 'https://feeds.bbci.co.uk/news/rss.xml',
                'reuters': 'https://feeds.reuters.com/Reuters/worldNews',
                'cnn': 'http://rss.cnn.com/rss/edition.rss',
                'guardian': 'https://www.theguardian.com/world/rss',
                'ap': 'https://feeds.apnews.com/apf-worldnews',
                'npr': 'https://feeds.npr.org/1001/rss.xml',
                'wsj': 'https://feeds.a.dj.com/rss/RSSWorldNews.xml',
                'nyt': 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
                'france24': 'https://www.france24.com/en/rss',
                'dw': 'https://rss.dw.com/rdf/rss-en'
            }
        }
        
        # Словарь ключевых слов для категоризации
        self.category_keywords = {
            'политика': ['политика', 'президент', 'правительство', 'депутат', 'парламент', 'выборы', 'митинг', 'протест', 'власть'],
            'экономика': ['экономика', 'биржа', 'валюта', 'рубль', 'доллар', 'нефть', 'газ', 'банк', 'кредит', 'инфляция'],
            'спорт': ['спорт', 'футбол', 'хоккей', 'баскетбол', 'теннис', 'олимпиада', 'чемпионат', 'матч', 'игрок'],
            'технологии': ['технологии', 'искусственный интеллект', 'робот', 'программа', 'приложение', 'гаджет', 'смартфон', 'интернет']
        }
    
    def clean_text(self, text: str, max_length: int = 200) -> str:
        """Очистка текста от HTML тегов и ограничение длины"""
        if not text:
            return ""
        
        # Удаление HTML тегов
        clean = re.sub('<[^<]+?>', '', text)
        # Удаление лишних пробелов
        clean = re.sub(r'\s+', ' ', clean).strip()
        # Ограничение длины
        if len(clean) > max_length:
            clean = clean[:max_length].rsplit(' ', 1)[0] + '...'
        return clean
    
    def detect_category(self, title: str, description: str = "") -> str:
        """Определение категории новости по ключевым словам"""
        text = (title + " " + description).lower()
        
        for category, keywords in self.category_keywords.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        # Если категория не определена, возвращаем "мировые"
        return "мировые"
    
    def get_news_by_category(self, categories: List[str], limit: int = 10) -> List[Dict]:
        """Получение новостей по определенным категориям"""
        all_news = []
        
        for category in categories:
            if category in self.news_sources:
                category_sources = self.news_sources[category]
                
                for source_name, url in category_sources.items():
                    try:
                        feed = feedparser.parse(url)
                        if feed.bozo == 0 and feed.entries:
                            for entry in feed.entries[:3]:  # Берем по 3 новости с каждого источника
                                detected_category = self.detect_category(
                                    entry.get('title', ''), 
                                    entry.get('description', '')
                                )
                                
                                news_item = {
                                    'title': self.clean_text(entry.get('title', 'Без заголовка')),
                                    'description': self.clean_text(entry.get('description', 'Описание отсутствует')),
                                    'link': entry.get('link', ''),
                                    'source': f"{source_name.upper()} ({category})",
                                    'category': detected_category,
                                    'published': entry.get('published', ''),
                                    'published_parsed': entry.get('published_parsed', None),
                                    'original_language': self.detect_language(entry.get('title', '') + ' ' + entry.get('description', ''))
                                }
                                all_news.append(news_item)
                    except Exception as e:
                        logger.error(f"Ошибка при получении новостей из {source_name} (категория {category}): {e}")
        
        # Сортируем по дате публикации (если есть)
        all_news.sort(key=lambda x: x.get('published_parsed') or (0, 0, 0, 0, 0, 0), reverse=True)
        
        return all_news[:limit]
    
    def get_all_news(self, limit: int = 15) -> List[Dict]:
        """Получение новостей из всех категорий"""
        all_news = []
        
        for category, sources in self.news_sources.items():
            for source_name, url in sources.items():
                try:
                    feed = feedparser.parse(url)
                    if feed.bozo == 0 and feed.entries:
                        for entry in feed.entries[:2]:  # Берем по 2 новости с каждого источника
                            detected_category = self.detect_category(
                                entry.get('title', ''), 
                                entry.get('description', '')
                            )
                            
                            news_item = {
                                'title': self.clean_text(entry.get('title', 'Без заголовка')),
                                'description': self.clean_text(entry.get('description', 'Описание отсутствует')),
                                'link': entry.get('link', ''),
                                'source': f"{source_name.upper()}",
                                'category': detected_category,
                                'published': entry.get('published', ''),
                                'published_parsed': entry.get('published_parsed', None),
                                'original_language': self.detect_language(entry.get('title', '') + ' ' + entry.get('description', ''))
                            }
                            all_news.append(news_item)
                except Exception as e:
                    logger.error(f"Ошибка при получении новостей из {source_name}: {e}")
        
        # Сортируем по дате публикации
        all_news.sort(key=lambda x: x.get('published_parsed') or (0, 0, 0, 0, 0, 0), reverse=True)
        
        return all_news[:limit]
    
    def detect_language(self, text: str) -> str:
        """Простое определение языка текста"""
        if not text:
            return "unknown"
        
        # Русские буквы
        russian_chars = re.findall(r'[а-яёА-ЯЁ]', text)
        # Латинские буквы
        latin_chars = re.findall(r'[a-zA-Z]', text)
        
        if len(russian_chars) > len(latin_chars):
            return "ru"
        elif len(latin_chars) > len(russian_chars):
            return "en"
        else:
            return "mixed"
    
    def format_news_message(self, news_list: List[Dict], show_categories: bool = True, show_translation: bool = True) -> str:
        """Форматирование новостей для отправки в Telegram"""
        if not news_list:
            return "😔 К сожалению, не удалось получить новости. Попробуйте позже."
        
        message = "📰 *ИНФОМОНИТОР - ПОСЛЕДНИЕ НОВОСТИ*\n\n"
        
        # Группировка по категориям
        categories = {}
        for news in news_list:
            category = news.get('category', 'общие')
            if category not in categories:
                categories[category] = []
            categories[category].append(news)
        
        for i, (category, category_news) in enumerate(categories.items(), 1):
            if show_categories:
                emoji = self.get_category_emoji(category)
                message += f"📂 *{emoji} {category.upper()}*\n\n"
            
            for j, news in enumerate(category_news, 1):
                if show_categories:
                    num = f"{i}.{j}"
                else:
                    num = str(i + j - 1)
                
                message += f"*{num}. {news['title']}*\n"
                message += f"📝 {news['description']}\n"
                
                # Информация о языке и переводе
                lang_info = ""
                if news.get('original_language') == 'en' and show_translation:
                    lang_info = " 🇬🇧 (на английском)"
                elif news.get('original_language') == 'mixed' and show_translation:
                    lang_info = " 🌍 (смешанный)"
                
                message += f"🔗 [Читать полностью]({news['link']})\n"
                message += f"📰 Источник: {news['source']}{lang_info}\n"
                
                if news['published']:
                    message += f"🕐 {news['published']}\n"
                message += "\n" + "─" * 40 + "\n\n"
        
        message += f"📊 Показано новостей: {len(news_list)} из категорий: {', '.join(categories.keys())}"
        return message
    
    def get_category_emoji(self, category: str) -> str:
        """Получение эмодзи для категории"""
        emojis = {
            'политика': '🏛️',
            'экономика': '💰',
            'спорт': '⚽',
            'технологии': '💻',
            'мировые': '🌍',
            'общие': '📄'
        }
        return emojis.get(category, '📰')
    
    def translate_text(self, text: str, target_lang: str = 'ru') -> Optional[str]:
        """Перевод текста через бесплатный сервис LibreTranslate"""
        try:
            # Используем публичный инстанс LibreTranslate
            url = "https://libretranslate.de/translate"
            
            payload = {
                "q": text,
                "source": "auto",
                "target": target_lang,
                "format": "text"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('translatedText', text)
            else:
                logger.warning(f"Ошибка перевода: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при переводе текста: {e}")
            return None