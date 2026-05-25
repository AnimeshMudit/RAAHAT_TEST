import os
import colorama
from colorama import Fore, Style
import getpass

from app.core import memory
from app.core import brain
from app.core import knowledge
from app.core import security


def main():
    colorama.init(autoreset=True)
    print(Fore.CYAN + "========================================")
    print(Fore.CYAN + "   🧠 INITIALIZING RAAHAT SYSTEM...   ")
    print(Fore.CYAN + "========================================")

    data_folder = "data"
    faiss_path = "faiss_index"

    if os.path.exists(faiss_path):
        vector_db = knowledge.load_vector_store()
        print(Fore.GREEN + "Vector Vault Online! (Loaded from disk)")

    elif os.path.exists(data_folder):
        print(
            Fore.YELLOW
            + f"\nFirst boot detected! Reading knowledge from {data_folder} directory..."
        )
        vector_db = knowledge.build_vector_store_from_folder(data_folder)
        if vector_db:
            print(Fore.GREEN + "Vector Vault Online!")
        else:
            print(Fore.RED + "Warning: Could not build Vector Vault.")
    else:
        print(
            Fore.RED
            + f" Warning: '{data_folder}' folder not found. RAAHAT will run without context."
        )
        vector_db = None

    print(Fore.CYAN + "\n--- SYSTEM LOGIN ---")

    # Authentication
    while True:
        user_name = input(
            Fore.YELLOW + "Enter your username: " + Style.RESET_ALL
        ).strip()
        password = getpass.getpass(
            Fore.YELLOW + "Enter your password: " + Style.RESET_ALL
        )  # need to know the working

        user_record = memory.get_user_by_email(user_name)
        if user_record:
            if user_record.get("telegram_id"):
                user_id = None
            elif security.verify_password(password, user_record["password_hash"]):
                user_id = user_record["id"]
            else:
                user_id = None
        else:
            hashed_password = security.get_password_hash(password)
            user_id = memory.create_user(user_name, hashed_password)

        if user_id:
            print(
                Fore.GREEN
                + f"\nWelcome, {user_name}. RAAHAT is online and connected to Supabase. Type 'quit' to exit.\n"
            )
            break
        else:
            print(Fore.RED + "❌ Login failed. Wrong username or password.")

    # greeting message
    print(Fore.CYAN + "—" * 60)

    greeting = (
        f"Welcome back, {user_name}.\n\n"
        "The world asks a lot of you, but here, you don't have to be anyone but yourself.\n"
        "Your secrets are safe, your burdens are shared, and your pace is respected.\n"
        "Whenever you're ready to let it out, I'm here to listen."
    )

    print(Fore.LIGHTWHITE_EX + greeting)
    print(Fore.CYAN + "—" * 60 + "\n")

    # saving greeting message to supabase so ai know it spoke first
    memory.save_message(user_id, "ai", greeting)

    while True:
        # User Input
        user_input = input(Fore.YELLOW + "You: " + Style.RESET_ALL)

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit"]:
            print(Fore.CYAN + "RAAHAT shutting down. Take care.")
            break

        # Save user query
        memory.save_message(user_id, "user", user_input)

        context_text = ""
        if vector_db:
            try:
                # --- NEW: SEARCH QUERY EXPANSION ---
                # 1. Ask brain to generate clinical terms (e.g., "drowning" -> "Grounding")
                search_query = brain.generate_search_keywords(user_input)
                print(Fore.MAGENTA + f"🔍 Searching Knowledge Base for: {search_query}")

                # 2. search_knowledge cleans the query internally via clean_query()
                results = knowledge.search_knowledge(search_query, vector_db)
                context_text = "\n".join(results)
            except Exception as e:
                print(Fore.RED + f"Search Error: {e}")

        # Retrieve Past Memory
        chat_history = memory.fetch_history(user_id)

        # Generate Brain Response
        response = brain.get_response(user_input, chat_history, context_text)

        # Speak to the User
        print(Fore.GREEN + f"RAAHAT: {response}\n")

        # Save AI response
        memory.save_message(user_id, "ai", response)


if __name__ == "__main__":
    main()
