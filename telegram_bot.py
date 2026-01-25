"""
HeadHunter Destroyer - Telegram Bot
Secure bot for remote control and notifications.
Each user deploys their own bot with their own token.
"""

import os
import asyncio
import threading
from datetime import datetime
from typing import Optional, Callable

# Check for telegram library
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, CallbackQueryHandler,
        ContextTypes, MessageHandler, filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("[!] python-telegram-bot not installed. Run: pip install python-telegram-bot")


class HHDestroyerBot:
    """
    Telegram bot for HeadHunter Destroyer.

    Security: Only responds to OWNER_ID, ignores everyone else.
    """

    def __init__(
        self,
        token: str = None,
        owner_id: int = None,
        on_boost: Callable = None,
        on_apply: Callable = None,
        on_stop: Callable = None,
        get_stats: Callable = None,
        filters_manager = None,
        db = None
    ):
        """
        Initialize Telegram bot.

        Args:
            token: Bot token from @BotFather
            owner_id: Telegram user ID of the owner (only this user can control the bot)
            on_boost: Callback for resume boost
            on_apply: Callback for mass apply (receives optional query string)
            on_stop: Callback to stop current operation
            get_stats: Callback to get current statistics
            filters_manager: VacancyFilter instance for blacklist/whitelist
            db: Database instance
        """
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.owner_id = owner_id or int(os.environ.get("TELEGRAM_OWNER_ID", "0"))

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        if not self.owner_id:
            raise ValueError("TELEGRAM_OWNER_ID not set")

        self.on_boost = on_boost
        self.on_apply = on_apply
        self.on_stop = on_stop
        self.get_stats = get_stats
        self.filters_manager = filters_manager
        self.db = db

        self.app: Optional[Application] = None
        self.is_running = False
        self.current_task: Optional[str] = None
        self._thread: Optional[threading.Thread] = None

    def is_owner(self, user_id: int) -> bool:
        """Check if user is the owner."""
        return user_id == self.owner_id

    async def _check_owner(self, update: Update) -> bool:
        """Check if message is from owner. If not, ignore silently."""
        if not self.is_owner(update.effective_user.id):
            # Silently ignore non-owners
            return False
        return True

    # ============ Command Handlers ============

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not await self._check_owner(update):
            return

        keyboard = [
            [
                InlineKeyboardButton("📄 Boost Resumes", callback_data="boost"),
                InlineKeyboardButton("🚀 Mass Apply", callback_data="apply"),
            ],
            [
                InlineKeyboardButton("📊 Statistics", callback_data="stats"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
            ],
            [
                InlineKeyboardButton("🛑 Stop", callback_data="stop"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🤖 *HeadHunter Destroyer Bot*\n\n"
            f"Owner ID: `{self.owner_id}` ✅\n\n"
            "Commands:\n"
            "/boost - Update all resumes\n"
            "/apply - Mass apply to vacancies\n"
            "/apply `<query>` - Apply with search query\n"
            "/stats - Show statistics\n"
            "/stop - Stop current operation\n"
            "/blacklist `<company>` - Add to blacklist\n"
            "/whitelist `<company>` - Add to whitelist\n"
            "/filters - Show current filters\n"
            "/help - Show this help",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not await self._check_owner(update):
            return
        await self.cmd_start(update, context)

    async def cmd_boost(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /boost command."""
        if not await self._check_owner(update):
            return

        if self.current_task:
            await update.message.reply_text(f"⚠️ Task already running: {self.current_task}")
            return

        await update.message.reply_text("📄 Starting resume boost...")
        self.current_task = "boost"

        try:
            if self.on_boost:
                # Run in thread to not block bot
                result = await asyncio.to_thread(self.on_boost)
                await update.message.reply_text(
                    f"✅ Resume boost complete!\n"
                    f"Updated: {result.get('success', 0)} resumes"
                )
            else:
                await update.message.reply_text("❌ Boost function not configured")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
        finally:
            self.current_task = None

    async def cmd_apply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /apply command."""
        if not await self._check_owner(update):
            return

        if self.current_task:
            await update.message.reply_text(f"⚠️ Task already running: {self.current_task}")
            return

        # Get optional search query from args
        query = " ".join(context.args) if context.args else None

        msg = "🚀 Starting mass apply"
        if query:
            msg += f" for: `{query}`"
        msg += "..."

        await update.message.reply_text(msg, parse_mode="Markdown")
        self.current_task = "apply"

        try:
            if self.on_apply:
                result = await asyncio.to_thread(self.on_apply, query)
                applied = len(result.get('applied', []))
                skipped = len(result.get('skipped', []))
                filtered = len(result.get('filtered', []))

                await update.message.reply_text(
                    f"✅ Mass apply complete!\n\n"
                    f"📝 Applied: {applied}\n"
                    f"⏭️ Skipped: {skipped}\n"
                    f"🚫 Filtered: {filtered}"
                )
            else:
                await update.message.reply_text("❌ Apply function not configured")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
        finally:
            self.current_task = None

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command."""
        if not await self._check_owner(update):
            return

        if not self.current_task:
            await update.message.reply_text("ℹ️ No task running")
            return

        await update.message.reply_text(f"🛑 Stopping {self.current_task}...")

        if self.on_stop:
            self.on_stop()

        self.current_task = None
        await update.message.reply_text("✅ Stopped")

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        if not await self._check_owner(update):
            return

        stats_text = "📊 *Statistics*\n\n"

        if self.get_stats:
            stats = self.get_stats()
            stats_text += f"*Session:*\n"
            stats_text += f"  Applied: {stats.get('applied', 0)}\n"
            stats_text += f"  Skipped: {stats.get('skipped', 0)}\n"
            stats_text += f"  Filtered: {stats.get('filtered', 0)}\n"

        if self.db:
            db_stats = self.db.get_stats()
            stats_text += f"\n*Database:*\n"
            stats_text += f"  Total applications: {db_stats.get('total_applications', 0)}\n"
            stats_text += f"  Today: {db_stats.get('today_applications', 0)}\n"
            stats_text += f"  This week: {db_stats.get('week_applications', 0)}\n"

        if self.current_task:
            stats_text += f"\n⏳ Current task: {self.current_task}"

        await update.message.reply_text(stats_text, parse_mode="Markdown")

    async def cmd_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /blacklist command."""
        if not await self._check_owner(update):
            return

        if not context.args:
            await update.message.reply_text("Usage: /blacklist <company name>")
            return

        company = " ".join(context.args)

        if self.filters_manager:
            self.filters_manager.add_blacklist_company(company)
            await update.message.reply_text(f"✅ Added `{company}` to blacklist", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Filters not configured")

    async def cmd_whitelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /whitelist command."""
        if not await self._check_owner(update):
            return

        if not context.args:
            await update.message.reply_text("Usage: /whitelist <company name>")
            return

        company = " ".join(context.args)

        if self.filters_manager:
            self.filters_manager.add_whitelist_company(company)
            await update.message.reply_text(f"✅ Added `{company}` to whitelist", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Filters not configured")

    async def cmd_filters(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /filters command."""
        if not await self._check_owner(update):
            return

        if not self.filters_manager:
            await update.message.reply_text("❌ Filters not configured")
            return

        stats = self.filters_manager.get_filter_stats()

        blacklist = ", ".join(stats['blacklist_companies'][:10]) or "none"
        whitelist = ", ".join(stats['whitelist_companies'][:10]) or "none"
        words = ", ".join(stats['blacklist_words'][:10]) or "none"

        text = (
            "⚙️ *Current Filters*\n\n"
            f"*Blacklisted companies:*\n{blacklist}\n\n"
            f"*Whitelisted companies:*\n{whitelist}\n\n"
            f"*Blacklisted words:*\n{words}"
        )

        if stats.get('min_salary'):
            text += f"\n\n*Min salary:* {stats['min_salary']:,}₽"
        if stats.get('max_salary'):
            text += f"\n*Max salary:* {stats['max_salary']:,}₽"

        await update.message.reply_text(text, parse_mode="Markdown")

    # ============ Callback Query Handler ============

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query

        if not self.is_owner(query.from_user.id):
            await query.answer("⛔ Access denied", show_alert=True)
            return

        await query.answer()

        if query.data == "boost":
            await query.message.reply_text("Starting boost...")
            # Trigger boost command
            context.args = []
            await self.cmd_boost(update, context)

        elif query.data == "apply":
            await query.message.reply_text("Starting mass apply...")
            context.args = []
            await self.cmd_apply(update, context)

        elif query.data == "stats":
            context.args = []
            # Create a fake update with message for cmd_stats
            await self.cmd_stats(update, context)

        elif query.data == "stop":
            context.args = []
            await self.cmd_stop(update, context)

        elif query.data == "settings":
            await query.message.reply_text(
                "⚙️ *Settings*\n\n"
                "Use commands:\n"
                "/blacklist <company> - Add to blacklist\n"
                "/whitelist <company> - Add to whitelist\n"
                "/filters - Show current filters",
                parse_mode="Markdown"
            )

    # ============ Notification Methods ============

    async def send_notification(self, message: str):
        """Send notification to owner."""
        if self.app and self.owner_id:
            try:
                await self.app.bot.send_message(
                    chat_id=self.owner_id,
                    text=message,
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"[!] Failed to send notification: {e}")

    def notify(self, message: str):
        """Sync wrapper for send_notification."""
        if self.app:
            asyncio.run_coroutine_threadsafe(
                self.send_notification(message),
                self.app._loop if hasattr(self.app, '_loop') else asyncio.get_event_loop()
            )

    def notify_application(self, title: str, employer: str, status: str):
        """Send notification about application."""
        if status == "applied":
            self.notify(f"✅ Applied: {title} @ {employer}")

    def notify_invitation(self, title: str, employer: str):
        """Send notification about interview invitation."""
        self.notify(f"🎉 *Interview Invitation!*\n\n{title}\n{employer}")

    def notify_resume_boost(self, count: int):
        """Send notification about resume boost."""
        self.notify(f"📄 Resumes updated: {count}")

    def notify_session_summary(self, stats: dict):
        """Send daily/session summary."""
        self.notify(
            f"📊 *Session Summary*\n\n"
            f"Applied: {stats.get('applied', 0)}\n"
            f"Skipped: {stats.get('skipped', 0)}\n"
            f"Filtered: {stats.get('filtered', 0)}"
        )

    # ============ Bot Lifecycle ============

    def setup(self):
        """Setup bot handlers."""
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot not installed")

        self.app = Application.builder().token(self.token).build()

        # Command handlers
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("boost", self.cmd_boost))
        self.app.add_handler(CommandHandler("apply", self.cmd_apply))
        self.app.add_handler(CommandHandler("stop", self.cmd_stop))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("blacklist", self.cmd_blacklist))
        self.app.add_handler(CommandHandler("whitelist", self.cmd_whitelist))
        self.app.add_handler(CommandHandler("filters", self.cmd_filters))

        # Callback handler for inline buttons
        self.app.add_handler(CallbackQueryHandler(self.button_callback))

        return self

    def run(self):
        """Run bot (blocking)."""
        if not self.app:
            self.setup()

        print(f"[*] Telegram bot started. Owner ID: {self.owner_id}")
        self.is_running = True
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

    def run_async(self):
        """Run bot in background thread."""
        if not self.app:
            self.setup()

        def _run():
            self.is_running = True
            self.app.run_polling(allowed_updates=Update.ALL_TYPES)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        print(f"[*] Telegram bot started in background. Owner ID: {self.owner_id}")

    def stop(self):
        """Stop bot."""
        self.is_running = False
        if self.app:
            self.app.stop()


# ============ Standalone Bot Runner ============

def run_standalone_bot():
    """Run bot as standalone process."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from database import Database
    from filters import VacancyFilter

    db = Database()
    filters = VacancyFilter(db)

    bot = HHDestroyerBot(
        filters_manager=filters,
        db=db
    )

    print("Starting Telegram bot in standalone mode...")
    print("Note: Boost and Apply functions require browser, use main.py --telegram instead")

    bot.run()


if __name__ == "__main__":
    run_standalone_bot()
