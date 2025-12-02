import sqlite3
import logging
from typing import Optional, Dict, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class Database:
    """Класс для работы с базой данных пользователей и настроек"""
    
    def __init__(self, db_path: str = "infomonitor.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация таблиц базы данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        language TEXT DEFAULT 'ru',
                        timezone TEXT DEFAULT 'Europe/Moscow',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица настроек пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_settings (
                        user_id INTEGER,
                        setting_key TEXT,
                        setting_value TEXT,
                        PRIMARY KEY (user_id, setting_key),
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                    )
                ''')
                
                # Таблица предпочтений категорий
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_categories (
                        user_id INTEGER,
                        category TEXT,
                        PRIMARY KEY (user_id, category),
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                    )
                ''')
                
                # Таблица лайков/дизлайков новостей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS news_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        news_title TEXT,
                        news_link TEXT,
                        feedback_type TEXT CHECK (feedback_type IN ('like', 'dislike')),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                    )
                ''')
                
                # Таблица статистики просмотров новостей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS news_stats (
                        news_link TEXT PRIMARY KEY,
                        title TEXT,
                        category TEXT,
                        view_count INTEGER DEFAULT 0,
                        like_count INTEGER DEFAULT 0,
                        dislike_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("✅ База данных инициализирована")
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """Добавление нового пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, last_activity)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, username, first_name, last_name))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя {user_id}: {e}")
            return False
    
    def update_user_activity(self, user_id: int):
        """Обновление времени последней активности пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления активности пользователя {user_id}: {e}")
    
    def set_user_setting(self, user_id: int, key: str, value: str):
        """Установка настройки пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_settings (user_id, setting_key, setting_value)
                    VALUES (?, ?, ?)
                ''', (user_id, key, value))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка установки настройки {key} для пользователя {user_id}: {e}")
    
    def get_user_setting(self, user_id: int, key: str) -> Optional[str]:
        """Получение настройки пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT setting_value FROM user_settings 
                    WHERE user_id = ? AND setting_key = ?
                ''', (user_id, key))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка получения настройки {key} для пользователя {user_id}: {e}")
            return None
    
    def get_all_user_settings(self, user_id: int) -> Dict[str, str]:
        """Получение всех настроек пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT setting_key, setting_value FROM user_settings 
                    WHERE user_id = ?
                ''', (user_id,))
                return dict(cursor.fetchall())
        except Exception as e:
            logger.error(f"Ошибка получения настроек пользователя {user_id}: {e}")
            return {}
    
    def set_user_category_preference(self, user_id: int, category: str, enabled: bool):
        """Установка предпочтения категории для пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if enabled:
                    cursor.execute('''
                        INSERT OR IGNORE INTO user_categories (user_id, category)
                        VALUES (?, ?)
                    ''', (user_id, category))
                else:
                    cursor.execute('''
                        DELETE FROM user_categories WHERE user_id = ? AND category = ?
                    ''', (user_id, category))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка установки предпочтения категории {category} для пользователя {user_id}: {e}")
    
    def get_user_categories(self, user_id: int) -> List[str]:
        """Получение предпочтительных категорий пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT category FROM user_categories WHERE user_id = ?
                ''', (user_id,))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения категорий пользователя {user_id}: {e}")
            return []
    
    def add_news_feedback(self, user_id: int, news_title: str, news_link: str, feedback_type: str):
        """Добавление обратной связи для новости"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO news_feedback (user_id, news_title, news_link, feedback_type)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, news_title, news_link, feedback_type))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка добавления обратной связи: {e}")
    
    def update_news_stats(self, news_link: str, title: str, category: str, view_increment: int = 0, like_increment: int = 0, dislike_increment: int = 0):
        """Обновление статистики новости"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO news_stats 
                    (news_link, title, category, view_count, like_count, dislike_count, updated_at)
                    VALUES (?, ?, ?, 
                            COALESCE((SELECT view_count FROM news_stats WHERE news_link = ?), 0) + ?,
                            COALESCE((SELECT like_count FROM news_stats WHERE news_link = ?), 0) + ?,
                            COALESCE((SELECT dislike_count FROM news_stats WHERE news_link = ?), 0) + ?,
                            CURRENT_TIMESTAMP)
                ''', (news_link, title, category, news_link, view_increment, news_link, like_increment, news_link, dislike_increment))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления статистики новости: {e}")
    
    def get_news_stats(self, news_link: str) -> Optional[Dict]:
        """Получение статистики новости"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT view_count, like_count, dislike_count FROM news_stats WHERE news_link = ?
                ''', (news_link,))
                result = cursor.fetchone()
                if result:
                    return {
                        'view_count': result[0],
                        'like_count': result[1],
                        'dislike_count': result[2]
                    }
                return None
        except Exception as e:
            logger.error(f"Ошибка получения статистики новости: {e}")
            return None
    
    def get_user_feedback_stats(self, user_id: int) -> Dict[str, int]:
        """Получение статистики обратной связи пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT feedback_type, COUNT(*) FROM news_feedback 
                    WHERE user_id = ? GROUP BY feedback_type
                ''', (user_id,))
                stats = {'like': 0, 'dislike': 0}
                for feedback_type, count in cursor.fetchall():
                    stats[feedback_type] = count
                return stats
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователя {user_id}: {e}")
            return {'like': 0, 'dislike': 0}