import os
# pyrefly: ignore [missing-import]
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


# ── Emotion theme keyword mapping ──────────────────────────────────────────────
_THEME_KEYWORDS: dict[str, list[str]] = {
    "anxiety":      ["anxious", "anxiety", "panic", "nervous", "worry", "worrying", "restless", "on edge"],
    "depression":   ["depressed", "depression", "hopeless", "sad", "empty", "numb", "worthless", "meaningless"],
    "overwhelm":    ["overwhelmed", "overwhelm", "too much", "can't cope", "cannot cope", "drowning", "exhausted", "burnout"],
    "isolation":    ["alone", "lonely", "loneliness", "isolated", "no one", "nobody", "disconnected"],
    "anger":        ["angry", "anger", "furious", "rage", "frustrated", "frustration", "irritated", "irritable"],
    "grief":        ["grief", "grieving", "loss", "lost", "miss", "missing", "mourn", "mourning"],
    "guilt":        ["guilty", "guilt", "blame", "my fault", "ashamed", "shame", "regret"],
    "self_harm":    ["hurt myself", "self harm", "cut myself", "cutting", "suicidal", "end it all", "kill myself"],
}


def get_session_summary(user_id: str) -> dict | None:
    """
    Queries the Supabase messages table for the given user's recent history and
    extracts the top emotional themes present in their messages.

    Returns a dict of shape:
        {
            "user_id": str,
            "themes": list[str],          # Up to 3 dominant emotion categories
            "dominant_emotion": str | None,  # Single top emotion, or None
            "message_count": int
        }
    Returns None if the user has no messages.
    """
    history = fetch_history(user_id)
    if not history:
        return None

    # Build a single lowercase corpus from user-side messages only
    user_messages = [m["content"].lower() for m in history if m.get("role") == "user"]
    if not user_messages:
        return None

    corpus = " ".join(user_messages)

    # Count how many keyword hits each theme gets
    theme_scores: dict[str, int] = {}
    for theme, keywords in _THEME_KEYWORDS.items():
        hits = sum(corpus.count(kw) for kw in keywords)
        if hits > 0:
            theme_scores[theme] = hits

    if not theme_scores:
        dominant = None
        top_themes = []
    else:
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        dominant = sorted_themes[0][0]
        top_themes = [t for t, _ in sorted_themes[:3]]

    return {
        "user_id": user_id,
        "themes": top_themes,
        "dominant_emotion": dominant,
        "message_count": len(history),
    }
    
def get_recurring_themes(user_id: str, limit: int = 100):
    """
    Analyze a larger history window to identify recurring emotional themes.
    Used for long-term continuity.
    """

    response = (
        supabase.table("messages")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    history = list(reversed(response.data))

    if not history:
        return []

    user_messages = [
        m["content"].lower()
        for m in history
        if m.get("role") == "user"
    ]

    corpus = " ".join(user_messages)

    theme_scores = {}

    for theme, keywords in _THEME_KEYWORDS.items():

        hits = sum(
            corpus.count(keyword)
            for keyword in keywords
        )

        if hits > 0:
            theme_scores[theme] = hits

    ranked = sorted(
        theme_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [theme for theme, _ in ranked[:5]]




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
    
    save_message(
    tg_uuid,
    "user",
    "Hi RAAHAT, I'm messaging from Telegram." 
    )


    # --- TEST 3: VERIFYING SHARED HISTORY ---
    print(f"\n{Fore.GREEN}📜 Fetching Consolidated History for Telegram User:{Fore.RESET}")
    history = fetch_history(tg_uuid)
    
    print(f"\n{Fore.CYAN}🧠 Session Summary:{Fore.RESET}")
    print(get_session_summary(tg_uuid))

    print(f"\n{Fore.CYAN}🔁 Recurring Themes:{Fore.RESET}")
    print(get_recurring_themes(tg_uuid))
    
    for row in history:
        timestamp = row['created_at'][:19].replace("T", " ")
        role_color = Fore.MAGENTA if row['role'] == "user" else Fore.BLUE
        print(f"{Fore.WHITE}[{timestamp}]{Fore.RESET} {role_color}{row['role'].upper()}:{Fore.RESET} {row['content']}")

    print(f"\n{Fore.CYAN}✨ Database Challenge Phase 2 Complete!{Fore.RESET}")