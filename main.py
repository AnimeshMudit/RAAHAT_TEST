import os
import colorama
from colorama import Fore,Style
import getpass

from core import memory
from core import brain
from core import knowledge

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
        print(Fore.YELLOW + f"\nFirst boot detected! Reading knowledge from {data_folder} directory...")
        raw_text = knowledge.load_all_pdfs_from_folder(data_folder)
        
        if raw_text.strip():
            chunks = knowledge.split_chunks(raw_text)
            vector_db = knowledge.create_vector_store(chunks) 
            print(Fore.GREEN + f"Vector Vault Online! Processed {len(chunks)} total chunks.")
        else:
            print(Fore.RED + "Warning: PDFs were empty or unreadable.")
            vector_db = None
    else:
        print(Fore.RED + f" Warning: '{data_folder}' folder not found. RAAHAT will run without context.")
        vector_db = None
        
    print(Fore.CYAN + "\n--- SYSTEM LOGIN ---")
    
    #Authentication
    while True:
        user_name = input(Fore.YELLOW + "Enter your username: " + Style.RESET_ALL).strip()
        password = getpass.getpass(Fore.YELLOW + "Enter your password: " + Style.RESET_ALL) #need to know the working
         
        user_id = memory.get_or_create_user(user_name,password) 
        if user_id:
            print(Fore.GREEN + f"\nWelcome, {user_name}. RAAHAT is online and connected to Supabase. Type 'quit' to exit.\n")
            break
        else:
            print(Fore.RED + "❌ Login failed. Wrong username or password.")
            
    #greeting message
    print(Fore.CYAN + "—" * 60)
    
    greeting = (
        f"Welcome back, {user_name}.\n\n"
        "The world asks a lot of you, but here, you don't have to be anyone but yourself.\n"
        "Your secrets are safe, your burdens are shared, and your pace is respected.\n"
        "Whenever you're ready to let it out, I'm here to listen."
    )
    
    print(Fore.LIGHTWHITE_EX + greeting)
    print(Fore.CYAN + "—" * 60 + "\n")


    #saving greeting message to supabase so ai know it spoke first
    memory.save_message(user_id, "ai", greeting)
    
    while True:
        #User Input
        user_input = input(Fore.YELLOW + "You: " + Style.RESET_ALL)
        
        if not user_input: # Handle empty enters
            continue
        
        if user_input.lower() in ['quit', 'exit']:
            print(Fore.CYAN + "RAAHAT shutting down. Take care.")
            break
        
        #user query is saved 
        memory.save_message(user_id, "user", user_input)
        
        context_text = ""
        if vector_db:
            # Search the PDF and join the top 3 chunks into one big string
            results = knowledge.search_knowledge(user_input, vector_db)
            context_text = "\n".join(results)
        
        # Retrieve Past Memory
        chat_history = memory.fetch_history(user_id)
        
        # Generate Brain Response
        response = brain.get_response(user_input, chat_history, context_text)
        
        # Speak to the User
        print(Fore.GREEN + f"RAAHAT: {response}\n")
        
        # Save AI response to the Cloud
        memory.save_message(user_id, "ai", response)

if __name__ == "__main__":
    main()