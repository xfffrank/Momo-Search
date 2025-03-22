import logging
import os
from datetime import datetime, time
os.environ['TOKENIZERS_PARALLELISM'] = "false"

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from llm_search import LLMSearch
from config import TELEGRAM_TOKEN, CHAT_ID, DAILY_QUERY_TXT, SCHEDULED_TIME

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
    
    query = ' '.join(context.args)
    await perform_search(update, query)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the user message as a search query."""
    query = update.message.text
    await perform_search(update, query)


async def perform_search(update: Update, query: str) -> None:
    """Perform search and send the result."""
    await update.message.reply_text("🔍 Searching and processing your query. This may take a moment...")
    
    try:
        # Process the query
        response = search_engine.process_query(query, mode="speed")
        
        # Split response if needed (Telegram has a 4096 character limit per message)
        if len(response) <= 4000:
            await update.message.reply_text(response)
        else:
            # Split the response into chunks
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for i, chunk in enumerate(chunks):
                await update.message.reply_text(f"Part {i+1}/{len(chunks)}:\n\n{chunk}")
    
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        await update.message.reply_text(f"Sorry, an error occurred while processing your query: {str(e)}")


async def reply_msg(context: ContextTypes.DEFAULT_TYPE, response: str) -> None:
    try:
        # Split response if needed (Telegram has a 4096 character limit per message)
        if len(response) <= 4000:
            await context.bot.send_message(chat_id=CHAT_ID, text=response)
        else:
            # Split the response into chunks
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for i, chunk in enumerate(chunks):
                await context.bot.send_message(chat_id=CHAT_ID, text=f"Part {i+1}/{len(chunks)}:\n\n{chunk}")
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
            # Process the query
            response = search_engine.process_query(query, mode="speed")
            
            # Get the current date for the message
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Prepare the message
            message = f"📰 Daily Update ({current_date}) 📰\n\n{response}"
            
            # Send the message
            await reply_msg(context, message)
    
    except Exception as e:
        logger.error(f"Error in daily news job: {e}", exc_info=True)


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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    setup_daily_job(application)

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot with daily news scheduler...")
    application.run_polling()


if __name__ == "__main__":
    main()
