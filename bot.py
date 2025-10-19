"""Main Telegram bot for China IT News channel."""

import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import pytz

import config
from rss_collector import RSSCollector
from generator import get_generator, generate_vacancy_from_freeform
from publisher import get_publisher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FSM States for vacancy submission
class VacancyStates(StatesGroup):
    waiting_for_position = State()
    waiting_for_company = State()
    waiting_for_location = State()
    waiting_for_salary = State()
    waiting_for_experience = State()
    waiting_for_description = State()
    waiting_for_requirements = State()
    waiting_for_benefits = State()
    waiting_for_contact = State()
    confirming_vacancy = State()
    # Free-form vacancy flow
    waiting_for_freeform = State()
    confirming_freeform = State()

# FSM States for advertisement submission
class AdStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_brand = State()
    waiting_for_description = State()
    waiting_for_offer = State()
    waiting_for_link = State()
    waiting_for_contact = State()
    confirming_ad = State()

class ChinaITBot:
    def __init__(self):
        self.bot = Bot(token=config.BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone(config.TIMEZONE))
        
        # Initialize components
        self.rss_collector = RSSCollector()
        self.generator = get_generator()
        self.publisher = get_publisher()
        
        # Setup handlers
        self.setup_handlers()
        
        # Setup scheduler
        self.setup_scheduler()

    def setup_handlers(self):
        """Setup bot message and callback handlers."""
        
        # Command handlers
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("help"))(self.cmd_help)
        self.dp.message(Command("post_vacancy"))(self.cmd_post_vacancy)
        self.dp.message(Command("post_vacancy_free"))(self.cmd_post_vacancy_free)
        self.dp.message(Command("post_ad"))(self.cmd_post_ad)
        self.dp.message(Command("post_now"))(self.cmd_post_now)
        self.dp.message(Command("status"))(self.cmd_status)
        
        # Vacancy submission FSM handlers
        self.dp.message(StateFilter(VacancyStates.waiting_for_position))(self.process_position)
        self.dp.message(StateFilter(VacancyStates.waiting_for_company))(self.process_company)
        self.dp.message(StateFilter(VacancyStates.waiting_for_location))(self.process_location)
        self.dp.message(StateFilter(VacancyStates.waiting_for_salary))(self.process_salary)
        self.dp.message(StateFilter(VacancyStates.waiting_for_experience))(self.process_experience)
        self.dp.message(StateFilter(VacancyStates.waiting_for_description))(self.process_description)
        self.dp.message(StateFilter(VacancyStates.waiting_for_requirements))(self.process_requirements)
        self.dp.message(StateFilter(VacancyStates.waiting_for_benefits))(self.process_benefits)
        self.dp.message(StateFilter(VacancyStates.waiting_for_contact))(self.process_contact)
        # Free-form vacancy text handler
        self.dp.message(StateFilter(VacancyStates.waiting_for_freeform))(self.process_freeform_text)

        # Advertisement FSM handlers
        self.dp.message(StateFilter(AdStates.waiting_for_title))(self.process_ad_title)
        self.dp.message(StateFilter(AdStates.waiting_for_brand))(self.process_ad_brand)
        self.dp.message(StateFilter(AdStates.waiting_for_description))(self.process_ad_description)
        self.dp.message(StateFilter(AdStates.waiting_for_offer))(self.process_ad_offer)
        self.dp.message(StateFilter(AdStates.waiting_for_link))(self.process_ad_link)
        self.dp.message(StateFilter(AdStates.waiting_for_contact))(self.process_ad_contact)
        
        # Callback handlers
        self.dp.callback_query(F.data == "confirm_vacancy")(self.confirm_vacancy)
        self.dp.callback_query(F.data == "edit_vacancy")(self.edit_vacancy)
        self.dp.callback_query(F.data == "cancel_vacancy")(self.cancel_vacancy)
        self.dp.callback_query(F.data.startswith("polish_"))(self.handle_polish_choice)
        # Free-form callbacks
        self.dp.callback_query(F.data == "confirm_freeform_vacancy")(self.confirm_freeform_vacancy)
        self.dp.callback_query(F.data == "edit_freeform_vacancy")(self.edit_freeform_vacancy)
        # Advertisement callbacks
        self.dp.callback_query(F.data == "confirm_ad")(self.confirm_ad)
        self.dp.callback_query(F.data == "edit_ad")(self.edit_ad)

    def setup_scheduler(self):
        """Setup scheduled tasks."""
        # Parse publish time
        hour, minute = map(int, config.PUBLISH_TIME.split(':'))
        
        # Schedule hourly news posting (one article per hour)
        if getattr(config, 'ENABLE_HOURLY_POST', True):
            self.scheduler.add_job(
                self.hourly_news_job,
                IntervalTrigger(minutes=10),
                id='hourly_news',
                name='Hourly News Posting',
                replace_existing=True
            )
            logger.info("📅 Scheduled news posting: every 10 minutes")
        
        # Optionally schedule daily news posting (disabled by default)
        if getattr(config, 'ENABLE_DAILY_POST', False):
            self.scheduler.add_job(
                self.daily_news_job,
                CronTrigger(hour=hour, minute=minute),
                id='daily_news',
                name='Daily News Posting',
                replace_existing=True
            )
            logger.info(f"📅 Scheduled daily news posting at {config.PUBLISH_TIME} {config.TIMEZONE}")

    async def daily_news_job(self):
        """Daily job to collect and publish news."""
        try:
            logger.info("🔄 Starting daily news collection...")
            # Collect RSS articles
            articles = await self.rss_collector.collect_all_feeds()
            if articles:
                max_count = getattr(config, 'MAX_ARTICLES_PER_DAY', 3)
                published = 0
                for article in articles[:max_count]:
                    ok = await self.publisher.publish_article(article)
                    if ok:
                        # Mark as seen only after successful publish
                        self.rss_collector.seen_articles.add(article['link'])
                        self.rss_collector.save_seen_articles()
                        published += 1
                if published > 0:
                    logger.info(f"✅ Published {published} article(s) as individual posts")
                else:
                    logger.error("❌ Failed to publish articles")
                    await self.notify_admin("Ошибка публикации новостей по одной статье")
            else:
                logger.info("📰 No new articles found today")
        except Exception as e:
            logger.error(f"❌ Error in daily news job: {e}")
            await self.notify_admin(f"Ошибка в ежедневной задаче: {str(e)}")

    async def hourly_news_job(self):
        """Hourly job to publish exactly one article."""
        try:
            logger.info("🔄 Hourly run: collecting latest article...")
            articles = await self.rss_collector.collect_all_feeds()
            if articles:
                article = articles[0]
                ok = await self.publisher.publish_article(article)
                if ok:
                    # Mark as seen only after successful publish
                    self.rss_collector.seen_articles.add(article['link'])
                    self.rss_collector.save_seen_articles()
                    logger.info("✅ Published 1 article (hourly)")
                else:
                    logger.error("❌ Failed to publish hourly article")
                    await self.notify_admin("Ошибка публикации ежечасной статьи")
            else:
                logger.info("📰 Hourly: no new articles")
        except Exception as e:
            logger.error(f"❌ Error in hourly news job: {e}")
            await self.notify_admin(f"Ошибка в ежечасной задаче: {str(e)}")

    async def notify_admin(self, message: str):
        """Send notification to admin (you can customize this)."""
        try:
            # For now, just log the error. You can extend this to send DM to admin
            logger.warning(f"🔔 Admin notification: {message}")
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")

    # Command handlers
    async def cmd_start(self, message: Message):
        """Handle /start command."""
        welcome_text = """🇨🇳 **Добро пожаловать в China IT News Bot!**

Этот бот управляет каналом с новостями IT и вакансиями в Китае.

**Доступные команды:**
/post_vacancy - Добавить новую вакансию
/post_vacancy_free - Вакансия в свободной форме
/post_ad - Добавить рекламный пост
/post_now - Опубликовать новости сейчас (только для админов)
/status - Проверить статус бота
/help - Показать эту справку

**Автоматические функции:**
📰 Ежедневная публикация новостей в {publish_time}
🤖 AI-генерация контента
📊 Сбор новостей из проверенных источников

Для добавления вакансии используйте /post_vacancy или /post_vacancy_free""".format(publish_time=config.PUBLISH_TIME)
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="/post_vacancy"), KeyboardButton(text="/post_vacancy_free")],
                [KeyboardButton(text="/post_ad"), KeyboardButton(text="/status")],
                [KeyboardButton(text="/help")],
            ],
            resize_keyboard=True,
            input_field_placeholder="Выберите команду"
        )
        await message.answer(welcome_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    async def cmd_help(self, message: Message):
        """Handle /help command."""
        help_text = """📖 **Справка по боту China IT News**

**Команды:**
• `/start` - Начать работу с ботом
• `/post_vacancy` - Добавить новую вакансию
• `/post_vacancy_free` - Добавить вакансию в свободной форме
• `/post_ad` - Добавить рекламный пост
• `/post_now` - Принудительно опубликовать новости
• `/status` - Проверить статус системы

**Как добавить вакансию:**
1. Используйте команду `/post_vacancy`
   Бот по шагам спросит основные поля и покажет предпросмотр. Можно улучшить текст через AI.

Или отправьте свободный текст через `/post_vacancy_free` — я структурирую его по единому шаблону и прикреплю ссылку, если она есть в тексте.

**Как добавить рекламу:**
Используйте `/post_ad` — по шагам добавим заголовок, бренд, описание, оффер, ссылку и контакт, покажу предпросмотр и вы подтвердите публикацию."""
        await message.answer(help_text, parse_mode=ParseMode.HTML)

    async def cmd_status(self, message: Message):
        """Handle /status command."""
        try:
            # Check components status
            status_text = "🔍 **Статус системы:**\n\n"
            
            # Check publisher connection
            publisher_ok = await self.publisher.test_connection()
            status_text += f"📡 Telegram: {'✅' if publisher_ok else '❌'}\n"
            
            # Check scheduler
            scheduler_running = self.scheduler.running
            status_text += f"⏰ Планировщик: {'✅' if scheduler_running else '❌'}\n"
            
            # Check LLM
            try:
                llm_client = self.generator.llm_client
                status_text += f"🤖 LLM ({config.LLM_PROVIDER}): ✅\n"
            except Exception:
                status_text += f"🤖 LLM: ❌\n"
            
            # Show next scheduled job
            if scheduler_running:
                jobs = self.scheduler.get_jobs()
                if jobs:
                    next_job = min(jobs, key=lambda j: j.next_run_time)
                    status_text += f"\n⏭️ Следующая публикация: {next_job.next_run_time.strftime('%d.%m.%Y %H:%M')}"
            
            status_text += f"\n\n📊 Конфигурация:\n"
            status_text += f"• Канал: {config.CHANNEL_ID}\n"
            status_text += f"• Время публикации: {config.PUBLISH_TIME}\n"
            status_text += f"• LLM провайдер: {config.LLM_PROVIDER}\n"
            status_text += f"• Макс. статей в день: {config.MAX_ARTICLES_PER_DAY}\n"
            # AI polish flags
            ai_vac = 'Да' if getattr(config, 'AI_POLISH_ENABLE_VACANCY', True) else 'Нет'
            ai_ad = 'Да' if getattr(config, 'AI_POLISH_ENABLE_AD', True) else 'Нет'
            status_text += f"• Полировка вакансий AI: {ai_vac}\n"
            status_text += f"• Полировка рекламы AI: {ai_ad}"
            
        except Exception as e:
            status_text = f"❌ Ошибка проверки статуса: {str(e)}"
        
        await message.answer(status_text, parse_mode=ParseMode.HTML)

    async def cmd_post_now(self, message: Message):
        """Handle /post_now command (admin only)."""
        # Admin check based on config.ADMIN_IDS
        if message.from_user.id not in config.ADMIN_IDS:
            await message.answer("❌ Эта команда доступна только администраторам.")
            return
        await message.answer("🔄 Запускаю сбор и публикацию одной новости (ежечасной логикой)...")
        try:
            await self.hourly_news_job()
            await message.answer("✅ Новость опубликована!")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)}")

    async def cmd_post_vacancy(self, message: Message, state: FSMContext):
        """Start vacancy posting process."""
        await state.set_state(VacancyStates.waiting_for_position)
        await message.answer(
            "💼 **Добавление новой вакансии**\n\n"
            "Давайте заполним информацию о вакансии по шагам.\n\n"
            "**Шаг 1/9:** Введите название позиции\n"
            "Например: *Senior Python Developer*",
            parse_mode=ParseMode.HTML
        )

    async def cmd_post_vacancy_free(self, message: Message, state: FSMContext):
        """Start free-form vacancy posting process."""
        await state.set_state(VacancyStates.waiting_for_freeform)
        await message.answer(
            "💼 **Свободная вакансия**\n\n"
            "Пришлите одним сообщением текст вакансии в свободной форме.\n"
            "Можно включить любую информацию: позицию, компанию, локацию, зарплату, требования, условия, контакт.\n"
            "Если есть ссылка на вакансию — вставьте её прямо в текст.",
            parse_mode=ParseMode.HTML
        )

    async def cmd_post_ad(self, message: Message, state: FSMContext):
        """Start advertisement posting process."""
        await state.set_state(AdStates.waiting_for_title)
        await message.answer(
            "📣 **Добавление рекламного поста**\n\n"
            "Заполним данные по шагам.\n\n"
            "**Шаг 1/6:** Введите заголовок\n"
            "Например: *Курс по Python со скидкой 30%*",
            parse_mode=ParseMode.HTML
        )

    async def process_freeform_text(self, message: Message, state: FSMContext):
        """Handle incoming free-form vacancy text, normalize via LLM, and show preview."""
        await message.answer("🔄 Обрабатываю текст вакансии...")
        try:
            normalized = await generate_vacancy_from_freeform(message.text)
            await state.update_data(freeform_post=normalized)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Опубликовать", callback_data="confirm_freeform_vacancy"),
                    InlineKeyboardButton(text="✏️ Изменить текст", callback_data="edit_freeform_vacancy")
                ],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_vacancy")]
            ])
            await message.answer(f"📋 **Предпросмотр вакансии:**\n\n{normalized}", reply_markup=keyboard, parse_mode=ParseMode.HTML)
            await state.set_state(VacancyStates.confirming_freeform)
        except Exception as e:
            await message.answer(f"❌ Ошибка обработки: {str(e)}")
            await state.clear()

    async def process_ad_title(self, message: Message, state: FSMContext):
        await state.update_data(ad_title=message.text)
        await state.set_state(AdStates.waiting_for_brand)
        await message.answer(
            "**Шаг 2/6:** Введите бренд/компанию\n"
            "Например: *EduTech*",
            parse_mode=ParseMode.HTML
        )

    async def process_ad_brand(self, message: Message, state: FSMContext):
        await state.update_data(ad_brand=message.text)
        await state.set_state(AdStates.waiting_for_description)
        await message.answer(
            "**Шаг 3/6:** Введите описание\n"
            "Кратко о продукте/услуге",
            parse_mode=ParseMode.HTML
        )

    async def process_ad_description(self, message: Message, state: FSMContext):
        await state.update_data(ad_description=message.text)
        await state.set_state(AdStates.waiting_for_offer)
        await message.answer(
            "**Шаг 4/6:** Введите оффер/преимущества\n"
            "Например: *Скидка 30%, рассрочка, сертификат*",
            parse_mode=ParseMode.HTML
        )

    async def process_ad_offer(self, message: Message, state: FSMContext):
        await state.update_data(ad_offer=message.text)
        await state.set_state(AdStates.waiting_for_link)
        await message.answer(
            "**Шаг 5/6:** Введите ссылку (если есть)\n"
            "Например: *https://example.com*",
            parse_mode=ParseMode.HTML
        )

    async def process_ad_link(self, message: Message, state: FSMContext):
        await state.update_data(ad_link=message.text)
        await state.set_state(AdStates.waiting_for_contact)
        await message.answer(
            "**Шаг 6/6:** Введите контакт\n"
            "Например: *@manager* или *sales@example.com*",
            parse_mode=ParseMode.HTML
        )

    async def process_ad_contact(self, message: Message, state: FSMContext):
        await state.update_data(ad_contact=message.text)
        data = await state.get_data()
        preview = (
            "📣 **Рекламный пост**\n\n"
            f"🔖 **Заголовок:** {data.get('ad_title','')}\n"
            f"🏷️ **Бренд:** {data.get('ad_brand','')}\n"
            f"📝 **Описание:** {data.get('ad_description','')}\n"
            f"🎁 **Оффер:** {data.get('ad_offer','')}\n"
            f"🔗 **Ссылка:** {data.get('ad_link','—')}\n"
            f"📞 **Контакт:** {data.get('ad_contact','')}\n"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Опубликовать", callback_data="confirm_ad"),
                InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_ad")
            ],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_vacancy")]
        ])
        await message.answer(preview, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await state.set_state(AdStates.confirming_ad)

    async def confirm_freeform_vacancy(self, callback: CallbackQuery, state: FSMContext):
        """Publish normalized free-form vacancy."""
        data = await state.get_data()
        post = data.get("freeform_post")
        if not post:
            await callback.message.edit_text("❌ Нет готового текста для публикации.")
            await state.clear()
            return
        try:
            # Optional AI polish based on config
            final_text = post
            if getattr(config, 'AI_POLISH_ENABLE_VACANCY', True):
                try:
                    final_text = await self.generator.polish_vacancy_text(post)
                except Exception:
                    final_text = post
            ok = await self.publisher.publish_vacancy(final_text)
            if ok:
                await callback.message.edit_text("✅ Вакансия опубликована!")
            else:
                await callback.message.edit_text("❌ Не удалось опубликовать вакансию.")
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка публикации: {str(e)}")
        await state.clear()

    async def edit_freeform_vacancy(self, callback: CallbackQuery, state: FSMContext):
        """Return to free-form input for editing."""
        await callback.message.edit_text(
            "✏️ Отправьте заново текст вакансии одним сообщением.\n\n"
            "Если есть ссылка — вставьте её в текст.",
            parse_mode=ParseMode.HTML
        )
        await state.set_state(VacancyStates.waiting_for_freeform)

    async def confirm_ad(self, callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        try:
            # Generate ad post with optional AI polish from config
            use_ai = getattr(config, 'AI_POLISH_ENABLE_AD', True)
            post = await self.generator.generate_ad_post(data, use_ai_polish=use_ai)
            ok = await self.publisher.publish_vacancy(post)
            if ok:
                await callback.message.edit_text("✅ Рекламный пост опубликован!")
            else:
                await callback.message.edit_text("❌ Не удалось опубликовать пост.")
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка публикации: {str(e)}")
        await state.clear()

    async def edit_ad(self, callback: CallbackQuery, state: FSMContext):
        await callback.message.edit_text(
            "✏️ Отправьте заново данные — начнём с заголовка.",
            parse_mode=ParseMode.HTML
        )
        await state.set_state(AdStates.waiting_for_title)

    async def process_position(self, message: Message, state: FSMContext):
        await state.update_data(position=message.text)
        await state.set_state(VacancyStates.waiting_for_company)
        await message.answer(
            "**Шаг 2/9:** Введите название компании\n"
            "Например: *TechCorp Beijing*",
            parse_mode=ParseMode.HTML
        )

    async def process_company(self, message: Message, state: FSMContext):
        await state.update_data(company=message.text)
        await state.set_state(VacancyStates.waiting_for_location)
        await message.answer(
            "**Шаг 3/9:** Введите локацию\n"
            "Например: *Шанхай, Пудун* или *Пекин (удаленно)*",
            parse_mode=ParseMode.HTML
        )

    async def process_location(self, message: Message, state: FSMContext):
        await state.update_data(location=message.text)
        await state.set_state(VacancyStates.waiting_for_salary)
        await message.answer(
            "**Шаг 4/9:** Введите зарплату\n"
            "Например: *25,000-35,000 RMB* или *Обсуждается*",
            parse_mode=ParseMode.HTML
        )

    async def process_salary(self, message: Message, state: FSMContext):
        await state.update_data(salary=message.text)
        await state.set_state(VacancyStates.waiting_for_experience)
        await message.answer(
            "**Шаг 5/9:** Введите требуемый опыт\n"
            "Например: *3+ года* или *Middle/Senior*",
            parse_mode=ParseMode.HTML
        )

    async def process_experience(self, message: Message, state: FSMContext):
        await state.update_data(experience=message.text)
        await state.set_state(VacancyStates.waiting_for_description)
        await message.answer(
            "**Шаг 6/9:** Введите описание вакансии\n"
            "Опишите основные задачи и проект",
            parse_mode=ParseMode.HTML
        )

    async def process_description(self, message: Message, state: FSMContext):
        await state.update_data(description=message.text)
        await state.set_state(VacancyStates.waiting_for_requirements)
        await message.answer(
            "**Шаг 7/9:** Введите требования\n"
            "Например: *Python, Django, PostgreSQL, опыт с микросервисами*",
            parse_mode=ParseMode.HTML
        )

    async def process_requirements(self, message: Message, state: FSMContext):
        await state.update_data(requirements=message.text)
        await state.set_state(VacancyStates.waiting_for_benefits)
        await message.answer(
            "**Шаг 8/9:** Введите условия и бенефиты\n"
            "Например: *Релокация, медстраховка, обучение китайскому*",
            parse_mode=ParseMode.HTML
        )

    async def process_benefits(self, message: Message, state: FSMContext):
        await state.update_data(benefits=message.text)
        await state.set_state(VacancyStates.waiting_for_contact)
        await message.answer(
            "**Шаг 9/9:** Введите контактную информацию\n"
            "Например: *@hr_username* или *hr@company.com*",
            parse_mode=ParseMode.HTML
        )

    async def process_contact(self, message: Message, state: FSMContext):
        await state.update_data(contact=message.text)
        
        # Show preview and ask for AI polishing
        data = await state.get_data()
        
        preview = f"""📋 **Предварительный просмотр вакансии:**

🎯 **Позиция:** {data['position']}
🏢 **Компания:** {data['company']}
📍 **Локация:** {data['location']}
💰 **Зарплата:** {data['salary']}
⭐ **Опыт:** {data['experience']}

📝 **Описание:** {data['description']}
✅ **Требования:** {data['requirements']}
🎁 **Условия:** {data['benefits']}
📞 **Контакт:** {data['contact']}"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🤖 Улучшить с AI", callback_data="polish_yes"),
                InlineKeyboardButton(text="📝 Оставить как есть", callback_data="polish_no")
            ],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_vacancy")]
        ])
        
        await message.answer(preview, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await state.set_state(VacancyStates.confirming_vacancy)

    async def handle_polish_choice(self, callback: CallbackQuery, state: FSMContext):
        use_ai = callback.data == "polish_yes"
        data = await state.get_data()
        
        await callback.message.edit_text("🔄 Генерирую финальную версию вакансии...")
        
        try:
            # Generate final vacancy post
            vacancy_post = await self.generator.generate_vacancy_post(data, use_ai_polish=use_ai)
            
            # Show final version with confirmation
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Опубликовать", callback_data="confirm_vacancy"),
                    InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_vacancy")
                ],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_vacancy")]
            ])
            
            await callback.message.edit_text(
                f"📋 **Финальная версия вакансии:**\n\n{vacancy_post}",
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            
            # Store final post in state
            await state.update_data(final_post=vacancy_post)
            
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка генерации: {str(e)}")
            await state.clear()

    async def confirm_vacancy(self, callback: CallbackQuery, state: FSMContext):
        """Confirm and publish vacancy."""
        data = await state.get_data()
        final_post = data.get('final_post')
        
        if not final_post:
            await callback.message.edit_text("❌ Ошибка: финальный пост не найден")
            await state.clear()
            return
        
        await callback.message.edit_text("🔄 Публикую вакансию...")
        
        try:
            success = await self.publisher.publish_vacancy(final_post)
            
            if success:
                await callback.message.edit_text("✅ Вакансия успешно опубликована в канале!")
            else:
                await callback.message.edit_text("❌ Ошибка публикации. Проверьте настройки канала.")
                
        except Exception as e:
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
        
        await state.clear()

    async def edit_vacancy(self, callback: CallbackQuery, state: FSMContext):
        """Allow editing vacancy (restart process)."""
        await callback.message.edit_text(
            "✏️ Для редактирования используйте команду /post_vacancy заново.\n\n"
            "Вакансия не была опубликована."
        )
        await state.clear()

    async def cancel_vacancy(self, callback: CallbackQuery, state: FSMContext):
        """Cancel vacancy posting."""
        await callback.message.edit_text("❌ Добавление вакансии отменено.")
        await state.clear()

    async def start_bot(self):
        """Start the bot."""
        try:
            # Validate configuration
            config.validate_config()
            
            # Test connections
            logger.info("🔍 Testing connections...")
            publisher_ok = await self.publisher.test_connection()
            
            if not publisher_ok:
                logger.error("❌ Publisher connection failed. Check BOT_TOKEN and CHANNEL_ID.")
                return
            
            # Start scheduler
            self.scheduler.start()
            logger.info("⏰ Scheduler started")
            
            # Set bot command list for Telegram menu
            await self.bot.set_my_commands([
                BotCommand(command="start", description="Запустить бота"),
                BotCommand(command="help", description="Показать справку"),
                BotCommand(command="post_vacancy", description="Добавить вакансию по шагам"),
                BotCommand(command="post_vacancy_free", description="Вакансия в свободной форме"),
                BotCommand(command="post_ad", description="Добавить рекламный пост"),
                BotCommand(command="post_now", description="Опубликовать новости сейчас"),
                BotCommand(command="status", description="Проверить статус бота"),
            ])
            
            # Start polling
            logger.info("🚀 Starting bot...")
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources."""
        logger.info("🧹 Cleaning up...")
        
        if self.scheduler.running:
            self.scheduler.shutdown()
        
        await self.bot.session.close()
        await self.publisher.close()

async def main():
    """Main function."""
    bot = ChinaITBot()
    await bot.start_bot()

if __name__ == "__main__":
    asyncio.run(main())