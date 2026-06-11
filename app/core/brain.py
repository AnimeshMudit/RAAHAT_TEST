import os
import json
import random
import re
from dotenv import load_dotenv
from groq import Groq
import logging

logger = logging.getLogger(__name__)

load_dotenv()
api_keys = []
for env_name in ("GROQ_API_KEY", "FALLBACK_KEY"):
    value = os.getenv(env_name)
    if value and value not in api_keys:
        api_keys.append(value)

if not api_keys:
    raise ValueError("GROQ_API_KEY or FALLBACK_KEY not found.")

clients = [Groq(api_key=value) for value in api_keys]

DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

_BEHAVIOR_EXAMPLES: list = []
_CACHED_BEHAVIOR_EXAMPLE_BLOCK = ""
_PROMPT_HISTORY_MESSAGE_LIMIT = 8
_PROMPT_HISTORY_WITH_SUMMARY_LIMIT = 6


def _compress_whitespace(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _format_behavior_examples(examples, num_examples=3) -> str:
    if not examples:
        return ""
    selected = random.sample(examples, min(num_examples, len(examples)))
    return "\n\n".join(
        f"U: {ex['user']}\nR: {ex['good_response']}"
        for ex in selected
    )


def _load_behavior_examples_once() -> list:
    try:
        path = os.path.join(os.path.dirname(__file__), "behaviour_examples.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("Failed to load behaviour examples")
        return []


_BEHAVIOR_EXAMPLES = _load_behavior_examples_once()
_CACHED_BEHAVIOR_EXAMPLE_BLOCK = _compress_whitespace(
    _format_behavior_examples(_BEHAVIOR_EXAMPLES)
)

ACTIVE_SAFETY_OVERRIDE = """
CRISIS MODE ACTIVE. User may be in crisis or suicidal ideation.
Respond with warmth, calm, empathy. Acknowledge what they said first.
Keep RAAHAT personality — not robotic or clinical. Be concise.
Ask at most one gentle question.
"""

CRISIS_RESOURCE_CARD = """
**Need immediate support? approved Indian resources:**
- Kiran Mental Health Helpline: 14416 (24/7, free, multilingual)
- iCall: 9152987821 (Monday-Saturday, 10 AM-8 PM)
- Vandrevala Foundation: 1860-2662-345 or 9999-666-555 (24/7)
"""

CLASSIFIER_SYSTEM_PROMPT = """
You are a safety classification assistant.
Classify the user message into exactly one category:
- SAFE: Everyday chat, general queries, positive topics, minor ordinary stress.
- LOW: Sadness, relationship problems, stress, exam anxiety, fatigue, venting — no self-harm or death hints.
- HIGH: Indirect self-harm, deep hopelessness, passive suicidal ideation.
- CRISIS: Explicit suicidal ideation, self-harm, intent or plans.

Output ONLY: SAFE, LOW, HIGH, or CRISIS.
"""

_SAFETY_PATTERNS = [
    ("suicidal", re.compile(r"\bsuicidal\b", re.IGNORECASE)),
    ("I should die", re.compile(r"\bi\b.*\bshould\b.*\bdie\b", re.IGNORECASE)),
    ("I want to end my life", re.compile(r"\bi\b.*\bwant\b.*\b(to\b.*\b)?end\b.*\b(my\b.*\b)?life\b", re.IGNORECASE)),
    ("I don't wish to live anymore", re.compile(r"\bi\b.*\bdon'?t\b.*\bwish\b.*\bto\b.*\blive\b", re.IGNORECASE)),
    ("goodbye everyone", re.compile(r"\bgoodbye\b.*\beveryone\b", re.IGNORECASE)),
    ("goodbye mate", re.compile(r"\bgoodbye\b.*\bmate\b", re.IGNORECASE)),
    ("take the wrong step", re.compile(r"\btake\b.*\b(the\b.*\b)?wrong\b.*\bstep\b", re.IGNORECASE)),
    ("everyone would be better without me", re.compile(r"\b(everyone\b.*\bbetter\b.*\bwithout\b.*\bme\b|better\b.*\boff\b.*\bwithout\b.*\bme\b)", re.IGNORECASE)),
    ("no reason to continue", re.compile(r"\bno\b.*\breason\b.*\b(to\b.*\b)?continue\b", re.IGNORECASE)),
    ("wish I were dead", re.compile(r"\bwish\b.*\bi\b.*\b(were|was)\b.*\bdead\b", re.IGNORECASE)),
    ("suicide", re.compile(r"\bsuicide\b", re.IGNORECASE)),
    ("kill myself", re.compile(r"\bkill\b.*\bmyself\b", re.IGNORECASE)),
    ("killing myself", re.compile(r"\bkilling\b.*\bmyself\b", re.IGNORECASE)),
    ("want to die", re.compile(r"\bwant\b.*\bto\b.*\bdie\b", re.IGNORECASE)),
    ("wanted to die", re.compile(r"\bwanted\b.*\bto\b.*\bdie\b", re.IGNORECASE)),
    ("better off dead", re.compile(r"\bbetter\b.*\boff\b.*\bdead\b", re.IGNORECASE)),
    ("don't want to live", re.compile(r"\bdon'?t\b.*\bwant\b.*\bto\b.*\blive\b", re.IGNORECASE)),
    ("do not want to live", re.compile(r"\bdo\b.*\bnot\b.*\bwant\b.*\bto\b.*\blive\b", re.IGNORECASE)),
    ("no reason to live", re.compile(r"\bno\b.*\breason\b.*\bto\b.*\blive\b", re.IGNORECASE)),
    ("no reason to be alive", re.compile(r"\bno\b.*\breason\b.*\bto\b.*\bbe\b.*\balive\b", re.IGNORECASE)),
    ("end it all", re.compile(r"\bend\b.*\bit\b.*\ball\b", re.IGNORECASE)),
    ("take my life", re.compile(r"\btake\b.*\bmy\b.*\blife\b", re.IGNORECASE)),
    ("goodbye forever", re.compile(r"\bgoodbye\b.*\bforever\b", re.IGNORECASE)),
    ("no point going on", re.compile(r"\bno\b.*\bpoint\b.*\bgoing\b.*\bon\b", re.IGNORECASE)),
    ("no point in going on", re.compile(r"\bno\b.*\bpoint\b.*\bin\b.*\bgoing\b.*\bon\b", re.IGNORECASE)),
    ("can't go on", re.compile(r"\bcan'?t\b.*\bgo\b.*\bon\b", re.IGNORECASE)),
    ("cannot go on", re.compile(r"\bcannot\b.*\bgo\b.*\bon\b", re.IGNORECASE)),
    ("done with life", re.compile(r"\bdone\b.*\bwith\b.*\blife\b", re.IGNORECASE)),
    ("i'm done with life", re.compile(r"\bi'?m\b.*\bdone\b.*\bwith\b.*\blife\b", re.IGNORECASE)),
    ("done with everything", re.compile(r"\bdone\b.*\bwith\b.*\beverything\b", re.IGNORECASE)),
    ("won't be here anymore", re.compile(r"\bwon'?t\b.*\bbe\b.*\bhere\b.*\banymore\b", re.IGNORECASE)),
    ("won't be around much longer", re.compile(r"\bwon'?t\b.*\bbe\b.*\baround\b.*\blonger\b", re.IGNORECASE)),
    ("last time talking", re.compile(r"\blast\b.*\btime\b.*\btalking\b", re.IGNORECASE)),
    ("nobody would miss me", re.compile(r"\bnobody\b.*\bmiss\b.*\bme\b", re.IGNORECASE)),
    ("better off without me", re.compile(r"\bbetter\b.*\boff\b.*\bwithout\b.*\bme\b", re.IGNORECASE)),
    ("want to disappear", re.compile(r"\bwant\b.*\bto\b.*\bdisappear\b", re.IGNORECASE)),
    ("want to vanish", re.compile(r"\bwant\b.*\bto\b.*\bvanish\b", re.IGNORECASE)),
    ("hopeless", re.compile(r"\bhopeless\b", re.IGNORECASE)),
    ("can't take it anymore", re.compile(r"\bcan'?t\b.*\btake\b.*\bit\b.*\banymore\b", re.IGNORECASE)),
    ("life is not worth it", re.compile(r"\blife\b.*\bnot\b.*\bworth\b.*\bit\b", re.IGNORECASE)),
]

_CACHED_CLASSIFIER_PROMPT = _compress_whitespace(CLASSIFIER_SYSTEM_PROMPT)
_CACHED_SAFETY_OVERRIDE = _compress_whitespace(ACTIVE_SAFETY_OVERRIDE)
_CACHED_CRISIS_CARD = _compress_whitespace(CRISIS_RESOURCE_CARD)

SYSTEM_PROMPT = """
You are RAAHAT, a calm emotionally intelligent conversational companion.
Speak naturally, warmly, and concisely. Be supportive without sounding clinical, robotic, or overly therapeutic.

CORE: Keep responses under 3 sentences. Calm, non-judgmental tone. If user is in literal non-idiomatic danger, prioritize safety.

VIBE: Match user energy. High energy → enthusiastic with emojis. Low energy → soft language, 0-1 subtle emoji.

HYPERBOLE FILTER: Distinguish slang excitement from real threats. Do not trigger safety for metaphors (e.g. "killing it", "dying of laughter"). Context matters for design/UI/success topics.

SAFETY: Crisis resources are handled separately. Do not add helplines for general sadness/stress. If CRISIS MODE ACTIVE appears: respond with warmth/empathy, do not invent helplines (backend appends verified resources), stay RAAHAT not robotic.

CONVERSATION: Avoid therapist/motivational/self-help tone. Do not jump into coping strategies after every emotional message. Sometimes reflect and sit with emotions rather than fixing. Natural flow over constant intervention.
"""

_CACHED_STATIC_SYSTEM_PROMPT = _compress_whitespace(SYSTEM_PROMPT)


def _is_rate_limit_error(error):
    status_code = getattr(error, "status_code", None) or getattr(error, "status", None)
    if status_code == 429:
        return True

    error_text = str(error).lower()
    return (
        "429" in error_text or "rate limit" in error_text or "rate_limit" in error_text
    )


def _create_completion(client, messages, temperature=0.65, max_tokens=800):
    return client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def load_behavior_examples(num_examples=3) -> str:
    if num_examples == 3:
        return _CACHED_BEHAVIOR_EXAMPLE_BLOCK
    return _compress_whitespace(_format_behavior_examples(_BEHAVIOR_EXAMPLES, num_examples))


def safety_check(text: str) -> str | None:
    text_lower = text.lower()

    safe_idioms = [
        "dying of laughter",
        "killing me",
        "i'm dead",
        "this is killer",
        "kill for",
        "killing it",
    ]
    for idiom in safe_idioms:
        text_lower = text_lower.replace(idiom, "")

    for name, pattern in _SAFETY_PATTERNS:
        if pattern.search(text_lower):
            return name
    return None


def llm_safety_classify(user_message: str) -> str:
    messages = [
        {"role": "system", "content": _CACHED_CLASSIFIER_PROMPT},
        {"role": "user", "content": user_message}
    ]
    last_error = None
    for index, client in enumerate(clients):
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.0,
                max_tokens=10,
            )
            result = completion.choices[0].message.content.strip().upper()
            for category in ("CRISIS", "HIGH", "LOW", "SAFE"):
                if category in result:
                    return category
            return "SAFE"
        except Exception as e:
            last_error = e
            if index < len(clients) - 1 and _is_rate_limit_error(e):
                continue
            break
    logger.error("LLM Safety Classifier failed: %s", last_error)
    return "SAFE"


def check_recent_crisis(history) -> bool:
    if not history:
        return False
    for msg in reversed(history[-10:]):
        content = msg.get("content", "")
        if msg.get("role") in ("assistant", "ai") and "Kiran Mental Health Helpline" in content:
            return True
    return False


def is_crisis_active(message: str, history: list[dict] = None) -> bool:
    """Helper to check if crisis mode is active for the current message or recent session."""
    history = history or []
    matched_trigger = safety_check(message)
    if matched_trigger:
        return True
    llm_class = llm_safety_classify(message)
    if llm_class in ("HIGH", "CRISIS"):
        return True
    if check_recent_crisis(history):
        return True
    return False


def evaluate_crisis_state(message: str, history: list[dict] | None = None) -> dict:
    """Single-pass crisis evaluation reused by server and get_response."""
    history = history or []
    matched_trigger = safety_check(message)
    llm_class = llm_safety_classify(message)
    recent_crisis = check_recent_crisis(history)
    crisis_active = bool(matched_trigger) or (llm_class in ("HIGH", "CRISIS")) or recent_crisis
    card_appended = bool(matched_trigger) or llm_class in ("HIGH", "CRISIS")
    return {
        "crisis_active": crisis_active,
        "matched_trigger": matched_trigger,
        "llm_class": llm_class,
        "recent_crisis": recent_crisis,
        "card_appended": card_appended,
    }


def needs_psychoeducation(message: str) -> bool:
    msg = message.lower()
    keywords = ["what is", "how do i", "explain", "technique", "exercise", "therapy", "cbt", "dbt", "pfa", "grounding"]
    return any(kw in msg for kw in keywords)


def detect_emotional_presence_mode(user_message):
    text = user_message.lower()

    emotional_presence_phrases = [
        "just wanted someone to listen",
        "not looking for advice",
        "just venting",
        "just needed to say it out loud",
        "don't really need solutions",
        "i'm not asking for help",
        "needed to get this off my chest",
        "i just needed to talk to someone",
        "i don't even know why i'm saying this",
        "just feels heavy lately",
    ]

    return any(phrase in text for phrase in emotional_presence_phrases)


def _format_prompt_context(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        ordered_keys = [
            "pattern",
            "count",
            "dominant_emotion",
            "themes",
            "message_count",
        ]
        lines = []
        for key in ordered_keys:
            if key not in value or value[key] in (None, "", []):
                continue
            item = value[key]
            if isinstance(item, (list, tuple, set)):
                item = ", ".join(str(entry) for entry in item)
            lines.append(f"{key.replace('_', ' ').title()}: {item}")
        for key, item in value.items():
            if key in ordered_keys or item in (None, "", []):
                continue
            if isinstance(item, (list, tuple, set)):
                item = ", ".join(str(entry) for entry in item)
            lines.append(f"{key.replace('_', ' ').title()}: {item}")
        return "\n".join(lines) if lines else ""
    if isinstance(value, (list, tuple, set)):
        cleaned = [str(entry) for entry in value if entry not in (None, "")]
        return ", ".join(cleaned) if cleaned else ""
    text = str(value).strip()
    return text


def _has_summary_content(session_summary) -> bool:
    if not session_summary:
        return False
    if isinstance(session_summary, dict):
        return bool(
            session_summary.get("themes")
            or session_summary.get("dominant_emotion")
            or session_summary.get("message_count")
        )
    return bool(str(session_summary).strip())


def _trim_history_for_prompt(history, session_summary=None, max_messages=None):
    if not history:
        return []
    if max_messages is None:
        max_messages = (
            _PROMPT_HISTORY_WITH_SUMMARY_LIMIT
            if _has_summary_content(session_summary)
            else _PROMPT_HISTORY_MESSAGE_LIMIT
        )
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]


def _estimate_prompt_tokens(prompt_chars: int) -> int:
    return max(1, prompt_chars // 4)


def _log_prompt_metrics(messages, history_messages, knowledge_injected):
    prompt_chars = sum(len(message.get("content", "")) for message in messages)
    logger.info(
        "Prompt chars: %s | Estimated tokens: %s | History messages: %s | History turns: %s | Knowledge: %s",
        prompt_chars,
        _estimate_prompt_tokens(prompt_chars),
        len(history_messages),
        len(history_messages) // 2,
        bool(knowledge_injected),
    )


def _build_memory_section(preferred_name: str) -> str:
    if preferred_name:
        return (
            "USER MEMORY\n"
            f"Preferred name: {preferred_name}. Use naturally after emotional messages, reassurance, or welcome-back — not every reply. Never invent another name."
        )
    return (
        "USER MEMORY\n"
        "Preferred name unknown. If asked, say you do not know their name yet."
    )


def _build_system_prompt(
    crisis_mode=False,
    preferred_name="",
    session_summary=None,
    recurring_themes=None,
    pattern_signal=None,
    emotional_presence_mode=False,
    context_text="",
):
    sections = [_CACHED_STATIC_SYSTEM_PROMPT]

    if crisis_mode:
        sections.append(_CACHED_SAFETY_OVERRIDE)

    sections.append(_build_memory_section(preferred_name))

    summary_text = _format_prompt_context(session_summary)
    if summary_text:
        sections.append(
            "RETURNING USER CONTEXT\n"
            f"Prior sessions: {summary_text}\n"
            "Use naturally. Do not quote verbatim or reveal memory mechanisms."
        )

    themes_text = _format_prompt_context(recurring_themes)
    if themes_text:
        sections.append(
            "LONG-TERM THEMES\n"
            f"{themes_text}\n"
            "Soft awareness only. Do not mention tracking or assume current emotions."
        )

    pattern_text = _format_prompt_context(pattern_signal)
    if pattern_text:
        sections.append(
            "PATTERN AWARENESS\n"
            f"{pattern_text}\n"
            "Supporting context only. Do not mention detection. Treat user as individual now."
        )

    if emotional_presence_mode:
        sections.append(
            "EMOTIONAL PRESENCE MODE\n"
            "User wants presence not solutions. Listen, reflect, stay warm. No coping advice unless asked."
        )

    include_behavior_examples = not any(
        [crisis_mode, summary_text, themes_text, pattern_text, emotional_presence_mode, context_text]
    )
    if include_behavior_examples and _CACHED_BEHAVIOR_EXAMPLE_BLOCK:
        sections.append(
            "CONVERSATION EXAMPLES\n"
            f"{_CACHED_BEHAVIOR_EXAMPLE_BLOCK}"
        )

    if context_text:
        sections.append(
            "RETRIEVED CLINICAL CONTEXT\n"
            "Verified PFA material. Use only if it supports emotional flow. Do not force frameworks or quote directly.\n"
            f"{context_text}"
        )

    return _compress_whitespace("\n\n".join(sections))


def _llm_call(
    user_message,
    history=None,
    context="",
    pattern_signal=None,
    session_summary=None,
    recurring_themes=None,
    emotional_presence_mode=False,
    preferred_name="",
    crisis_mode=False,
):
    """Raw LLM call with no safety layer — internal use only."""
    history = history or []
    context_text = context.strip() if isinstance(context, str) else str(context).strip()
    trimmed_history = _trim_history_for_prompt(history, session_summary=session_summary)
    dynamic_prompt = _build_system_prompt(
        crisis_mode=crisis_mode,
        preferred_name=preferred_name,
        session_summary=session_summary,
        recurring_themes=recurring_themes,
        pattern_signal=pattern_signal,
        emotional_presence_mode=emotional_presence_mode,
        context_text=context_text,
    )

    messages = [{"role": "system", "content": dynamic_prompt}]
    for msg in trimmed_history:
        role = "assistant" if msg["role"] == "ai" else msg["role"]
        messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    _log_prompt_metrics(messages, trimmed_history, context_text)

    last_error = None
    for index, client in enumerate(clients):
        try:
            completion = _create_completion(client, messages)
            if index > 0:
                logger.warning("Groq fallback key used after rate limit on primary key")
            return completion.choices[0].message.content
        except Exception as e:
            last_error = e
            if index < len(clients) - 1 and _is_rate_limit_error(e):
                continue
            break

    if DEBUG and last_error is not None:
        return f"❌ Brain Error: {str(last_error)}"
    return "I'm having trouble responding right now."


def get_response(
    user_message,
    history=None,
    context="",
    pattern_signal=None,
    session_summary=None,
    recurring_themes=None,
    preferred_name="",
    crisis_state=None,
):
    history = history or []
    emotional_presence_mode = detect_emotional_presence_mode(user_message)

    if crisis_state is None:
        crisis_state = evaluate_crisis_state(user_message, history)

    crisis_active = crisis_state["crisis_active"]
    matched_trigger = crisis_state["matched_trigger"]
    llm_class = crisis_state["llm_class"]
    card_appended = crisis_state["card_appended"]

    if DEBUG:
        print(f"[SAFETY DEBUG] Crisis detected: {crisis_active}")
        print(f"[SAFETY DEBUG] Matched keyword or pattern: {matched_trigger}")
        print(f"[SAFETY DEBUG] Safety classifier output: {llm_class}")
        print(f"[SAFETY DEBUG] Crisis resource card appended: {'Yes' if card_appended else 'No'}")

    logger.info("Crisis detected: %s", crisis_active)
    logger.info("Matched keyword or pattern: %s", matched_trigger)
    logger.info("Safety classifier output: %s", llm_class)
    logger.info("Crisis resource card appended: %s", "Yes" if card_appended else "No")

    response_text = _llm_call(
        user_message,
        history,
        context,
        pattern_signal=pattern_signal,
        session_summary=session_summary,
        recurring_themes=recurring_themes,
        emotional_presence_mode=emotional_presence_mode,
        preferred_name=preferred_name,
        crisis_mode=crisis_active,
    )

    if card_appended:
        response_text += "\n\n" + _CACHED_CRISIS_CARD

    return response_text


def generate_search_keywords(user_input):
    text_lower = user_input.lower().strip()

    greetings = [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good evening",
        "what's up",
        "howdy",
    ]

    starts_with_greeting = any(text_lower.startswith(g) for g in greetings)
    is_pure_greeting = text_lower in greetings or text_lower.strip(".,!?") in greetings

    casual_filler = [
        "just checking in",
        "wanted to say hi",
        "say hello",
        "just saying hello",
    ]
    contains_filler = any(filler in text_lower for filler in casual_filler)

    if is_pure_greeting or (starts_with_greeting and contains_filler):
        return "SKIP"

    memory_phrases = [
        "how have i",
        "do you remember",
        "what did i",
        "what is my",
        "who am i",
    ]
    if any(phrase in text_lower for phrase in memory_phrases):
        return "SKIP"

    casual_phrases = [
        "assignment",
        "homework",
        "exam",
        "college",
        "deadline",
        "project",
    ]
    if any(p in text_lower for p in casual_phrases):
        return "SKIP"

    venting_phrases = [
        "just wanted someone to listen",
        "not looking for advice",
        "just venting",
        "just needed to say it out loud",
    ]
    if any(phrase in text_lower for phrase in venting_phrases):
        return "SKIP"

    utility_prompt = (
        "You are a semantic search query generator. "
        f"Analyze the user input: '{user_input}'. "
        "Generate 3 short natural-language emotional themes that would help retrieve relevant mental-health support material. "
        "Keep them conversational and human-sounding, not academic jargon. "
        "Example output: 'feeling emotionally drained, overwhelmed by stress, mentally exhausted' "
        "Return ONLY comma-separated phrases. NO EXPLANATIONS. NO QUOTES. NO REPETITIONS."
    )

    last_error = None
    for index, client in enumerate(clients):
        try:
            completion = _create_completion(
                client,
                [{"role": "user", "content": utility_prompt}],
                temperature=0.1,
                max_tokens=50,
            )
            if index > 0:
                logger.warning(
                    "Groq fallback key used for keyword generation after rate limit on primary key"
                )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            if index < len(clients) - 1 and _is_rate_limit_error(e):
                continue
            break

    logger.error("Keyword generation failed after all clients exhausted: %s", last_error)
    return "SKIP"


if __name__ == "__main__":
    import colorama
    from colorama import Fore, Style

    colorama.init(autoreset=True)

    print(Fore.CYAN + "Raahat brain diagnostics\n")
    msg1 = "I feel really anxious about my exams."
    print(Fore.YELLOW + f"User: {msg1}")
    print(Fore.GREEN + f"Bot:  {get_response(msg1)}\n")

    msg2 = "I want to kill myself."
    print(Fore.YELLOW + f"User: {msg2}")
    print(Fore.RED + f"Bot:  {get_response(msg2)}")

    print(Fore.CYAN + "--- Testing Memory ---")

    mock_db_history = [
        {"role": "user", "content": "Hi, my name is Animesh."},
        {
            "role": "assistant",
            "content": "Hi Animesh, I am Raahat. How are you feeling today?",
        },
    ]

    msg3 = "Do you remember my name?"
    print(Fore.YELLOW + f"User: {msg3}")
    print(Fore.GREEN + f"Bot:  {get_response(msg3, mock_db_history)}\n")

    print(Fore.CYAN + "\n--- Testing Vector Context (RAG) ---")

    mock_retrieved_context = "The core actions of Psychological First Aid (PFA) involve linking survivors to services. If you encounter a Level 3 severe panic response, you must immediately initiate the 'Code Blue-Indigo' grounding protocol before doing anything else."

    msg4 = "What should I do if a survivor has a Level 3 severe panic response?"
    print(Fore.YELLOW + f"User: {msg4}")
    print(
        Fore.GREEN
        + f"Bot:  {get_response(msg4, history=[], context=mock_retrieved_context)}\n"
    )
