import os
from dotenv import load_dotenv # this is to load the .env file
from supabase import create_client #this helps in executing supabase commands
from colorama import Fore

load_dotenv()       #this loads the .env file 
url = os.getenv("SUPABASE_URL")     #gets the url by looking at system active memory
key = os.getenv("SUPABASE_KEY")     #gets the key

supabase = create_client(url,key)   #i guess it establish the connection between database and my code 



def get_user_by_email(email):
    f = supabase.table("users").select("*").eq("username",email).execute() #returns the API response object and .data converts it to list
    if len(f.data):
        return f.data[0]
    return None

def create_user(
    email,
    hashed_password=None,
    is_verified=False,
    auth_provider="local",
    google_id=None,
    telegram_id=None
):
    d = {
        "username": email,
        "email": email,
        "password_hash": hashed_password,
        "is_verified": is_verified,
        "auth_provider": auth_provider,
        "google_id": google_id,
        "telegram_id": telegram_id
    }

    new_user = supabase.table("users").insert(d).execute()
    return new_user.data[0]["id"]

def get_user_by_telegram(tg_id: str):
    response = supabase.table("users").select("*").eq("telegram_id", str(tg_id)).execute()
    return response.data[0] if response.data else None

# 2. Create a new user specifically from Telegram
def create_telegram_user(tg_id: str, first_name: str):
    new_user = {
        "telegram_id": str(tg_id),
        "username": f"tg_{first_name}",
        "password_hash": None,
        "auth_provider": "telegram",
        "is_verified": True
    }

    response = supabase.table("users").insert(new_user).execute()
    return response.data[0] if response.data else None

def save_message(user_id, role, content):
    d={
        "user_id" : user_id,
        "role" : role,
        "content" : content
    }
    supabase.table("messages").insert(d).execute()
    
def fetch_history(user_id):
    response = supabase.table("messages").select("*").eq("user_id",user_id).order("created_at", desc=True).limit(25).execute()
    return list(reversed(response.data))



if __name__ == "__main__":
    print(f"\n{Fore.CYAN}🚀 Starting Unified Database Test (Web + Telegram)...{Fore.RESET}")

    # --- TEST 1: WEB USER FLOW ---
    print(f"\n{Fore.YELLOW}🌐 Testing Web User Flow...{Fore.RESET}")
    web_email = "anshuman@test.com"
    user_record = get_user_by_email(web_email)
    
    if not user_record:
        print("Creating new web user...")
        web_id = create_user(web_email, "secure_pass_123")
    else:
        web_id = user_record["id"]
    
    print(f"✅ Web User Linked! UUID: {web_id}")
    save_message(web_id, "user", "Hello from the Web Dashboard!")

    # --- TEST 2: TELEGRAM USER FLOW ---
    print(f"\n{Fore.YELLOW}📱 Testing Telegram Bot Flow...{Fore.RESET}")
    fake_tg_id = "5566778899" # Representative of a real Telegram chat.id
    
    # Check if this TG user already exists
    tg_user = get_user_by_telegram(fake_tg_id)
    
    if not tg_user:
        print("Bot seen for the first time. Provisioning shadow profile...")
        tg_user = create_telegram_user(fake_tg_id, "Anshuman_TG")
    
    tg_uuid = tg_user["id"]
    print(f"✅ Telegram User Linked! UUID: {tg_uuid}")
    save_message(tg_uuid, "user", "Hi RAAHAT, I'm messaging from Telegram.")

    # --- TEST 3: VERIFYING SHARED HISTORY ---
    print(f"\n{Fore.GREEN}📜 Fetching Consolidated History for Telegram User:{Fore.RESET}")
    history = fetch_history(tg_uuid)
    
    for row in history:
        timestamp = row['created_at'][:19].replace("T", " ")
        role_color = Fore.MAGENTA if row['role'] == "user" else Fore.BLUE
        print(f"{Fore.WHITE}[{timestamp}]{Fore.RESET} {role_color}{row['role'].upper()}:{Fore.RESET} {row['content']}")

    print(f"\n{Fore.CYAN}✨ Database Challenge Phase 2 Complete!{Fore.RESET}")