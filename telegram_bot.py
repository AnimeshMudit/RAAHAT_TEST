import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from supabase import create_client, Client

# Importing your RAG and Brain logic
from core.knowledge import load_vector_store, search_knowledge
# Ensure your SYSTEM_PROMPT is exported from brain.py or paste it here
from core.brain import SYSTEM_PROMPT 

# 1. Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
load_dotenv()

# 2. Initialize Clients
print("🧠 Loading Vector Vault...")
vector_db = load_vector_store()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# 3. Database Helper: User Registration
async def ensure_user_registered(user_id, first_name):
    # Check if user exists in your 'users' table
    res = supabase.table("users").select("*").eq("telegram_id", user_id).execute()
    if not res.data:
        print(f"🆕 Registering new user: {first_name}")
        supabase.table("users").insert({
            "telegram_id": user_id, 
            "name": first_name,
            "joined_at": "now()"
        }).execute()

# 4. Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await ensure_user_registered(user.id, user.first_name)
    await update.message.reply_text(f"Namaste, {user.first_name}! I'm RAAHAT. I'm right here with you. 🤍")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_text = update.message.text
    
    # Auto-register if they skipped /start
    await ensure_user_registered(user.id, user.first_name)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # A. RAG Search
        retrieved_chunks = search_knowledge(user_text, vector_db, k=5)
        context_text = "\n".join(retrieved_chunks)

        # B. Groq Completion with your specialized SYSTEM_PROMPT
        full_system_prompt = f"{SYSTEM_PROMPT}\n\nUSE THIS CONTEXT FROM MANUALS:\n{context_text}"
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": user_text},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.6, # Lower temp for more grounded "Safe House" vibes
        )

        response = chat_completion.choices[0].message.content

        # C. Store Chat in Database (History)
        supabase.table("chats").insert({
            "telegram_id": user.id,
            "user_message": user_text,
            "bot_response": response
        }).execute()

        await update.message.reply_text(response)

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("I'm feeling a bit tired right now. Can we try again in a second? 🤍")

if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🚀 RAAHAT is live on Telegram with Supabase & RAG!")
    app.run_polling()