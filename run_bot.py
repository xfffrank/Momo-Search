import logging
import os
from datetime import datetime, time
os.environ['TOKENIZERS_PARALLELISM'] = "false"

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from llm_search import LLMSearch
from config import TELEGRAM_TOKEN, CHAT_ID, DAILY_QUERY_TXT, SCHEDULED_TIME
from utils import escape_special_chars


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize the LLMSearch instance
search_engine = LLMSearch()


# Telegram bot command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! I'm your LLM Search Bot. "
        f"You can ask me anything, and I'll search the web and provide an answer. "
        f"Just type your question or use /search [your question]"
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /search command."""
    if not context.args:
        await update.message.reply_text("Please provide a search query after /search")
        return

    mode = "speed"  # Default mode
    args = context.args
    
    if args[0].lower() in ["-q", "--quality"]:
        mode = "quality"
        args = args[1:]  # Remove the mode flag
    elif args[0].lower() in ["-s", "--speed"]:
        mode = "speed"
        args = args[1:]  # Remove the mode flag
    
    query = ' '.join(args)
    if not query:
        await update.message.reply_text("Please provide a search query after the mode flag")
        return
    
    await perform_search(update, query, mode)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the user message as a search query."""
    query = update.message.text
    await perform_search(update, query)


async def perform_search(update: Update, query: str, mode: str = "speed") -> None:
    """Perform search and send the result."""
    cur_text = "🔍 Searching and processing your query. This may take a moment..."
    mode_emoji = "⚡" if mode == "speed" else "✨"
    await update.message.reply_text(f"{cur_text} Using {mode_emoji} {mode} mode.")
    
    try:
        query_rewrite = search_engine.rewrite_query(query)
        await update.message.reply_text(f'🔍 Searching for "{query_rewrite}"...')

        results_generator = search_engine.process_query(query, query_rewrite, mode=mode)

        doc_count = await anext(results_generator)
        await update.message.reply_text(f"Found {doc_count} relevant sources. Analyzing...")

        final_response = await anext(results_generator)
        await update.message.reply_text(final_response, parse_mode="MarkdownV2", disable_web_page_preview=True)
    
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        await update.message.reply_text(f"Sorry, an error occurred while processing your query: {str(e)}")


async def reply_msg(context: ContextTypes.DEFAULT_TYPE, response: str) -> None:
    try:
        await context.bot.send_message(chat_id=CHAT_ID, text=response, parse_mode="MarkdownV2", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Failed to send message to chat {CHAT_ID}: {e}")


async def daily_news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually trigger the daily news search."""
    await update.message.reply_text("📰 Fetching the latest update. This may take a moment...")
    await daily_news(context)


async def daily_news(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Running scheduled daily search")
    
    try:
        with open(DAILY_QUERY_TXT, "r") as file:
            query_list = file.readlines()

        for query in query_list:
            query = query.strip()
            query_rewrite = search_engine.rewrite_query(query)
            results_generator = search_engine.process_query(query, query_rewrite, mode="speed")

            doc_count = await anext(results_generator)
            logger.info(f"Found {doc_count} relevant sources for {query}")

            response = await anext(results_generator)

            current_date = datetime.now().strftime("%Y-%m-%d")
            title = f'📰 Daily Update ({current_date}) for "{query}"'
            title = escape_special_chars(title)

            message = f"{title}\n\n{response}"
            await reply_msg(context, message)
    
    except Exception as e:
        logger.error(f"Error in daily news job: {e}", exc_info=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message when the command /help is issued."""
    help_text = (
        "🤖 *Search Bot Commands* 🤖\n\n"
        "- /start - Start the bot\n"
        "- /search [query] - Search with default speed mode\n"
        "- /search -q [query] - Search with quality mode (more thorough but slower)\n"
        "- /search -s [query] - Search with speed mode (faster but less detailed)\n"
        "- /news - Fetch the daily news update\n"
        "- /help - Show this help message\n\n"
        "*Search Modes:*\n"
        "⚡ *Speed mode*: Faster results but may be less comprehensive\n"
        "✨ *Quality mode*: More detailed results with web page crawling for better analysis"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


def setup_daily_job(application: Application) -> None:
    job_queue = application.job_queue
    local_tz = datetime.now().astimezone().tzinfo
    h, m, s = SCHEDULED_TIME
    job_time = time(hour=h, minute=m, second=s, tzinfo=local_tz)
    job_queue.run_daily(daily_news, job_time)


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("news", daily_news_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    setup_daily_job(application)

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot with daily news scheduler...")
    application.run_polling()


if __name__ == "__main__":
    main()
