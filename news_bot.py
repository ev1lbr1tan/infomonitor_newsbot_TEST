import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

from news_collector import NewsCollector

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class InfoMonitor:
    """Основной класс Telegram бота ИнфоМонитор"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.news_collector = NewsCollector()
        self.scheduler = AsyncIOScheduler()
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        welcome_text = """
🤖 *Добро пожаловать в ИнфоМонитор!*

Я буду присылать вам актуальные новости каждый день в 9:00 утра (MSK).

📰 *Доступные команды:*
• /news - получить новости прямо сейчас
• /help - справка по командам
• /settings - настройки бота

📊 Источники новостей:
• РИА Новости
• ТАСС
• Лента.ру
• Ведомости
• РБК

Бот работает 24/7 и автоматически собирает последние новости!
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
🔧 *Справка по командам ИнфоМонитора*

📰 *Основные команды:*
• `/news` - получить последние новости
• `/start` - начать работу с ботом
• `/help` - показать эту справку

⏰ *Автоматическая рассылка:*
Новости приходят каждый день в 9:00 утра (MSK)

📊 *Источники новостей:*
• РИА Новости
• ТАСС  
• Лента.ру
• Ведомости
• РБК

🤔 *Нужна помощь?*
Просто напишите любое сообщение или используйте команду /news
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /news - получение новостей по запросу"""
        await update.message.reply_text("📡 Собираю последние новости...")
        
        try:
            news_list = self.news_collector.get_latest_news(limit=10)
            message = self.news_collector.format_news_message(news_list)
            await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Ошибка при получении новостей: {e}")
            await update.message.reply_text("😔 Произошла ошибка при получении новостей. Попробуйте позже.")
            
    async def daily_news_job(self):
        """Задача для ежедневной отправки новостей"""
        try:
            # Получаем всех пользователей, которые запустили бота
            # В реальном приложении здесь должна быть база данных
            logger.info("Отправка ежедневных новостей...")
            
            news_list = self.news_collector.get_latest_news(limit=5)
            message = self.news_collector.format_news_message(news_list)
            message = f"🌅 *Доброе утро! ИнфоМонитор приносит свежие новости:*\n\n" + message
            
            # Здесь должен быть код для отправки всем подписчикам
            # Для демонстрации просто логируем
            logger.info(f"Подготовлено сообщение с {len(news_list)} новостями")
            
        except Exception as e:
            logger.error(f"Ошибка при ежедневной отправке новостей: {e}")
            
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений"""
        user_message = update.message.text.lower()
        
        if any(word in user_message for word in ['новости', 'news', 'что нового']):
            await self.news_command(update, context)
        elif any(word in user_message for word in ['помощь', 'help', 'справка']):
            await self.help_command(update, context)
        else:
            response = """
🤖 Я ИнфоМонитор! 

📰 Используйте команду `/news` чтобы получить последние новости прямо сейчас!

⏰ Новости также приходят автоматически каждый день в 9:00 утра (MSK).
            """
            await update.message.reply_text(response, parse_mode='Markdown')
            
    def setup_scheduler(self):
        """Настройка планировщика для ежедневной отправки новостей"""
        # Запускаем ежедневно в 9:00 MSK (6:00 UTC)
        self.scheduler.add_job(
            self.daily_news_job,
            CronTrigger(hour=6, minute=0),  # 9:00 MSK = 6:00 UTC
            id='daily_news'
        )
        
    def run(self):
        """Запуск бота"""
        # Создаем приложение
        application = Application.builder().token(self.bot_token).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("news", self.news_command))
        
        # Добавляем обработчик сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Настраиваем планировщик
        self.setup_scheduler()
        self.scheduler.start()
        
        logger.info("🤖 Бот запущен...")
        logger.info("📅 Ежедневная рассылка новостей настроена на 9:00 MSK")
        
        # Запускаем бота
        application.run_polling()

def main():
    """Главная функция"""
    # Получаем токен бота из переменных окружения
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not BOT_TOKEN:
        print("❌ Ошибка: Установите переменную окружения TELEGRAM_BOT_TOKEN")
        print("💡 Создайте бота через @BotFather и получите токен")
        return
        
    # Создаем и запускаем бота
    bot = InfoMonitor(BOT_TOKEN)
    bot.run()

if __name__ == '__main__':
    main()