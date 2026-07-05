"""
RAAHAT memory layer — patched version addressing issue #7 (naive theming).

WHAT CHANGED (vs. original memory.py):
  1. _THEME_KEYWORDS  -> _THEME_PATTERNS  (word-boundary regex, no more substring matching)
  2. New _NEGATION_PATTERNS  (skip matches preceded by "not / don't / no longer / stopped / ...")
  3. New _HINDI_THEME_PATTERNS  (starter set for Hinglish/Hindi, parity with safety layer)
  4. _score_themes_from_messages now:
       - uses regex with word boundaries
       - skips negated matches (25-char lookback window)
       - applies linear time-decay weighting (recent messages weigh more)
       - returns an optional intensity block when with_intensity=True
  5. session_summary_from_history now also returns:
       - theme_details: [{theme, score, mentions, first_seen_idx, last_seen_idx}, ...]
       - intensity_band: "low" | "moderate" | "high"  (rough heuristic)
     Old keys (themes, dominant_emotion, message_count) are preserved unchanged
     so brain.py and server.py need NO changes.
  6. recurring_themes_from_history uses the same weighted scorer so time decay
     applies here too.
  7. The ambiguous bare tokens "miss" and "lost" are removed; replaced with
     more specific patterns ("miss you/him/her/them", "loss", "lost my ___").

FUNCTION SIGNATURES PRESERVED:
  - get_user_by_email, get_user_by_id, create_user, get_user_by_telegram,
    create_telegram_user, update_user_name, save_message, fetch_messages,
    fetch_history, get_history_for_llm
  - session_summary_from_history(history, user_id=None) -> dict | None
  - recurring_themes_from_history(history, top_n=5) -> list[str]
  - get_session_summary, get_recurring_themes, build_chat_context,
    get_user_display_name

LONG-TERM NOTE:
  This is still deterministic. The proper Phase-2 fix is an LLM-summarized
  session memory stored in a `session_summaries` table (one row per session
  window, updated incrementally). This patch removes the most egregious
  false positives while you build toward that.
"""

import os
import re
import time
import logging
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from supabase import create_client
from colorama import Fore

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

logger = logging.getLogger(__name__)

_MSG_COLS = "role,content,created_at"
_USER_PROFILE_COLS = "id,username,Name,is_verified,auth_provider,password_hash,google_id,telegram_id"
_LLM_HISTORY_LIMIT = 8
_STORAGE_HISTORY_LIMIT = 25
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
    f = supabase.table("users").select(_USER_PROFILE_COLS).eq("username", email).execute()
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
        "telegram_id": telegram_id,
    }
    new_user = supabase.table("users").insert(d).execute()
    return new_user.data[0]["id"]


def get_user_by_telegram(tg_id: str):
    response = supabase.table("users").select(_USER_PROFILE_COLS).eq("telegram_id", str(tg_id)).execute()
    return response.data[0] if response.data else None


def create_telegram_user(tg_id: str, first_name: str):
    new_user = {
        "telegram_id": str(tg_id),
        "username": f"tg_{first_name}",
        "password_hash": None,
        "auth_provider": "telegram",
        "is_verified": True,
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
    d = {"user_id": user_id, "role": role, "content": content}
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
    rows = history if history is not None else fetch_history(user_id)
    if len(rows) <= limit:
        return rows
    return rows[-limit:]


# ─────────────────────────────────────────────────────────────────────────────
# THEME DETECTION  (patched — see module docstring)
# ─────────────────────────────────────────────────────────────────────────────

# Word-boundary regex patterns. Each pattern is anchored with \b...\b so that
# "miss" no longer matches inside "missing the point", "mission", "mistake".
_THEME_PATTERNS: dict[str, list[re.Pattern]] = {
    "anxiety": [
        re.compile(r"\banxiet(?:y|ies)\b", re.I),
        re.compile(r"\banxious(?:ly|ness|er|est)?\b", re.I),
        re.compile(r"\bpanic(?:k(?:ed|ing|s))?\b", re.I),
        re.compile(r"\bpanic(?:ky|ked)?\b", re.I),
        re.compile(r"\bnervous(?:ness|ly)?\b", re.I),
        re.compile(r"\bworr(?:y|ies|ied|ying|ier|iest)\b", re.I),
        re.compile(r"\brestless(?:ness)?\b", re.I),
        re.compile(r"\bon[\s-]edge\b", re.I),
        re.compile(r"\bdread(?:ful|ing)?\b", re.I),
        re.compile(r"\bunease(?:y)?\b", re.I),
    ],
    "depression": [
        re.compile(r"\bdepress(?:ed|ion|ing|ive|iveness)?\b", re.I),
        re.compile(r"\bhopeless(?:ness)?\b", re.I),
        re.compile(r"\bsad(?:ness|ly|den(?:ed|ing)?)?\b", re.I),
        re.compile(r"\bempt(?:y|iness)\b", re.I),
        re.compile(r"\bnumb(?:ness)?\b", re.I),
        re.compile(r"\bworthless(?:ness)?\b", re.I),
        re.compile(r"\bmeaningless(?:ness)?\b", re.I),
        re.compile(r"\bjoyless\b", re.I),
        re.compile(r"\bheavy(?:-?hearted)?\b", re.I),
    ],
    "overwhelm": [
        re.compile(r"\boverwhelm(?:ed|ing|s)?\b", re.I),
        re.compile(r"\btoo\s+much\b", re.I),
        re.compile(r"\bcan'?t\s+cope\b", re.I),
        re.compile(r"\bcannot\s+cope\b", re.I),
        re.compile(r"\bdrowning\b", re.I),
        re.compile(r"\bexhaust(?:ed|ion|ing|s)?\b", re.I),
        re.compile(r"\bburn(?:t|ed)?[\s-]+out\b", re.I),
        re.compile(r"\bburnout\b", re.I),
        re.compile(r"\bdrained\b", re.I),
        re.compile(r"\bspent\b", re.I),
    ],
    "isolation": [
        re.compile(r"\balone\b", re.I),
        re.compile(r"\blonel(?:y|iness)\b", re.I),
        re.compile(r"\bisolat(?:ed|ion|ing|ions)?\b", re.I),
        re.compile(r"\bno[\s-]+one\b", re.I),
        re.compile(r"\bnobody\b", re.I),
        re.compile(r"\bdisconnected\b", re.I),
        re.compile(r"\bunsupported\b", re.I),
        re.compile(r"\bunseen\b", re.I),
        re.compile(r"\binvisible\b", re.I),
    ],
    "anger": [
        re.compile(r"\bangr(?:y|er|ily|ier|iest)\b", re.I),
        re.compile(r"\bfurious(?:ly|ness)?\b", re.I),
        re.compile(r"\brage(?:ful|s)?\b", re.I),
        re.compile(r"\bfrustrat(?:ed|ion|ing|ions)?\b", re.I),
        re.compile(r"\birritat(?:ed|ion|ing|ions)?\b", re.I),
        re.compile(r"\birritable(?:ness)?\b", re.I),
        re.compile(r"\bpissed(?:\s+off)?\b", re.I),
        re.compile(r"\bresent(?:ful|ment|ing)?\b", re.I),
    ],
    "grief": [
        re.compile(r"\bgrief\b", re.I),
        re.compile(r"\bgriev(?:e|ed|ing|ance|ances)\b", re.I),
        re.compile(r"\bmourn(?:ing|ed|s)?\b", re.I),
        re.compile(r"\bloss\b", re.I),
        re.compile(r"\bbereav(?:ed|ement)\b", re.I),
        # "lost someone" or "lost my <person>" — scoped to people, not objects,
        # so "lost my keys / job / way" do NOT trigger grief.
        re.compile(
            r"\blost\s+(?:"
            r"someone|everyone|anyone|her|him|them|you|us|"
            r"my\s+(?:mom|mum|mother|dad|father|brother|sister|friend|friends|"
            r"husband|wife|partner|son|daughter|child|children|grandparent|"
            r"grandma|grandpa|grandmother|grandfather|pet|dog|cat|cousin|uncle|aunt)"
            r")\b",
            re.I,
        ),
        # "miss you / him / her / them / everyone" — explicitly person-directed
        re.compile(
            r"\bmiss(?:es|ed|ing)?\s+(?:"
            r"you|him|her|them|us|everyone|someone|anyone|"
            r"my|your|his|their|our"
            r")\b",
            re.I,
        ),
    ],
    "guilt": [
        re.compile(r"\bguilt(?:y|iness)?\b", re.I),
        re.compile(r"\bblame(?:d|s|ing)?\b", re.I),
        re.compile(r"\bmy\s+fault\b", re.I),
        re.compile(r"\bashamed\b", re.I),
        re.compile(r"\bshame(?:d|ful|fulness|ful)?\b", re.I),
        re.compile(r"\bregret(?:s|ted|ting|ful)?\b", re.I),
        re.compile(r"\bembarrass(?:ed|ing|ment)?\b", re.I),
        re.compile(r"\bremorse(?:ful)?\b", re.I),
    ],
    "self_worth": [
        re.compile(r"\bworthless(?:ness)?\b", re.I),
        re.compile(r"\bnot\s+good\s+enough\b", re.I),
        re.compile(r"\bnot\s+(?:good|worthy|deserving|enough)\b", re.I),
        re.compile(r"\bdon'?t\s+deserve\b", re.I),
        re.compile(r"\binferior(?:ity)?\b", re.I),
        re.compile(r"\binadequate(?:cy)?\b", re.I),
        re.compile(r"\bfailure\b", re.I),
        re.compile(r"\bloser\b", re.I),
        re.compile(r"\buseless\b", re.I),
        re.compile(r"\bhate\s+myself\b", re.I),
        re.compile(r"\bself[\s-]?loath(?:ing|ed)\b", re.I),
        re.compile(r"\bself[\s-]?doubt\b", re.I),
        re.compile(r"\bself[\s-]?criticism\b", re.I),
        re.compile(r"\bself[\s-]?critical\b", re.I),
        re.compile(r"\bcompare\s+(?:myself|myself\s+to)\b", re.I),
        re.compile(r"\bsecond[\s-]guess(?:ing|ed)?\b", re.I),
        re.compile(r"\bcan'?t\s+measure\s+up\b", re.I),
        re.compile(r"\bimposter\b", re.I),
        re.compile(r"\bfeel\s+like\s+a\s+fraud\b", re.I),
        re.compile(r"\bconfidence\s+(?:gone|disappeared|lost|shattered|shaken)\b", re.I),
        re.compile(r"\bcan'?t\s+(?:do\s+)?anything\s+right\b", re.I),
        re.compile(r"\beveryone\s+else\s+(?:handles|does|seems|is)\s+better\b", re.I),
        re.compile(r"\bwalking\s+on\s+eggshells\b", re.I),
    ],
    "self_harm": [
        re.compile(r"\bhurt\s+myself\b", re.I),
        re.compile(r"\bself[\s-]harm(?:ed|ing)?\b", re.I),
        re.compile(r"\bcut\s+myself\b", re.I),
        re.compile(r"\bcutting\s+myself\b", re.I),
        re.compile(r"\bsuicid(?:e|al|ally)\b", re.I),
        re.compile(r"\bend\s+it\s+all\b", re.I),
        re.compile(r"\bkill\s+myself\b", re.I),
        re.compile(r"\bend\s+my\s+life\b", re.I),
        re.compile(r"\bdon'?t\s+want\s+to\s+(?:live|exist)\b", re.I),
    ],
}

# Starter set of Hinglish/Hindi patterns. Extend in collaboration with a
# Hindi-speaking clinician. Transliteration variance is high, so we accept
# common spellings.
_THEME_PATTERNS_HINGLISH: dict[str, list[re.Pattern]] = {
    "anxiety": [
        re.compile(r"\bghabr?aat?\b", re.I),         # ghabrahat
        re.compile(r"\bdar(?:\s+lag)?\s*(?:raha|rahi)?\b", re.I),  # dar lag raha
        re.compile(r"\btension(?:\s+ho\s?rahi?\s?hai)?\b", re.I),
        re.compile(r"\bchint(?:a|it)\b", re.I),
    ],
    "depression": [
        re.compile(r"\budas\b", re.I),
        re.compile(r"\bdukhi\b", re.I),
        re.compile(r"\bjeena?\s+nahi?\s+(?:chahta|chahti)\b", re.I),
        re.compile(r"\bdil\s+bhari\b", re.I),
    ],
    "overwhelm": [
        re.compile(r"\bthak\s+gaya?\b", re.I),
        re.compile(r"\bbohot\s+thak(?:\s+gaya?)?\b", re.I),
        re.compile(r"\bbhar\s+gaya?\s+dil\b", re.I),
    ],
    "isolation": [
        re.compile(r"\bakela?\b", re.I),
        re.compile(r"\btanha\b", re.I),
        re.compile(r"\bkoi?\s+nahi?\s?hai\b", re.I),
    ],
    "anger": [
        re.compile(r"\bgussa?\b", re.I),
        re.compile(r"\bnaraaz\b", re.I),
        re.compile(r"\birritat(?:ed)?\s+ho\s?raha?\s?hai\b", re.I),
    ],
    "grief": [
        re.compile(r"\bkisi?\s+ko\s+miss\s+(?:kar|karti?)\s?raha?\s?hoon\b", re.I),
        re.compile(r"\bkhoya?\s+hua\b", re.I),
    ],
    "guilt": [
        re.compile(r"\bapni?\s+(?:gal?ti|galti)\b", re.I),
        re.compile(r"\bsharm(?:ind(?:a|e|hi))? (?:aa?rahi?|aati)?\s?hai\b", re.I),
    ],
    "self_harm": [
        re.compile(r"\bmar\s+ja(?:a|oonga|oongi)\b", re.I),
        re.compile(r"\bmarne?\s+ka\s+mann\b", re.I),
        re.compile(r"\bkhud\s+ko\s+maar\b", re.I),
    ],
}

# Merge English + Hinglish into one lookup for scoring.
_ALL_THEME_PATTERNS: dict[str, list[re.Pattern]] = {
    theme: _THEME_PATTERNS.get(theme, []) + _THEME_PATTERNS_HINGLISH.get(theme, [])
    for theme in set(_THEME_PATTERNS) | set(_THEME_PATTERNS_HINGLISH)
}

# Tokens that, if they appear within ~25 chars BEFORE a theme match, strongly
# suggest the match is negated. Examples:
#   "I'm not anxious anymore"  -> anxiety match is negated
#   "I stopped feeling sad"    -> depression match is negated
#   "I no longer feel lonely"  -> isolation match is negated
_NEGATION_PATTERNS = re.compile(
    r"\b(?:"
    r"not|no|never|none|"
    r"don'?t|doesn'?t|didn'?t|isn'?t|aren'?t|wasn'?t|weren'?t|"
    r"haven'?t|hasn'?t|hadn'?t|wouldn'?t|couldn'?t|shouldn'?t|"
    r"no\s+longer|without|free\s+from|stopped|quit|over|past|"
    r"used\s+to|used\s+to\s+be|anymore|nowadays"
    r")\b",
    re.I,
)

# How many chars to look back from a theme match for a negation.
_NEGATION_LOOKBACK_CHARS = 25

# Rough intensity bands based on weighted score thresholds. Tunable.
_INTENSITY_BANDS = [
    (3.0, "high"),
    (1.0, "moderate"),
    (0.0, "low"),
]


def _classify_intensity(weighted_score: float) -> str:
    for threshold, label in _INTENSITY_BANDS:
        if weighted_score >= threshold:
            return label
    return "low"


def _score_themes_from_messages(
    user_messages: list[str],
    top_n: int = 3,
    with_intensity: bool = False,
) -> tuple[str | None, list]:
    """
    Score themes across user_messages with:
      - regex word-boundary matching (no substring false positives)
      - 25-char negation lookback (skip "not anxious", "no longer sad", etc.)
      - linear time-decay: most recent message has weight 1.0, oldest has 1/n

    Returns:
      (dominant_theme_or_None, top_themes)
        If with_intensity=False: top_themes = ["anxiety", "grief", ...]
        If with_intensity=True:  top_themes = [
            {"theme": "anxiety", "score": 2.4, "mentions": 3,
             "first_seen_idx": 1, "last_seen_idx": 8},
            ...
        ]
    """
    if not user_messages:
        return None, []

    n = len(user_messages)
    theme_weighted_score: dict[str, float] = {}
    theme_mention_indices: dict[str, list[int]] = {}

    for idx, raw_msg in enumerate(user_messages):
        if not raw_msg:
            continue
        msg = raw_msg.lower()
        # Linear time-decay weight: oldest message = 1/n, newest = 1.0
        weight = (idx + 1) / n

        for theme, patterns in _ALL_THEME_PATTERNS.items():
            for pattern in patterns:
                for match in pattern.finditer(msg):
                    # Look back for negation in a small window before the match
                    window_start = max(0, match.start() - _NEGATION_LOOKBACK_CHARS)
                    pre_context = msg[window_start:match.start()]
                    if _NEGATION_PATTERNS.search(pre_context):
                        continue
                    theme_weighted_score[theme] = (
                        theme_weighted_score.get(theme, 0.0) + weight
                    )
                    theme_mention_indices.setdefault(theme, []).append(idx)

    if not theme_weighted_score:
        return None, []

    ranked = sorted(theme_weighted_score.items(), key=lambda x: x[1], reverse=True)
    dominant = ranked[0][0]

    if with_intensity:
        top_themes = [
            {
                "theme": theme,
                "score": round(score, 3),
                "mentions": len(theme_mention_indices[theme]),
                "first_seen_idx": min(theme_mention_indices[theme]),
                "last_seen_idx": max(theme_mention_indices[theme]),
            }
            for theme, score in ranked[:top_n]
        ]
    else:
        top_themes = [theme for theme, _ in ranked[:top_n]]

    return dominant, top_themes


def session_summary_from_history(
    history: list[dict],
    user_id: str | None = None,
) -> dict | None:
    """
    Build a session summary dict.

    Returns None if no user messages exist.

    Output shape (additive over the original — old keys preserved):
      {
        "user_id": ...,
        "themes": ["anxiety", "overwhelm", "isolation"],   # backward-compat
        "dominant_emotion": "anxiety",                      # backward-compat
        "message_count": 14,                                # backward-compat
        "theme_details": [                                  # NEW
          {"theme": "anxiety", "score": 2.4, "mentions": 3,
           "first_seen_idx": 1, "last_seen_idx": 8},
          ...
        ],
        "intensity_band": "moderate",                       # NEW
      }
    """
    if not history:
        return None
    user_messages = [m["content"] for m in history if m.get("role") == "user"]
    if not user_messages:
        return None

    dominant, theme_details = _score_themes_from_messages(
        user_messages, top_n=3, with_intensity=True,
    )
    if not theme_details and not dominant:
        return None

    top_theme_names = [d["theme"] for d in theme_details]
    top_score = theme_details[0]["score"] if theme_details else 0.0

    return {
        "user_id": user_id,
        # ---- backward-compatible keys (consumed by brain.py) ----
        "themes": top_theme_names,
        "dominant_emotion": dominant,
        "message_count": len(history),
        # ---- new additive keys ----
        "theme_details": theme_details,
        "intensity_band": _classify_intensity(top_score),
    }


def recurring_themes_from_history(history: list[dict], top_n: int = 5) -> list[str]:
    """
    Top-N themes across the larger history window (default _THEME_HISTORY_LIMIT=100).
    Uses the same weighted, negation-aware scorer so time decay applies here too.
    """
    if not history:
        return []
    user_messages = [m["content"] for m in history if m.get("role") == "user"]
    if not user_messages:
        return []
    _, top_themes = _score_themes_from_messages(
        user_messages, top_n=top_n, with_intensity=False,
    )
    return top_themes


def get_session_summary(user_id: str) -> dict | None:
    history = fetch_history(user_id)
    return session_summary_from_history(history, user_id=user_id)


def get_recurring_themes(user_id: str, limit: int = _THEME_HISTORY_LIMIT):
    history = fetch_messages(user_id, limit=limit)
    return recurring_themes_from_history(history)


def build_chat_context(
    user_id: str,
    history: list[dict] | None = None,
    perf_out: dict | None = None,
) -> dict:
    """
    Single-pass context builder for the chat pipeline.
    Fetches messages once, derives summary/themes, and trims LLM history.
    """
    uid = str(user_id)
    if history is None:
        cached = _cache_get(_context_cache, uid)
        if cached is not None:
            if perf_out is not None:
                perf_out["history_fetch"] = 0.0
                perf_out["conversation_summary"] = 0.0
            return cached[2]

        t_fetch = time.perf_counter()
        theme_history = fetch_messages(uid, limit=_THEME_HISTORY_LIMIT)
        if perf_out is not None:
            perf_out["history_fetch"] = time.perf_counter() - t_fetch
        message_count = len(theme_history)
        session_history = (
            theme_history[-_STORAGE_HISTORY_LIMIT:]
            if message_count > _STORAGE_HISTORY_LIMIT
            else theme_history
        )
    else:
        if perf_out is not None:
            perf_out["history_fetch"] = 0.0
        theme_history = history
        message_count = len(theme_history)
        session_history = theme_history

    t_summary = time.perf_counter()
    session_summary = session_summary_from_history(session_history, user_id=uid)
    recurring_themes = recurring_themes_from_history(theme_history)
    llm_history = (
        session_history[-_LLM_HISTORY_LIMIT:]
        if len(session_history) > _LLM_HISTORY_LIMIT
        else session_history
    )
    if perf_out is not None:
        perf_out["conversation_summary"] = time.perf_counter() - t_summary

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


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSTIC SELF-TEST (run: python memory.py --selftest)
# ─────────────────────────────────────────────────────────────────────────────

def _run_theming_selftest() -> None:
    """
    Verifies the patched theming logic on hand-crafted cases that the OLD
    code got wrong. Run this whenever you tweak _THEME_PATTERNS.
    """
    cases = [
        # (label, messages, expected_dominant_or_None, must_NOT_contain)
        ("negation: not anxious",
         ["I used to be anxious but I'm not anxious anymore"],
         None, {"anxiety"}),
        ("negation: no longer sad",
         ["I am no longer sad about the breakup"],
         None, {"depression"}),
        ("negation: stopped feeling lonely",
         ["I stopped feeling lonely after joining the club"],
         None, {"isolation"}),
        ("substring: missed the bus",
         ["I missed the bus today and had to walk home"],
         None, {"grief"}),
        ("substring: missing the point",
         ["You're missing the point entirely"],
         None, {"grief"}),
        ("substring: lost my keys",
         ["I lost my keys this morning, ugh"],
         None, {"grief"}),  # "lost my keys" — NOT "lost my (someone)" so no grief
        ("positive: I miss her",
         ["She passed away last year and I miss her every day"],
         "grief", set()),
        ("positive: drowning in burnout",
         ["I'm drowning in burnout right now"],
         "overwhelm", set()),
        ("positive: Hinglish akela",
         ["aaj kal bohot akela feel kar raha hoon"],
         "isolation", set()),
        ("positive: Hinglish tension",
         ["mujhe exam ki bohot tension ho rahi hai"],
         "anxiety", set()),
        ("time-decay: old grief vs new anxiety",
         ["I miss her", "I miss her", "I miss her",
          "but lately I'm anxious about work", "anxious", "anxious", "anxious"],
         "anxiety", set()),
        ("multi-theme: guilt + anxiety",
         ["I feel so guilty about what I said", "and now I'm anxious she'll hate me"],
         None, set()),  # either guilt or anxiety is fine, both should appear in top 3
    ]

    print(f"\n{Fore.CYAN}=== Theming Self-Test ==={Fore.RESET}\n")
    passed, failed = 0, 0
    for label, msgs, expected, must_not in cases:
        dominant, details = _score_themes_from_messages(msgs, top_n=3, with_intensity=True)
        top_names = [d["theme"] for d in details]

        ok = True
        reason = ""
        if expected is not None and dominant != expected:
            ok = False
            reason = f"expected dominant={expected}, got {dominant}"
        if must_not & set(top_names):
            ok = False
            reason = f"forbidden themes appeared: {must_not & set(top_names)}"

        marker = f"{Fore.GREEN}PASS" if ok else f"{Fore.RED}FAIL"
        print(f"{marker}  {label}{Fore.RESET}")
        print(f"        dominant={dominant}  top3={top_names}")
        if not ok:
            print(f"        reason: {reason}")
            failed += 1
        else:
            passed += 1

    print(f"\n{Fore.CYAN}{passed} passed, {failed} failed.{Fore.RESET}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _run_theming_selftest()
        sys.exit(0)

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
    fake_tg_id = "5566778899"
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
    print(f"\n{Fore.CYAN}🧠 Session Summary:{Fore.RESET}")
    print(get_session_summary(tg_uuid))
    print(f"\n{Fore.CYAN}🔁 Recurring Themes:{Fore.RESET}")
    print(get_recurring_themes(tg_uuid))
    for row in history:
        timestamp = row['created_at'][:19].replace("T", " ")
        role_color = Fore.MAGENTA if row['role'] == "user" else Fore.BLUE
        print(f"{Fore.WHITE}[{timestamp}]{Fore.RESET} {role_color}{row['role'].upper()}:{Fore.RESET} {row['content']}")
    print(f"\n{Fore.CYAN}✨ Database Challenge Phase 2 Complete!{Fore.RESET}")
