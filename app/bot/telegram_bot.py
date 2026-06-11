import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

from app.core import memory, brain, knowledge

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Initialize Vector DB
vector_db = None
if os.path.exists("faiss_index"):
    vector_db = knowledge.load_vector_store()
    print("Vector Vault Online! (Loaded from disk)")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_text = update.message.text
    tele_id = str(user.id)

    # Get User DB UUID or create shadow profile
    tg_user = memory.get_user_by_telegram(tele_id)
    if not tg_user:
        logging.info(f"Bot seen for the first time. Provisioning shadow profile for {tele_id}...")
        tg_user = memory.create_telegram_user(tele_id, user.first_name)
    
    user_uuid = tg_user["id"]

    # 1. Save user msg to shared DB
    memory.save_message(user_uuid, "user", user_text)

    # 3. Get Shared History
    history_records = memory.fetch_history(user_uuid)

    # 2. Search PDF Context (if any)
    context_text = ""
    if vector_db:
        try:
            is_crisis = brain.is_crisis_active(user_text, history_records)
            if is_crisis and not brain.needs_psychoeducation(user_text):
                rel_chunks = []
            else:
                search_query = brain.generate_search_keywords(user_text)
                if search_query == "SKIP":
                    rel_chunks = []
                else:
                    k_val = 1 if is_crisis else 4
                    rel_chunks = knowledge.search_knowledge(search_query, vector_db, k=k_val)
            if rel_chunks:
                context_text = "\n".join(rel_chunks)
        except Exception as e:
            logging.error(f"Vector search failed: {e}")

    # 4. Generate Brain Response
    response = brain.get_response(user_text, history_records, context_text)

    # 5. Save AI response to DB
    memory.save_message(user_uuid, "ai", response)

    await update.message.reply_text(response)

def run():
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("🚀 RAAHAT Bot is syncing with Web History...")
    app.run_polling()

if __name__ == '__main__':
    run()