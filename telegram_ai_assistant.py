"""
HeadHunter Destroyer - AI-powered Telegram Assistant
Intelligent bot that understands natural language commands.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

from database import Database
from filters import VacancyFilter
from ai_assistant import get_ai_assistant
from response_tracker import ResponseTracker


class TelegramAIAssistant:
    """
    AI-powered Telegram assistant for HeadHunter Destroyer.

    Features:
    - Natural language command processing
    - Smart vacancy search
    - Resume viewing and analysis
    - Intelligent recommendations
    - Interactive dialogue
    """

    def __init__(
        self,
        token: str = None,
        owner_id: int = None,
        browser_manager=None,
        booster=None,
        applier=None,
        tracker=None,
        db: Database = None,
        filters_manager: VacancyFilter = None
    ):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.owner_id = owner_id or int(os.environ.get("TELEGRAM_OWNER_ID", "0"))

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        if not self.owner_id:
            raise ValueError("TELEGRAM_OWNER_ID not set")

        # Core components
        self.browser_manager = browser_manager
        self.booster = booster
        self.applier = applier
        self.tracker = tracker
        self.db = db
        self.filters_manager = filters_manager

        # AI assistant
        self.ai = get_ai_assistant(db) if db else None

        # State
        self.app: Optional[Application] = None
        self.is_running = False
        self.current_task: Optional[str] = None

        # Conversation context (для multi-turn диалога)
        self.user_context: Dict[int, Dict] = {}

    def is_owner(self, user_id: int) -> bool:
        """Check if user is the owner."""
        return user_id == self.owner_id

    async def _check_owner(self, update: Update) -> bool:
        """Check if message is from owner."""
        if not self.is_owner(update.effective_user.id):
            return False
        return True

    def _get_user_context(self, user_id: int) -> Dict:
        """Get or create user context."""
        if user_id not in self.user_context:
            self.user_context[user_id] = {
                "last_search": None,
                "last_vacancies": [],
                "conversation_history": []
            }
        return self.user_context[user_id]

    def _add_to_history(self, user_id: int, role: str, message: str):
        """Add message to conversation history."""
        context = self._get_user_context(user_id)
        context["conversation_history"].append({
            "role": role,
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        # Keep last 10 messages
        if len(context["conversation_history"]) > 10:
            context["conversation_history"] = context["conversation_history"][-10:]

    # ============ Command Handlers ============

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not await self._check_owner(update):
            return

        keyboard = [
            [
                InlineKeyboardButton("🔍 Найти вакансии", callback_data="search"),
                InlineKeyboardButton("📄 Мои резюме", callback_data="resumes"),
            ],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="stats"),
                InlineKeyboardButton("💡 Рекомендации", callback_data="recommend"),
            ],
            [
                InlineKeyboardButton("📬 Проверить отклики", callback_data="check_responses"),
                InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
            ],
            [
                InlineKeyboardButton("🚀 Массовая рассылка", callback_data="apply"),
                InlineKeyboardButton("🛑 Стоп", callback_data="stop"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🤖 *HeadHunter AI Assistant*\n\n"
            f"Привет! Я твой умный помощник по поиску работы.\n\n"
            "*Что я умею:*\n"
            "• 💬 Понимаю естественные команды\n"
            "• 🔍 Ищу подходящие вакансии\n"
            "• 📄 Показываю твои резюме\n"
            "• 💡 Даю персональные рекомендации\n"
            "• 📊 Анализирую статистику откликов\n"
            "• 🚀 Автоматически откликаюсь на вакансии\n\n"
            "*Попробуй написать:*\n"
            "• \"Найди вакансии python разработчика\"\n"
            "• \"Покажи мои резюме\"\n"
            "• \"Какая статистика откликов?\"\n"
            "• \"Дай совет по поиску работы\"\n\n"
            "Или используй кнопки ниже 👇",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not await self._check_owner(update):
            return

        await update.message.reply_text(
            "*HeadHunter AI Assistant - Помощь*\n\n"
            "*Команды:*\n"
            "/start - Главное меню\n"
            "/search `<запрос>` - Поиск вакансий\n"
            "/resumes - Показать мои резюме\n"
            "/stats - Статистика откликов\n"
            "/recommend - Получить рекомендации\n"
            "/check - Проверить статусы откликов\n"
            "/apply - Массовая рассылка\n"
            "/boost - Обновить резюме\n"
            "/blacklist `<компания>` - В черный список\n"
            "/whitelist `<компания>` - В белый список\n"
            "/filters - Показать фильтры\n\n"
            "*Естественные запросы:*\n"
            "Просто напиши что хочешь, я пойму!\n"
            "Например:\n"
            "• \"Найди работу python с зарплатой 200к\"\n"
            "• \"Покажи текст моего резюме\"\n"
            "• \"Сколько откликов просмотрели?\"\n"
            "• \"Отправь отклики на вакансии middle разработчика\"",
            parse_mode="Markdown"
        )

    async def cmd_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        if not await self._check_owner(update):
            return

        query = " ".join(context.args) if context.args else None

        if not query:
            await update.message.reply_text(
                "🔍 *Поиск вакансий*\n\n"
                "Использование: `/search <запрос>`\n\n"
                "Примеры:\n"
                "• /search python developer\n"
                "• /search senior backend\n"
                "• /search remote frontend",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text(f"🔍 Ищу вакансии: *{query}*...", parse_mode="Markdown")

        try:
            # Use applier to search
            if not self.applier:
                await update.message.reply_text("❌ Applier не настроен")
                return

            # Get vacancies
            vacancies = await asyncio.to_thread(
                self._search_vacancies,
                query
            )

            if not vacancies:
                await update.message.reply_text("😔 Вакансии не найдены")
                return

            # Save to context
            user_id = update.effective_user.id
            ctx = self._get_user_context(user_id)
            ctx["last_search"] = query
            ctx["last_vacancies"] = vacancies[:10]  # Top 10

            # Show results
            await self._show_vacancies(update, vacancies[:5], query)

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка поиска: {e}")

    async def cmd_resumes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resumes command - show user's resumes."""
        if not await self._check_owner(update):
            return

        await update.message.reply_text("📄 Загружаю резюме...")

        try:
            if not self.booster:
                await update.message.reply_text("❌ Booster не настроен")
                return

            # Get resumes
            resumes = await asyncio.to_thread(self.booster.get_resumes)

            if not resumes:
                await update.message.reply_text("😔 Резюме не найдены")
                return

            # Show resumes
            message = "📄 *Ваши резюме:*\n\n"
            for i, resume in enumerate(resumes, 1):
                title = resume.get('title', 'Unknown')
                link = resume.get('link', '')
                message += f"{i}. {title}\n"
                if link:
                    message += f"   🔗 {link}\n"
                message += "\n"

            # Add buttons for actions
            keyboard = []
            for i, resume in enumerate(resumes[:5], 1):  # Max 5 buttons
                keyboard.append([
                    InlineKeyboardButton(
                        f"📖 Показать текст #{i}",
                        callback_data=f"resume_text_{i-1}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton("♻️ Обновить все", callback_data="boost")
            ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            # Save to context
            user_id = update.effective_user.id
            ctx = self._get_user_context(user_id)
            ctx["last_resumes"] = resumes

            await update.message.reply_text(
                message,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        if not await self._check_owner(update):
            return

        await update.message.reply_text("📊 Загружаю статистику...")

        try:
            if not self.db:
                await update.message.reply_text("❌ База данных не настроена")
                return

            stats = self.db.get_stats()

            total = stats.get('total_applications', 0)
            today = stats.get('today_applications', 0)
            week = stats.get('week_applications', 0)

            by_status = stats.get('by_status', {})
            applied = by_status.get('applied', 0)
            viewed = by_status.get('viewed', 0)
            invited = by_status.get('invited', 0)
            rejected = by_status.get('rejected', 0)

            # Calculate conversion
            view_rate = round(viewed / total * 100, 1) if total > 0 else 0
            invite_rate = round(invited / total * 100, 1) if total > 0 else 0
            reject_rate = round(rejected / total * 100, 1) if total > 0 else 0

            message = (
                "📊 *Статистика откликов*\n\n"
                f"*Всего откликов:* {total}\n"
                f"• Сегодня: {today}\n"
                f"• За неделю: {week}\n\n"
                f"*По статусам:*\n"
                f"📤 Отправлено: {applied}\n"
                f"📖 Просмотрено: {viewed} ({view_rate}%)\n"
                f"✉️ Приглашений: {invited} ({invite_rate}%)\n"
                f"❌ Отказов: {rejected} ({reject_rate}%)\n\n"
            )

            # Add recommendations based on stats
            if invite_rate < 5 and total > 20:
                message += "💡 *Совет:* Конверсия низкая. Попробуй:\n"
                message += "• Обновить резюме\n"
                message += "• Изменить поисковые запросы\n"
                message += "• Добавить больше компаний в whitelist\n"
            elif invite_rate > 15:
                message += "🎉 Отличная конверсия! Продолжай в том же духе!\n"

            keyboard = [
                [
                    InlineKeyboardButton("📬 Проверить отклики", callback_data="check_responses"),
                    InlineKeyboardButton("💾 Экспорт CSV", callback_data="export")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                message,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")

    async def cmd_recommend(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recommend command - AI recommendations."""
        if not await self._check_owner(update):
            return

        await update.message.reply_text("💡 Генерирую рекомендации...")

        try:
            # Get stats for AI analysis
            stats = self.db.get_stats() if self.db else {}

            # Prepare data for AI
            recommendations = await asyncio.to_thread(
                self._generate_recommendations,
                stats
            )

            await update.message.reply_text(
                recommendations,
                parse_mode="Markdown"
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")

    async def cmd_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check command - check response statuses."""
        if not await self._check_owner(update):
            return

        await update.message.reply_text("📬 Проверяю статусы откликов...")

        try:
            if not self.tracker:
                await update.message.reply_text("❌ Tracker не настроен")
                return

            result = await asyncio.to_thread(self.tracker.check_all_responses)

            total = result.get('total', 0)
            updated = result.get('updated', 0)
            viewed = result.get('viewed', 0)
            invited = result.get('invited', 0)
            rejected = result.get('rejected', 0)

            message = (
                "📬 *Проверка откликов завершена*\n\n"
                f"Проверено: {total}\n"
                f"Обновлено: {updated}\n\n"
                f"*Новые статусы:*\n"
                f"📖 Просмотрено: {viewed}\n"
                f"✉️ Приглашений: {invited}\n"
                f"❌ Отказов: {rejected}\n"
            )

            # Show recent updates
            recent = self.tracker.get_recent_updates(days=1)
            if recent:
                message += "\n*Последние обновления:*\n"
                for resp in recent[:3]:
                    status_icon = {
                        'viewed': '📖',
                        'invited': '✉️',
                        'rejected': '❌'
                    }.get(resp['status'], '•')

                    message += f"{status_icon} {resp['title'][:40]}\n"

            await update.message.reply_text(message, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")

    async def cmd_boost(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /boost command."""
        if not await self._check_owner(update):
            return

        await update.message.reply_text("📄 Обновляю резюме...")

        try:
            if not self.booster:
                await update.message.reply_text("❌ Booster не настроен")
                return

            result = await asyncio.to_thread(self.booster.boost_all_resumes)

            success = len(result.get('success', []))
            failed = len(result.get('failed', []))

            await update.message.reply_text(
                f"✅ *Обновление завершено!*\n\n"
                f"✓ Успешно: {success}\n"
                f"✗ Ошибок: {failed}",
                parse_mode="Markdown"
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")

    async def cmd_apply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /apply command."""
        if not await self._check_owner(update):
            return

        query = " ".join(context.args) if context.args else None

        if self.current_task:
            await update.message.reply_text(
                f"⚠️ Уже выполняется: {self.current_task}\n"
                "Используй /stop для остановки"
            )
            return

        msg = "🚀 Запускаю массовую рассылку"
        if query:
            msg += f" по запросу: *{query}*"
        msg += "..."

        await update.message.reply_text(msg, parse_mode="Markdown")
        self.current_task = "apply"

        try:
            if not self.applier:
                await update.message.reply_text("❌ Applier не настроен")
                return

            params = {}
            if query:
                params["text"] = query

            # Run in background
            result = await asyncio.to_thread(
                self._run_mass_apply,
                params
            )

            applied = result.get('applied', 0)
            skipped = result.get('skipped', 0)
            filtered = result.get('filtered', 0)

            await update.message.reply_text(
                f"✅ *Рассылка завершена!*\n\n"
                f"📝 Отправлено: {applied}\n"
                f"⏭️ Пропущено: {skipped}\n"
                f"🚫 Отфильтровано: {filtered}",
                parse_mode="Markdown"
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
        finally:
            self.current_task = None

    async def cmd_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /blacklist command."""
        if not await self._check_owner(update):
            return

        if not context.args:
            # Show current blacklist
            if self.filters_manager:
                companies = self.filters_manager.get_blacklist_companies()
                if companies:
                    message = "🚫 *Черный список компаний:*\n\n"
                    for company in companies[:20]:
                        message += f"• {company}\n"
                    await update.message.reply_text(message, parse_mode="Markdown")
                else:
                    await update.message.reply_text("Черный список пуст")
            return

        company = " ".join(context.args)

        if self.filters_manager:
            self.filters_manager.add_to_blacklist(company)
            await update.message.reply_text(
                f"✅ Добавлено в черный список: *{company}*",
                parse_mode="Markdown"
            )

    async def cmd_whitelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /whitelist command."""
        if not await self._check_owner(update):
            return

        if not context.args:
            # Show current whitelist
            if self.filters_manager:
                companies = self.filters_manager.get_whitelist_companies()
                if companies:
                    message = "⭐ *Белый список компаний:*\n\n"
                    for company in companies[:20]:
                        message += f"• {company}\n"
                    await update.message.reply_text(message, parse_mode="Markdown")
                else:
                    await update.message.reply_text("Белый список пуст")
            return

        company = " ".join(context.args)

        if self.filters_manager:
            self.filters_manager.add_to_whitelist(company)
            await update.message.reply_text(
                f"✅ Добавлено в белый список: *{company}*",
                parse_mode="Markdown"
            )

    async def cmd_filters(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /filters command."""
        if not await self._check_owner(update):
            return

        if not self.filters_manager:
            await update.message.reply_text("❌ Filters не настроены")
            return

        stats = self.filters_manager.get_filter_stats()

        blacklist = stats.get('blacklist_companies', [])
        whitelist = stats.get('whitelist_companies', [])
        blacklist_words = stats.get('blacklist_words', [])

        message = "⚙️ *Текущие фильтры:*\n\n"
        message += f"🚫 Черный список: {len(blacklist)} компаний\n"
        message += f"⭐ Белый список: {len(whitelist)} компаний\n"
        message += f"📝 Запрещенные слова: {len(blacklist_words)}\n"

        keyboard = [
            [
                InlineKeyboardButton("🚫 Черный список", callback_data="show_blacklist"),
                InlineKeyboardButton("⭐ Белый список", callback_data="show_whitelist"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    # ============ Natural Language Processing ============

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language messages with AI."""
        if not await self._check_owner(update):
            return

        text = update.message.text
        user_id = update.effective_user.id

        # Add to history
        self._add_to_history(user_id, "user", text)

        # Show typing indicator
        await update.message.reply_chat_action("typing")

        try:
            # Analyze intent with AI
            response = await asyncio.to_thread(
                self._process_natural_command,
                text,
                user_id
            )

            await update.message.reply_text(response, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(
                f"❌ Извини, произошла ошибка: {e}\n\n"
                "Попробуй переформулировать запрос или используй команды."
            )

    # ============ Callback Handlers ============

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        await query.answer()

        if not self.is_owner(query.from_user.id):
            return

        data = query.data

        if data == "search":
            await query.message.reply_text(
                "🔍 Используй команду:\n"
                "`/search <запрос>`\n\n"
                "Или просто напиши что ищешь!",
                parse_mode="Markdown"
            )
        elif data == "resumes":
            await self.cmd_resumes(update, context)
        elif data == "stats":
            await self.cmd_stats(update, context)
        elif data == "recommend":
            await self.cmd_recommend(update, context)
        elif data == "check_responses":
            await self.cmd_check(update, context)
        elif data == "settings":
            await self.cmd_filters(update, context)
        elif data == "apply":
            await query.message.reply_text(
                "🚀 Массовая рассылка\n\n"
                "Используй: `/apply [запрос]`\n"
                "Или: просто напиши \"отправь отклики\"",
                parse_mode="Markdown"
            )
        elif data == "boost":
            await self.cmd_boost(update, context)
        elif data == "stop":
            self.current_task = None
            await query.message.reply_text("🛑 Остановлено")
        elif data.startswith("resume_text_"):
            # Show resume text
            idx = int(data.split("_")[-1])
            await self._show_resume_text(query, idx)
        elif data == "show_blacklist":
            await self.cmd_blacklist(update, context)
        elif data == "show_whitelist":
            await self.cmd_whitelist(update, context)
        elif data == "export":
            await self._export_csv(query)

    # ============ Helper Methods ============

    def _search_vacancies(self, query: str) -> List[Dict]:
        """Search vacancies using applier."""
        if not self.applier:
            return []

        # Build search URL
        url = self.applier.build_search_url({"text": query})
        self.applier.page.goto(url, wait_until="domcontentloaded")

        # Get vacancies from first page
        vacancies = self.applier.get_vacancies_on_page()
        return vacancies

    async def _show_vacancies(self, update: Update, vacancies: List[Dict], query: str):
        """Show vacancy results."""
        message = f"🔍 *Результаты поиска: {query}*\n\n"
        message += f"Найдено: {len(vacancies)} вакансий\n\n"

        for i, vac in enumerate(vacancies[:5], 1):
            title = vac.get('title', 'Unknown')
            employer = vac.get('employer', 'Unknown')
            salary_from = vac.get('salary_from')
            salary_to = vac.get('salary_to')
            url = vac.get('url', '')

            message += f"{i}. *{title}*\n"
            message += f"   🏢 {employer}\n"

            if salary_from or salary_to:
                salary = self._format_salary(salary_from, salary_to)
                message += f"   💰 {salary}\n"

            if url:
                message += f"   🔗 https://hh.ru{url}\n"

            message += "\n"

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚀 Отправить отклики на все",
                    callback_data=f"apply_search_{query}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    def _format_salary(self, salary_from, salary_to):
        """Format salary display."""
        if salary_from and salary_to:
            return f"{salary_from:,} - {salary_to:,} ₽".replace(',', ' ')
        elif salary_from:
            return f"от {salary_from:,} ₽".replace(',', ' ')
        elif salary_to:
            return f"до {salary_to:,} ₽".replace(',', ' ')
        return "не указана"

    async def _show_resume_text(self, query, resume_idx: int):
        """Show full resume text."""
        user_id = query.from_user.id
        ctx = self._get_user_context(user_id)

        resumes = ctx.get("last_resumes", [])
        if resume_idx >= len(resumes):
            await query.message.reply_text("❌ Резюме не найдено")
            return

        resume = resumes[resume_idx]

        # In real implementation, would fetch full resume content
        # For now, just show basic info
        message = (
            f"📄 *{resume.get('title', 'Unknown')}*\n\n"
            f"🔗 {resume.get('link', '')}\n\n"
            "_(Полный текст резюме доступен на HH.ru)_"
        )

        await query.message.reply_text(message, parse_mode="Markdown")

    def _generate_recommendations(self, stats: Dict) -> str:
        """Generate AI recommendations based on stats."""
        total = stats.get('total_applications', 0)

        if total < 10:
            return (
                "💡 *Рекомендации*\n\n"
                "У тебя пока мало откликов. Рекомендую:\n\n"
                "1. 🚀 Отправить минимум 50-100 откликов\n"
                "2. 📄 Обновить резюме каждые 4 часа\n"
                "3. 🔍 Попробовать разные поисковые запросы\n"
                "4. ⭐ Добавить интересные компании в whitelist"
            )

        by_status = stats.get('by_status', {})
        viewed = by_status.get('viewed', 0)
        invited = by_status.get('invited', 0)

        view_rate = round(viewed / total * 100, 1) if total > 0 else 0
        invite_rate = round(invited / total * 100, 1) if total > 0 else 0

        message = "💡 *Персональные рекомендации*\n\n"

        if view_rate < 30:
            message += (
                "⚠️ Низкий процент просмотров ({:.1f}%)\n\n"
                "Рекомендации:\n"
                "• Пересмотри заголовок резюме\n"
                "• Добавь ключевые навыки в начало\n"
                "• Укажи желаемую зарплату\n\n"
            ).format(view_rate)
        elif view_rate > 50:
            message += f"✅ Отличный процент просмотров ({view_rate:.1f}%)!\n\n"

        if invite_rate < 5 and total > 30:
            message += (
                "⚠️ Мало приглашений ({:.1f}%)\n\n"
                "Попробуй:\n"
                "• Персонализировать сопроводительные письма\n"
                "• Использовать AI для генерации писем\n"
                "• Откликаться на более релевантные вакансии\n"
            ).format(invite_rate)
        elif invite_rate > 15:
            message += f"🎉 Высокая конверсия в приглашения ({invite_rate:.1f}%)!\n"

        return message

    def _run_mass_apply(self, params: Dict) -> Dict:
        """Run mass apply in sync context."""
        if not self.applier:
            return {"applied": 0, "skipped": 0, "filtered": 0}

        # Get search params
        search_url = self.applier.build_search_url(params)

        applied = []
        skipped = []
        filtered = []

        # Scan pages and apply
        page_num = 0
        max_applications = params.get("_max_applications", 50)

        while len(applied) < max_applications and page_num < 10:
            # Navigate to page
            url = f"{search_url}&page={page_num}"
            self.applier.page.goto(url, wait_until="domcontentloaded")

            # Get vacancies
            vacancies = self.applier.get_vacancies_on_page()

            if not vacancies:
                break

            for vacancy in vacancies:
                if len(applied) >= max_applications:
                    break

                # Check if should apply
                should_apply, reason = self.applier.filters.should_apply(vacancy) if self.applier.filters else (True, "")

                if not should_apply:
                    filtered.append(vacancy)
                    continue

                # Check if already applied
                if self.applier.db and self.applier.db.is_already_applied(vacancy.get('vacancy_id')):
                    skipped.append(vacancy)
                    continue

                # Apply
                status, _ = self.applier.apply_to_vacancy(vacancy)

                if status == "applied":
                    applied.append(vacancy)
                elif status == "skipped":
                    skipped.append(vacancy)
                else:
                    filtered.append(vacancy)

            page_num += 1

        return {
            "applied": len(applied),
            "skipped": len(skipped),
            "filtered": len(filtered)
        }

    def _process_natural_command(self, text: str, user_id: int) -> str:
        """Process natural language command with AI."""
        text_lower = text.lower()

        # Intent detection (simple keywords for now)
        # In production, use LLM for better understanding

        # Search intent
        if any(word in text_lower for word in ['найди', 'поиск', 'ищу', 'вакансии', 'работа']):
            # Extract query
            query = text
            for word in ['найди', 'ищу', 'найти', 'поиск', 'вакансии', 'работа', 'работу']:
                query = query.lower().replace(word, '').strip()

            return (
                f"🔍 Хорошо, ищу вакансии: *{query}*\n\n"
                f"Используй: `/search {query}`"
            )

        # Resume intent
        elif any(word in text_lower for word in ['резюме', 'cv', 'резюм']):
            if 'покажи' in text_lower or 'посмотреть' in text_lower:
                return "📄 Показываю резюме...\n\nИспользуй: `/resumes`"
            elif 'обнов' in text_lower:
                return "📄 Обновляю резюме...\n\nИспользуй: `/boost`"

        # Stats intent
        elif any(word in text_lower for word in ['статистика', 'стат', 'сколько откликов', 'конверсия']):
            return "📊 Загружаю статистику...\n\nИспользуй: `/stats`"

        # Apply intent
        elif any(word in text_lower for word in ['отправ', 'рассылк', 'отклик', 'откликну']):
            return "🚀 Запускаю массовую рассылку...\n\nИспользуй: `/apply`"

        # Check responses intent
        elif any(word in text_lower for word in ['проверь отклик', 'статус отклик', 'ответ']):
            return "📬 Проверяю отклики...\n\nИспользуй: `/check`"

        # Recommendation intent
        elif any(word in text_lower for word in ['совет', 'рекоменд', 'посовету', 'что делать']):
            return "💡 Генерирую рекомендации...\n\nИспользуй: `/recommend`"

        # Fallback - use AI if available
        if self.ai and self.ai.is_enabled():
            try:
                # Use AI to generate response
                ctx = self._get_user_context(user_id)
                history = ctx.get("conversation_history", [])

                prompt = self._build_ai_prompt(text, history)
                response = self._call_ai(prompt)

                self._add_to_history(user_id, "assistant", response)
                return response
            except:
                pass

        # Default fallback
        return (
            "🤔 Не совсем понял запрос.\n\n"
            "Попробуй:\n"
            "• \"Найди вакансии python developer\"\n"
            "• \"Покажи мои резюме\"\n"
            "• \"Какая статистика?\"\n"
            "• \"Дай совет\"\n\n"
            "Или используй `/help` для списка команд"
        )

    def _build_ai_prompt(self, user_message: str, history: List[Dict]) -> str:
        """Build prompt for AI."""
        prompt = (
            "Ты AI-помощник HeadHunter Destroyer для поиска работы.\n"
            "Отвечай кратко, по делу, на русском.\n\n"
            "Доступные команды:\n"
            "- /search <запрос> - поиск вакансий\n"
            "- /resumes - показать резюме\n"
            "- /stats - статистика\n"
            "- /apply - массовая рассылка\n"
            "- /boost - обновить резюме\n"
            "- /recommend - рекомендации\n\n"
        )

        # Add recent history
        if history:
            prompt += "История:\n"
            for msg in history[-3:]:
                role = msg['role']
                content = msg['content']
                prompt += f"{role}: {content}\n"
            prompt += "\n"

        prompt += f"Пользователь: {user_message}\n"
        prompt += "Ответ:"

        return prompt

    def _call_ai(self, prompt: str) -> str:
        """Call AI model."""
        if not self.ai or not self.ai.is_enabled():
            raise Exception("AI not available")

        # Use AI assistant
        if self.ai.provider == "openai":
            return self._call_openai(prompt)
        elif self.ai.provider == "ollama":
            return self._call_ollama(prompt)

        raise Exception("Unknown AI provider")

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        import openai

        client = openai.OpenAI(api_key=self.ai.api_key)

        response = client.chat.completions.create(
            model=self.ai.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )

        return response.choices[0].message.content

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API."""
        import requests

        response = requests.post(
            f"{self.ai.ollama_host}/api/generate",
            json={
                "model": self.ai.model,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )

        if response.status_code == 200:
            return response.json()['response']

        raise Exception(f"Ollama error: {response.status_code}")

    async def _export_csv(self, query):
        """Export data to CSV."""
        if not self.db:
            await query.message.reply_text("❌ База данных не настроена")
            return

        try:
            filename = f"hh_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = self.db.export_to_csv(filename)

            await query.message.reply_text(
                f"✅ Данные экспортированы:\n`{filepath}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка экспорта: {e}")

    # ============ Bot Lifecycle ============

    def setup_handlers(self):
        """Setup all command and message handlers."""
        # Commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("search", self.cmd_search))
        self.app.add_handler(CommandHandler("resumes", self.cmd_resumes))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("recommend", self.cmd_recommend))
        self.app.add_handler(CommandHandler("check", self.cmd_check))
        self.app.add_handler(CommandHandler("boost", self.cmd_boost))
        self.app.add_handler(CommandHandler("apply", self.cmd_apply))
        self.app.add_handler(CommandHandler("blacklist", self.cmd_blacklist))
        self.app.add_handler(CommandHandler("whitelist", self.cmd_whitelist))
        self.app.add_handler(CommandHandler("filters", self.cmd_filters))

        # Callbacks
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        # Natural language messages
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_message
            )
        )

    async def start(self):
        """Start the bot."""
        self.app = Application.builder().token(self.token).build()
        self.setup_handlers()

        print(f"[Telegram] Starting AI Assistant bot...")
        print(f"[Telegram] Owner ID: {self.owner_id}")

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        self.is_running = True
        print("[Telegram] AI Assistant bot is running!")

    async def stop(self):
        """Stop the bot."""
        if self.app and self.is_running:
            print("[Telegram] Stopping bot...")
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            self.is_running = False
            print("[Telegram] Bot stopped")

    def run(self):
        """Run the bot (blocking)."""
        asyncio.run(self.start())

        # Keep running
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            asyncio.run(self.stop())


def run_ai_bot(
    browser_manager=None,
    booster=None,
    applier=None,
    tracker=None,
    db=None,
    filters_manager=None
):
    """
    Run AI Telegram bot standalone.

    Usage:
        bot = TelegramAIAssistant(...)
        bot.run()
    """
    bot = TelegramAIAssistant(
        browser_manager=browser_manager,
        booster=booster,
        applier=applier,
        tracker=tracker,
        db=db,
        filters_manager=filters_manager
    )

    bot.run()


if __name__ == "__main__":
    run_ai_bot()
