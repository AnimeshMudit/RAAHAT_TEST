import os
import time
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv # this is to load the .env file
from supabase import create_client #this helps in executing supabase commands
from colorama import Fore

load_dotenv()       #this loads the .env file 
url = os.getenv("SUPABASE_URL")     #gets the url by looking at system active memory
key = os.getenv("SUPABASE_KEY")     #gets the key

supabase = create_client(url,key)   #i guess it establish the connection between database and my code 

_MSG_COLS = "role,content,created_at"
_USER_PROFILE_COLS = "id,username,Name,is_verified,auth_provider,password_hash,google_id,telegram_id"
_LLM_HISTORY_LIMIT = 8          # 4 turns for LLM prompt
_STORAGE_HISTORY_LIMIT = 25     # unchanged storage/API limit
_THEME_HISTORY_LIMIT = 100
_CACHE_TTL_SEC = 120

_profile_cache: dict[str, tuple[float, dict | None]] = {}
_context_cache: dict[str, tuple[float, int, dict]] = {}


def _cache_get(store: dict, key: str, ttl: float = _CACHE_TTL_SEC):
    entry = store.get(key)
    if not entry:
        return None
    if time.monotonic() - entry[0] > ttl:
        store.pop(key, None)
        return None
    return entry


def invalidate_user_cache(user_id: str) -> None:
    uid = str(user_id)
    _profile_cache.pop(uid, None)
    _context_cache.pop(uid, None)


def get_user_by_email(email):
    f = supabase.table("users").select(_USER_PROFILE_COLS).eq("username",email).execute() #returns the API response object and .data converts it to list
    if len(f.data):
        return f.data[0]
    return None


def get_user_by_id(user_id: str):
    uid = str(user_id)
    cached = _cache_get(_profile_cache, uid)
    if cached is not None:
        return cached[1]
    response = supabase.table("users").select(_USER_PROFILE_COLS).eq("id", uid).execute()
    row = response.data[0] if response.data else None
    _profile_cache[uid] = (time.monotonic(), row)
    return row

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
    response = supabase.table("users").select(_USER_PROFILE_COLS).eq("telegram_id", str(tg_id)).execute()
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


def update_user_name(user_id: str, name: str):
    trimmed_name = (name or "").strip()
    response = (
        supabase.table("users")
        .update({"Name": trimmed_name})
        .eq("id", str(user_id))
        .execute()
    )
    invalidate_user_cache(user_id)
    return response.data[0] if response.data else None

def save_message(user_id, role, content):
    d={
        "user_id" : user_id,
        "role" : role,
        "content" : content
    }
    supabase.table("messages").insert(d).execute()
    invalidate_user_cache(user_id)
    
def fetch_messages(user_id, limit=_STORAGE_HISTORY_LIMIT, columns=_MSG_COLS):
    response = (
        supabase.table("messages")
        .select(columns)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(response.data))


def fetch_history(user_id):
    return fetch_messages(user_id, limit=_STORAGE_HISTORY_LIMIT)


def get_history_for_llm(user_id, history=None, limit=_LLM_HISTORY_LIMIT):
    """Return only the recent turns sent to the LLM (storage limit unchanged)."""
    rows = history if history is not None else fetch_history(user_id)
    if len(rows) <= limit:
        return rows
    return rows[-limit:]


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


def _score_themes_from_messages(user_messages: list[str], top_n: int = 3) -> tuple[str | None, list[str]]:
    if not user_messages:
        return None, []
    corpus = " ".join(user_messages)
    theme_scores: dict[str, int] = {}
    for theme, keywords in _THEME_KEYWORDS.items():
        hits = sum(corpus.count(kw) for kw in keywords)
        if hits > 0:
            theme_scores[theme] = hits
    if not theme_scores:
        return None, []
    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_themes[0][0], [t for t, _ in sorted_themes[:top_n]]


def session_summary_from_history(history: list[dict], user_id: str | None = None) -> dict | None:
    if not history:
        return None
    user_messages = [m["content"].lower() for m in history if m.get("role") == "user"]
    if not user_messages:
        return None
    dominant, top_themes = _score_themes_from_messages(user_messages, top_n=3)
    if not top_themes and not dominant:
        return None
    return {
        "user_id": user_id,
        "themes": top_themes,
        "dominant_emotion": dominant,
        "message_count": len(history),
    }


def recurring_themes_from_history(history: list[dict], top_n: int = 5) -> list[str]:
    if not history:
        return []
    user_messages = [m["content"].lower() for m in history if m.get("role") == "user"]
    if not user_messages:
        return []
    corpus = " ".join(user_messages)
    theme_scores: dict[str, int] = {}
    for theme, keywords in _THEME_KEYWORDS.items():
        hits = sum(corpus.count(keyword) for keyword in keywords)
        if hits > 0:
            theme_scores[theme] = hits
    ranked = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
    return [theme for theme, _ in ranked[:top_n]]


def get_session_summary(user_id: str) -> dict | None:
    """
    Queries the Supabase messages table for the given user's recent history and
    extracts the top emotional themes present in their messages.
    """
    history = fetch_history(user_id)
    return session_summary_from_history(history, user_id=user_id)


def get_recurring_themes(user_id: str, limit: int = _THEME_HISTORY_LIMIT):
    """Analyze a larger history window to identify recurring emotional themes."""
    history = fetch_messages(user_id, limit=limit)
    return recurring_themes_from_history(history)


def build_chat_context(user_id: str, history: list[dict] | None = None) -> dict:
    """
    Single-pass context builder for the chat pipeline.
    Fetches messages once, derives summary/themes, and trims LLM history.
    """
    uid = str(user_id)
    if history is None:
        cached = _cache_get(_context_cache, uid)
        if cached is not None:
            return cached[2]

        theme_history = fetch_messages(uid, limit=_THEME_HISTORY_LIMIT)
        message_count = len(theme_history)
        session_history = theme_history[-_STORAGE_HISTORY_LIMIT:] if message_count > _STORAGE_HISTORY_LIMIT else theme_history
    else:
        theme_history = history
        message_count = len(theme_history)
        session_history = theme_history

    session_summary = session_summary_from_history(session_history, user_id=uid)
    recurring_themes = recurring_themes_from_history(theme_history)
    llm_history = session_history[-_LLM_HISTORY_LIMIT:] if len(session_history) > _LLM_HISTORY_LIMIT else session_history

    context = {
        "history": session_history,
        "llm_history": llm_history,
        "session_summary": session_summary,
        "recurring_themes": recurring_themes,
        "message_count": message_count,
    }
    if history is None:
        _context_cache[uid] = (time.monotonic(), message_count, context)
    return context


def get_user_display_name(user_row: dict | None, preferred_name: str | None = None) -> str:
    if preferred_name and preferred_name.strip():
        return preferred_name.strip()
    if not user_row:
        return ""
    return str(
        user_row.get("Name")
        or user_row.get("display_name")
        or ""
    ).strip()


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
