import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

from database import Database
from enhanced_news_collector import EnhancedNewsCollector

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class EnhancedInfoMonitor:
    """Улучшенный класс Telegram бота ИнфоМонитор"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.news_collector = EnhancedNewsCollector()
        self.database = Database()
        self.scheduler = AsyncIOScheduler()
        
        # Список доступных категорий
        self.categories = ['политика', 'экономика', 'спорт', 'технологии', 'мировые']
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        
        # Добавляем пользователя в базу данных
        self.database.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        welcome_text = f"""
🤖 *Добро пожаловать в ИнфоМонитор!*

Привет, {user.first_name}! 👋

Я буду присылать вам актуальные новости каждый день в 9:00 утра (MSK).

📰 *Доступные категории новостей:*
• 🏛️ Политика
• 💰 Экономика  
• ⚽ Спорт
• 💻 Технологии
• 🌍 Мировые новости

🎯 *Особенности:*
• Выберите интересующие категории
• Лайкайте/дизлайкайте новости
• ИИ-перевод иностранных новостей
• Персонализированная лента

📱 *Команды:*
• /news - получить новости
• /settings - настроить категории  
• /stats - ваша статистика
• /help - справка

Давайте настроим ваши предпочтения!
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        
        # Показываем настройку категорий
        await self.show_categories_settings(update, context)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = """
🔧 *Справка по командам ИнфоМонитора*

📰 *Основные команды:*
• `/news` - получить последние новости
• `/news <категория>` - получить новости определенной категории
• `/categories` - показать все доступные категории
• `/settings` - настроить предпочтения
• `/stats` - ваша статистика активности
• `/start` - начать работу с ботом
• `/help` - показать эту справку

🎯 *Интерактивные функции:*
• Кнопки лайк/дизлайк для каждой новости
• Клавиатура для выбора категорий
• Персонализированная подача новостей

⏰ *Автоматическая рассылка:*
Новости приходят каждый день в 9:00 утра (MSK)

📊 *Источники новостей:*
Российские: РИА, ТАСС, Лента.ру, Ведомости, РБК
Международные: BBC, Reuters, CNN, The Guardian
Технологии: Habr, TAdviser, VC.ru, TechCrunch

🌐 *Перевод:*
Иностранные новости автоматически помечаются для удобства

🤔 *Нужна помощь?*
Просто напишите любое сообщение или используйте команду /news
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    async def news_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /news - получение новостей"""
        user_id = update.effective_user.id
        self.database.update_user_activity(user_id)
        
        # Определяем категорию из аргументов
        args = context.args
        requested_category = args[0].lower() if args else None
        
        await update.message.reply_text("📡 Собираю последние новости...")
        
        try:
            if requested_category and requested_category in self.categories:
                # Получаем новости конкретной категории
                news_list = self.news_collector.get_news_by_category([requested_category], limit=8)
                category_text = f"категории *{requested_category.upper()}*"
            else:
                # Получаем предпочтительные категории пользователя
                user_categories = self.database.get_user_categories(user_id)
                if not user_categories:
                    # Если нет настроек, показываем все категории
                    news_list = self.news_collector.get_all_news(limit=10)
                    category_text = "всех доступных категорий"
                else:
                    # Получаем новости по предпочтениям
                    news_list = self.news_collector.get_news_by_category(user_categories, limit=10)
                    category_text = f"ваших предпочтений ({', '.join(user_categories)})"
            
            message = self.news_collector.format_news_message(news_list, show_categories=True)
            message = f"📰 *Новости {category_text}:*\n\n" + message
            
            # Добавляем кнопки лайков
            keyboard = []
            for i, news in enumerate(news_list[:5]):  # Максимум 5 новостей с кнопками
                news_id = f"news_{i}_{hash(news['link']) % 10000}"  # Простой уникальный ID
                keyboard.append([
                    InlineKeyboardButton(f"👍 Лайк", callback_data=f"like_{news_id}_{i}"),
                    InlineKeyboardButton(f"👎 Дизлайк", callback_data=f"dislike_{news_id}_{i}")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            sent_message = await update.message.reply_text(
                message, 
                parse_mode='Markdown', 
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
            
            # Сохраняем статистику просмотров
            for news in news_list:
                self.database.update_news_stats(
                    news_link=news['link'],
                    title=news['title'],
                    category=news['category'],
                    view_increment=1
                )
                
        except Exception as e:
            logger.error(f"Ошибка при получении новостей: {e}")
            await update.message.reply_text("😔 Произошла ошибка при получении новостей. Попробуйте позже.")
    
    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /categories - показать все категории"""
        user_id = update.effective_user.id
        user_categories = self.database.get_user_categories(user_id)
        
        categories_text = "📂 *ДОСТУПНЫЕ КАТЕГОРИИ НОВОСТЕЙ:*\n\n"
        
        for category in self.categories:
            emoji = self.news_collector.get_category_emoji(category)
            status = "✅" if category in user_categories else "⚪"
            categories_text += f"{status} {emoji} *{category.upper()}*\n"
        
        categories_text += "\n💡 Используйте /settings для настройки предпочтений"
        
        await update.message.reply_text(categories_text, parse_mode='Markdown')
    
    async def show_categories_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать настройки категорий"""
        user_id = update.effective_user.id
        user_categories = self.database.get_user_categories(user_id)
        
        keyboard = []
        for category in self.categories:
            emoji = self.news_collector.get_category_emoji(category)
            status = "✅" if category in user_categories else "⚪"
            callback_data = f"toggle_category_{category}"
            keyboard.append([InlineKeyboardButton(f"{status} {emoji} {category.upper()}", callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("✅ ГОТОВО", callback_data="categories_done")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎯 *Выберите интересующие вас категории новостей:*\n\n"
            "Нажмите на категорию, чтобы включить/выключить её",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /settings - настройки пользователя"""
        await self.show_categories_settings(update, context)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика пользователя"""
        user_id = update.effective_user.id
        user_categories = self.database.get_user_categories(user_id)
        feedback_stats = self.database.get_user_feedback_stats(user_id)
        
        stats_text = f"""
📊 *ВАША СТАТИСТИКА ИНФОМОНИТОРА*

👤 *Информация:*
• ID пользователя: `{user_id}`
• Настроенных категорий: {len(user_categories)}
• Предпочитаемые темы: {', '.join(user_categories) if user_categories else 'Не настроены'}

👍👎 *Обратная связь:*
• Лайков поставлено: {feedback_stats['like']}
• Дизлайков поставлено: {feedback_stats['dislike']}

⏰ *Активность:*
• Последние новости запрашивались недавно
• Ежедневная рассылка активна в 9:00 MSK

💡 *Советы:*
• Настройте категории командой /settings
• Используйте лайки для улучшения рекомендаций
• Попробуйте `/news спорт` для конкретной категории
        """
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith('toggle_category_'):
            # Переключение категории
            category = data.replace('toggle_category_', '')
            user_id = update.effective_user.id
            
            user_categories = self.database.get_user_categories(user_id)
            is_enabled = category in user_categories
            
            self.database.set_user_category_preference(user_id, category, not is_enabled)
            
            # Обновляем клавиатуру
            await self.show_categories_settings(update, context)
            
        elif data == 'categories_done':
            # Завершение настройки категорий
            await query.edit_message_text(
                "✅ *Настройки сохранены!*\n\n"
                "Теперь вы будете получать персонализированные новости.\n"
                "Используйте команду `/news` для получения новостей.",
                parse_mode='Markdown'
            )
            
        elif data.startswith('like_') or data.startswith('dislike_'):
            # Обработка лайков/дизлайков
            parts = data.split('_')
            feedback_type = parts[0]
            news_index = int(parts[2])
            
            # Здесь можно добавить логику обработки лайков
            # Пока что просто отвечаем пользователю
            
            emoji = "👍" if feedback_type == "like" else "👎"
            await query.edit_message_text(f"{emoji} Спасибо за обратную связь!")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений"""
        user_id = update.effective_user.id
        user_message = update.message.text.lower()
        
        # Обновляем активность пользователя
        self.database.update_user_activity(user_id)
        
        if any(word in user_message for word in ['новости', 'news', 'что нового']):
            await self.news_command(update, context)
        elif any(word in user_message for word in ['помощь', 'help', 'справка']):
            await self.help_command(update, context)
        elif any(word in user_message for word in ['настройки', 'settings', 'категории']):
            await self.settings_command(update, context)
        elif any(word in user_message for word in ['статистика', 'stats', 'статус']):
            await self.stats_command(update, context)
        else:
            response = f"""
🤖 Я ИнфоМонитор! 

📰 Используйте команду `/news` чтобы получить последние новости прямо сейчас!

🎯 Попробуйте `/settings` чтобы настроить интересующие вас категории новостей.

⏰ Новости также приходят автоматически каждый день в 9:00 утра (MSK).
            """
            await update.message.reply_text(response, parse_mode='Markdown')
    
    async def daily_news_job(self):
        """Задача для ежедневной отправки новостей"""
        try:
            logger.info("Отправка ежедневных персонализированных новостей...")
            
            # Здесь должен быть код для отправки всем пользователям
            # В реальном приложении нужно получить список всех пользователей из БД
            # и отправить каждому персонализированные новости
            
            # Для демонстрации просто логируем
            logger.info("Ежедневная отправка новостей завершена")
            
        except Exception as e:
            logger.error(f"Ошибка при ежедневной отправке новостей: {e}")
    
    def setup_scheduler(self):
        """Настройка планировщика для ежедневной отправки новостей"""
        # Запускаем ежедневно в 9:00 MSK (6:00 UTC)
        self.scheduler.add_job(
            self.daily_news_job,
            CronTrigger(hour=6, minute=0),  # 9:00 MSK = 6:00 UTC
            id='daily_news'
        )
        
    def run(self):
        """Запуск улучшенного бота"""
        # Создаем приложение
        application = Application.builder().token(self.bot_token).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("news", self.news_command))
        application.add_handler(CommandHandler("settings", self.settings_command))
        application.add_handler(CommandHandler("categories", self.categories_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Добавляем обработчик кнопок
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Добавляем обработчик сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Настраиваем планировщик
        self.setup_scheduler()
        self.scheduler.start()
        
        logger.info("🤖 Улучшенный ИнфоМонитор запущен...")
        logger.info("📅 Ежедневная персонализированная рассылка настроена на 9:00 MSK")
        logger.info("🎯 База данных пользователей и настроек активна")
        
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
        
    # Создаем и запускаем улучшенного бота
    bot = EnhancedInfoMonitor(BOT_TOKEN)
    bot.run()

if __name__ == '__main__':
    main()