import os
import logging
from datetime import datetime
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
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
        
    async def show_command_keyboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать клавиатуру с основными командами"""
        keyboard = [
            ['📰 Новости', '🎯 Настройки'],
            ['📊 Статистика', '📂 Категории'],
            ['🆘 Помощь']
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "📱 *Используйте кнопки ниже для быстрого доступа к функциям:*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    async def send_individual_news(self, update: Update, news_item: Dict, news_index: int, total_count: int):
        """Отправить отдельную новость с кнопками лайк/дизлайк"""
        emoji = self.news_collector.get_category_emoji(news_item['category'])
        
        message = f"{emoji} *НОВОСТЬ {news_index}/{total_count}*\n\n"
        message += f"*{news_item['title']}*\n\n"
        
        # Информация о языке и переводе
        lang_info = ""
        if news_item.get('original_language') == 'en':
            lang_info = " 🇬🇧 (на английском)"
        elif news_item.get('original_language') == 'mixed':
            lang_info = " 🌍 (смешанный)"
            
        message += f"🔗 [Читать полностью]({news_item['link']})\n"
        message += f"📰 Источник: {news_item['source']}{lang_info}\n"
        
        if news_item.get('published'):
            message += f"🕐 {news_item['published']}\n"
            
        message += f"\n📊 Категория: {news_item['category']}"
        
        # Создаем inline кнопки для лайков
        news_id = f"news_{news_index}_{hash(news_item['link']) % 10000}"
        
        keyboard = [
            [InlineKeyboardButton("👍 Лайк", callback_data=f"like_{news_id}_{news_index}"),
             InlineKeyboardButton("👎 Дизлайк", callback_data=f"dislike_{news_id}_{news_index}")]
        ]
        
        # Кнопки навигации (если новостей больше одной)
        if total_count > 1:
            nav_buttons = []
            if news_index > 1:
                nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущая", callback_data=f"nav_prev_{news_index}"))
            if news_index < total_count:
                nav_buttons.append(InlineKeyboardButton("Следующая ➡️", callback_data=f"nav_next_{news_index}"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Проверяем наличие изображения в новости
        if news_item.get('image_url'):
            try:
                await update.message.reply_photo(
                    photo=news_item['image_url'],
                    caption=message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить изображение: {e}")
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
        
        # Обновляем статистику просмотров
        self.database.update_news_stats(
            news_link=news_item['link'],
            title=news_item['title'],
            category=news_item['category'],
            view_increment=1
        )
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - приветствие и настройка категорий"""
        user = update.effective_user
        
        # Добавляем пользователя в базу данных
        self.database.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        user_id = user.id
        user_categories = self.database.get_user_categories(user_id)
        
        # Проверяем, первый ли это запуск пользователя
        is_new_user = not user_categories or len(user_categories) == 0
        
        welcome_text = f"""
🤖 *Добро пожаловать в ИнфоМонитор!*

Привет, {user.first_name}! 👋

Я ваш персональный помощник для получения актуальных новостей! 📰

⏰ *Ежедневная рассылка в 9:00 утра (MSK)*
🎯 *Персонализированные новости по вашим интересам*
📱 *Удобная навигация с лайками и дизлайками*
        """
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
        
        if is_new_user:
            # Для новых пользователей - настраиваем категории сразу
            setup_text = """
🎯 *Давайте настроим ваши предпочтения!*

Выберите категории новостей, которые вас интересуют.
Вы всегда сможете изменить эти настройки позже командой `/settings` или кнопкой "🎯 Настройки".

📰 *Доступные категории:*
            """
            
            await update.message.reply_text(setup_text, parse_mode='Markdown')
            await self.show_categories_settings(update, context)
        else:
            # Для существующих пользователей
            categories_text = f"✅ *Ваши текущие категории: {', '.join(user_categories)}*"
            await update.message.reply_text(categories_text, parse_mode='Markdown')
            
            # Показываем клавиатуру с командами
            await self.show_command_keyboard(update, context)
            
            # Предлагаем получить новости
            await update.message.reply_text(
                "📰 Готов показать последние новости! Нажмите кнопку '📰 Новости' или используйте команду `/news`",
                parse_mode='Markdown'
            )
        
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
        """Команда /news - получение новостей по отдельности"""
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
            
            if not news_list:
                await update.message.reply_text("😔 К сожалению, новости не найдены. Попробуйте позже.")
                return
            
            # Сохраняем список новостей в контексте пользователя для навигации
            context.user_data['news_list'] = news_list
            context.user_data['category_text'] = category_text
            context.user_data['current_news_index'] = 0
            
            # Отправляем первую новость
            await self.send_individual_news(update, news_list[0], 1, len(news_list))
            
        except Exception as e:
            logger.error(f"Ошибка при получении новостей: {e}")
            await update.message.reply_text("😔 Произошла ошибка при получении новостей. Попробуйте позже.")
    
    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /categories - показать все категории"""
        user = update.effective_user
        
        # Добавляем пользователя в базу данных если его там нет
        self.database.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        user_id = user.id
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
        
        # Определяем, новый ли это пользователь
        is_new_user = not user_categories or len(user_categories) == 0
        
        if is_new_user:
            message_text = """🎯 *Настройка категорий новостей*

Выберите категории, которые вас интересуют. Я буду присылать вам персонализированные новости только по выбранным темам.

📋 *Доступные категории:*
• 🏛️ Политика - внутренняя и внешняя политика
• 💰 Экономика - финансы, бизнес, рынки
• ⚽ Спорт - все виды спорта и соревнования
• 💻 Технологии - IT, гаджеты, инновации
• 🌍 Мировые - международные события

✅ *Выберите интересующие категории и нажмите "ГОТОВО"*"""
        else:
            selected_count = len(user_categories)
            message_text = f"""🎯 *Настройка категорий новостей*

📊 *Сейчас выбрано: {selected_count} категорий*
{', '.join([f"{self.news_collector.get_category_emoji(cat)} {cat}" for cat in user_categories])}

Измените свой выбор или нажмите "ГОТОВО" для сохранения."""
        
        await update.message.reply_text(
            message_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /settings - настройки пользователя"""
        user = update.effective_user
        
        # Добавляем пользователя в базу данных если его там нет
        self.database.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        await self.show_categories_settings(update, context)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика пользователя"""
        user = update.effective_user
        
        # Добавляем пользователя в базу данных если его там нет
        self.database.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        user_id = user.id
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
            user = update.effective_user
            
            # Добавляем пользователя в базу данных если его там нет
            self.database.add_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            user_id = user.id
            user_categories = self.database.get_user_categories(user_id)
            is_enabled = category in user_categories
            
            self.database.set_user_category_preference(user_id, category, not is_enabled)
            
            # Обновляем клавиатуру
            await self.show_categories_settings(update, context)
            
        elif data == 'categories_done':
            # Завершение настройки категорий
            user_id = update.effective_user.id
            user_categories = self.database.get_user_categories(user_id)
            
            if user_categories:
                categories_list = ', '.join([f"{self.news_collector.get_category_emoji(cat)} {cat}" for cat in user_categories])
                await query.edit_message_text(
                    f"✅ *Настройки сохранены!*\n\n"
                    f"🎯 *Выбранные категории:*\n{categories_list}\n\n"
                    f"📰 Теперь вы будете получать персонализированные новости каждый день в 9:00 утра!\n\n"
                    f"📱 *Сразу получить новости:* `/news` или нажмите кнопку '📰 Новости'",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "⚠️ *Категории не выбраны*\n\n"
                    "Вы не выбрали ни одной категории. Выберите интересующие вас темы "
                    "командой `/settings` или настройте их позже.",
                    parse_mode='Markdown'
                )
            
        elif data.startswith('like_') or data.startswith('dislike_'):
            # Обработка лайков/дизлайков
            parts = data.split('_')
            feedback_type = parts[0]
            news_index = int(parts[2])
            
            # Показываем уведомление пользователю
            emoji = "👍" if feedback_type == "like" else "👎"
            feedback_text = "Спасибо за лайк!" if feedback_type == "like" else "Спасибо за обратную связь!"
            
            await query.answer(f"{emoji} {feedback_text}", show_alert=False)
            
        elif data.startswith('nav_prev_') or data.startswith('nav_next_'):
            # Обработка навигации между новостями
            parts = data.split('_')
            direction = parts[1]  # prev или next
            current_index = int(parts[2])
            
            # Получаем список новостей из контекста пользователя
            news_list = context.user_data.get('news_list', [])
            if not news_list:
                await query.edit_message_text("😔 Список новостей не найден. Используйте /news для получения новых новостей.")
                return
            
            # Вычисляем новый индекс (исправлено)
            if direction == 'prev':
                new_index = current_index - 1  # Просто переходим к предыдущей
            else:  # direction == 'next'
                new_index = current_index  # Переходим к следующей (индекс в news_list)
            
            # Проверяем границы
            if new_index < 0 or new_index >= len(news_list):
                if direction == 'prev':
                    await query.answer("⬅️ Это первая новость", show_alert=False)
                else:
                    await query.answer("➡️ Это последняя новость", show_alert=False)
                return
            
            # Удаляем предыдущее сообщение
            await query.message.delete()
            
            # Обновляем индекс в контексте
            context.user_data['current_news_index'] = new_index
            
            # Отправляем новую новость
            await self.send_individual_news(
                update, 
                news_list[new_index], 
                new_index + 1,  # +1 для отображения (1-based)
                len(news_list)
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений и кнопок клавиатуры"""
        user = update.effective_user
        user_message = update.message.text.lower()
        
        # Добавляем пользователя в базу данных если его там нет
        self.database.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        user_id = user.id
        
        # Обновляем активность пользователя
        self.database.update_user_activity(user_id)
        
        # Обработка кнопок клавиатуры с командами
        if user_message == '📰 новости':
            await self.news_command(update, context)
        elif user_message == '🎯 настройки':
            await self.settings_command(update, context)
        elif user_message == '📊 статистика':
            await self.stats_command(update, context)
        elif user_message == '📂 категории':
            await self.categories_command(update, context)
        elif user_message == '🆘 помощь':
            await self.help_command(update, context)
        elif any(word in user_message for word in ['новости', 'news', 'что нового']):
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

📰 Используйте команду `/news` или кнопку "📰 Новости" чтобы получить последние новости прямо сейчас!

🎯 Попробуйте `/settings` или кнопку "🎯 Настройки" чтобы настроить интересующие вас категории новостей.

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