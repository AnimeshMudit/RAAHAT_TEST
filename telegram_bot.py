import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# IMPORT YOUR LOCAL FILES (Flat structure)
import core.memory as memory
import core.knowledge as knowledge
import core.brain as brain

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
load_dotenv()

print("🧠 RAAHAT: Loading Vector Vault...")
vector_db = knowledge.load_vector_store()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Helper to link Telegram users to your 'users' table UUIDs
async def get_internal_id(tg_id, first_name):
    # 1. Check if TG user exists in 'users' table
    user_record = memory.get_user_by_telegram(tg_id)
    
    if not user_record:
        print(f"🆕 New user detected on Telegram: {first_name}. Creating profile...")
        # 2. Create them using your existing memory logic
        user_record = memory.create_telegram_user(tg_id, first_name)
    
    return user_record["id"] # This is the UUID shared with the Web Dashboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await get_internal_id(user.id, user.first_name)
    await update.message.reply_text(f"Namaste, {user.first_name}! I'm RAAHAT. I've linked your session to your secure sanctuary. 🤍")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_text = update.message.text
    
    # Get the UUID (Internal ID) for this Telegram user
    internal_uuid = await get_internal_id(user.id, user.first_name)
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # A. Save User Message to 'messages' table (Syncs with Web Dashboard)
        memory.save_message(internal_uuid, "user", user_text)

        # B. RAG Search from PDFs
        retrieved_chunks = knowledge.search_knowledge(user_text, vector_db)
        context_text = "\n".join(retrieved_chunks)

        # C. Fetch History from 'messages' table for continuity
        chat_history = memory.fetch_history(internal_uuid)

        # D. Generate Response using your brain logic
        response = brain.get_response(user_text, chat_history, context_text)

        # E. Save AI response to 'messages' table (Syncs with Web Dashboard)
        memory.save_message(internal_uuid, "ai", response)

        await update.message.reply_text(response)

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("I'm feeling a bit tired right now. Can we try again in a second? 🤍")

if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🚀 RAAHAT is live on Telegram! Messaging here will appear on your Web Dashboard.")
    app.run_polling()