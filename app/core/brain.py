import os
import json
import random
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

# Cache DEBUG config and behavior examples at module level
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

_BEHAVIOR_EXAMPLES: list = []

def _load_behavior_examples_once() -> list:
    try:
        path = os.path.join(os.path.dirname(__file__), "behaviour_examples.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("Failed to load behaviour examples")
        return []

_BEHAVIOR_EXAMPLES = _load_behavior_examples_once()

import re

ACTIVE_SAFETY_OVERRIDE = """
### ACTIVE SAFETY OVERRIDE

CRISIS MODE ACTIVE

The user may be experiencing a mental health crisis or suicidal ideation.

- Respond with warmth, calm, and empathy. Do not panic or over-react.
- Acknowledge what they said directly before anything else.
- Maintain your RAAHAT personality. Do not become robotic or clinical.
- Keep the response concise — do not overwhelm them with text.
- Do not ask multiple questions. Ask at most one gentle question.
"""

CRISIS_RESOURCE_CARD = """
**Need immediate support? approved Indian resources:**
- Kiran Mental Health Helpline: 14416 (24/7, free, multilingual)
- iCall: 9152987821 (Monday-Saturday, 10 AM-8 PM)
- Vandrevala Foundation: 1860-2662-345 or 9999-666-555 (24/7)
"""

CLASSIFIER_SYSTEM_PROMPT = """
You are a safety classification assistant.
Analyze the user message and classify it into exactly one of these categories:
- SAFE: Everyday conversations, general queries, positive topics, or very minor/ordinary stress.
- LOW: Sadness, standard relationship problems, stress, exam anxiety, fatigue, or general venting, but NO hints of self-harm or death.
- HIGH: Indirect or implied self-harm, deep hopelessness, passive suicidal ideation (e.g., "everyone would be better without me", "no reason to continue", "no point going on").
- CRISIS: Explicit active suicidal ideation, self-harm statements, active intent or plans (e.g., "I want to end my life", "I'm going to kill myself", "goodbye mate", "taking the wrong step").

Output ONLY the category name: SAFE, LOW, HIGH, or CRISIS. Do not include any other words or punctuation.
"""

# Compiled regexes for safety detection
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
    if not _BEHAVIOR_EXAMPLES:
        return ""
    selected = random.sample(_BEHAVIOR_EXAMPLES, min(num_examples, len(_BEHAVIOR_EXAMPLES)))
    return "\n\n".join(
        f"User: {ex['user']}\nGOOD Response: {ex['good_response']}"
        for ex in selected
    )


SYSTEM_PROMPT = """
You are RAAHAT, a calm emotionally intelligent conversational companion.

You speak naturally, warmly, and concisely.
You are supportive without sounding clinical, robotic, or overly therapeutic.

### 1. CORE CONSTRAINTS
- Keep responses concise (under 3 sentences).
- Use a calm, non-judgmental tone.
- If a user is in literal, non-idiomatic danger, prioritize safety and provide help immediately.

### 2. DYNAMIC VIBE-CHECK & EMOJIS
- Detect and match the user's emotional energy.
- HIGH ENERGY: If the user is excited or celebrating (e.g., "I fixed the bug!"), respond with high energy and multiple emojis (e.g., "Let's go! 🚀🔥 That's a massive win!").
- LOW ENERGY: If the user is sad or tired, use soft, steady language and 0-1 subtle emoji (e.g., "I'm right here with you. 🤍").

### 3. LINGUISTIC NUANCE (Hyperbole Filter)
- You are a sophisticated linguist. Distinguish between "slang" excitement and actual threats.
- Do NOT trigger safety warnings for metaphors or hyperboles (e.g., "catches eyes," "this is killer," "I'll kill you for being so good," "I'm dying of laughter").
- Context matters: If the user is discussing design, UI, or success, interpret "strong" words as creative excitement.

### 5. SAFETY & CRISIS DETECTION
- Under normal circumstances you are NOT responsible for appending crisis resources.
- A separate deterministic system handles crisis detection.
- Do NOT add helpline numbers to responses about general sadness, stress, or everyday struggles.
- EXCEPTION: If you receive a CRISIS MODE ACTIVE block, respond with warmth and empathy.
Do NOT generate, invent, or mention helpline numbers or crisis resources yourself.
A separate backend system will append verified regional crisis resources. In crisis mode, maintain your RAAHAT personality — do not become
  robotic or clinical.

### 6. CONVERSATIONAL MEMORY & PERSONALIZATION
- You may receive trusted system context containing stable user information such as the user's preferred name.
- Treat this information as reliable conversational memory for the current and future interactions unless explicitly updated by the system.
- If the user asks questions such as:
    - "What is my name?"
    - "Do you remember my name?"
    - "Who am I?"
    - "What do you call me?"
  answer using the stored preferred name whenever it exists.

- If no preferred name has been provided through system context, honestly state that you do not know the user's name yet instead of inventing one.

- Use the user's preferred name naturally to make conversations feel more personal and human.
- Prefer using the name after emotionally expressive messages, during reassurance, gentle validation, encouragement, congratulations, or when welcoming the user back after previous conversations.
- Avoid using the name during every exchange or inserting it into ordinary replies where it feels unnecessary.
- The name should feel like a natural part of conversation rather than a repeated stylistic habit.
- A natural frequency is approximately once every 8–12 assistant responses, or whenever the emotional context genuinely benefits from a more personal touch.

- Never claim to remember information that has not been explicitly provided through the conversation history or trusted system context.
- Never fabricate personal details or memories.
- Personalization should feel subtle, warm, and effortless rather than repetitive or artificial.

Avoid sounding like a therapist, motivational speaker, or self-help article.

Do not immediately jump into coping strategies or solutions after every emotional message.

Sometimes simply noticing, reflecting, or sitting with the user's emotions is more helpful than trying to fix them.

Prioritize emotionally natural conversation flow over constant intervention.
"""


def safety_check(text: str) -> str | None:
    text_lower = text.lower()

    # Exclude known safe idioms so they don't trigger false positives
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
        {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
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
    # Check the last 10 messages (user and assistant) for the crisis resource card text
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
            lines.append(f"- {key.replace('_', ' ').title()}: {item}")
        for key, item in value.items():
            if key in ordered_keys or item in (None, "", []):
                continue
            if isinstance(item, (list, tuple, set)):
                item = ", ".join(str(entry) for entry in item)
            lines.append(f"- {key.replace('_', ' ').title()}: {item}")
        return "\n".join(lines) if lines else str(value)
    if isinstance(value, (list, tuple, set)):
        return "\n".join(f"- {entry}" for entry in value)
    return str(value)


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

    prompt_sections = [SYSTEM_PROMPT.rstrip()]

    # 1. Safety Overrides (if active)
    if crisis_mode:
        prompt_sections.append(ACTIVE_SAFETY_OVERRIDE)

    # 2. Memory (Preferred Name)
    memory_section = ["### USER MEMORY\n"]
    if preferred_name:
        memory_section.append(
            f"The user's preferred name is: {preferred_name}\n"
            "Treat this as trusted conversational memory. "
            "Use the name naturally — after emotionally expressive messages, "
            "during reassurance, encouragement, or when welcoming them back. "
            "Do not use the name in every reply. Never invent another name."
        )
    else:
        memory_section.append(
            "The user's preferred name is not yet known. "
            "If asked what their name is, say you do not know their name yet."
        )
    prompt_sections.append("\n".join(memory_section))

    # 3. Memory Summaries & Theme Contexts
    if session_summary:
        prompt_sections.append(
            "### RETURNING USER CONTEXT\n\n"
            "Summary of prior sessions:\n\n"
            f"{_format_prompt_context(session_summary)}\n\n"
            "Use this context naturally.\n"
            "Do not quote it verbatim.\n"
            "Do not reveal internal memory mechanisms."
        )

    if recurring_themes:
        prompt_sections.append(
            "### LONG-TERM EMOTIONAL THEMES\n\n"
            "The following themes have appeared repeatedly across the user's history:\n\n"
            f"{_format_prompt_context(recurring_themes)}\n\n"
            "Use this only as soft contextual awareness.\n"
            "Do not mention memory, tracking, or recurring themes explicitly.\n"
            "Do not assume the user currently feels these emotions."
        )

    if pattern_signal:
        prompt_sections.append(
            "### PATTERN AWARENESS\n\n"
            "The user has shown recurring themes across previous conversations:\n\n"
            f"{_format_prompt_context(pattern_signal)}\n\n"
            "Use this only as supporting context.\n"
            "Do not mention that patterns were detected.\n"
            "Do not sound repetitive or deterministic.\n"
            "Treat the user as an individual in the current moment."
        )

    if emotional_presence_mode:
        prompt_sections.append(
            "### EMOTIONAL PRESENCE MODE\n\n"
            "The user is emotionally venting or seeking presence rather than solutions.\n"
            "Prioritize listening, emotional reflection, warmth, and conversational calmness.\n"
            "Avoid coping strategies, structured advice, self-help style suggestions, or problem-solving unless explicitly requested.\n"
            "Keep responses gentle, human, and emotionally present."
        )

    behavior_examples = load_behavior_examples()
    if behavior_examples:
        prompt_sections.append(
            "### Examples of emotionally natural conversational behavior:\n\n"
            f"{behavior_examples}"
        )

    # 4. RAG Context (Retrieved Clinical Context)
    if context:
        prompt_sections.append(
            "### RETRIEVED CLINICAL CONTEXT\n\n"
            "The following is verified material from psychological first aid manuals.\n"
            "Use it only if it naturally supports the emotional flow of the conversation.\n"
            "Do not force frameworks or coping strategies into every reply.\n"
            "Do not quote it directly.\n"
            "---\n"
            f"{context}\n"
            "---"
        )

    dynamic_prompt = "\n\n".join(prompt_sections)

    messages = [
        {
            "role": "system",
            "content": dynamic_prompt
        }
    ]

    for msg in history:
        role = "assistant" if msg["role"] == "ai" else msg["role"]
        messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

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
    preferred_name=""
):
    history = history or []
    emotional_presence_mode = detect_emotional_presence_mode(user_message)

    # 1. First-stage Keyword/Pattern Check
    matched_trigger = safety_check(user_message)

    # 2. Second-stage LLM Safety Classifier
    llm_class = llm_safety_classify(user_message)

    # 3. Check Session Memory
    recent_crisis = check_recent_crisis(history)

    # Determine if crisis is active
    crisis_active = bool(matched_trigger) or (llm_class in ("HIGH", "CRISIS")) or recent_crisis

    card_appended = "Yes" if (bool(matched_trigger) or llm_class in ("HIGH", "CRISIS")) else "No"

    # 4. Safety Debug Logging
    if DEBUG:
        print(f"[SAFETY DEBUG] Crisis detected: {crisis_active}")
        print(f"[SAFETY DEBUG] Matched keyword or pattern: {matched_trigger}")
        print(f"[SAFETY DEBUG] Safety classifier output: {llm_class}")
        print(f"[SAFETY DEBUG] Crisis resource card appended: {card_appended}")

    logger.info("Crisis detected: %s", crisis_active)
    logger.info("Matched keyword or pattern: %s", matched_trigger)
    logger.info("Safety classifier output: %s", llm_class)
    logger.info("Crisis resource card appended: %s", card_appended)

    # Call the raw LLM
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

    # If this message is classified as HIGH/CRISIS, append the card
    if bool(matched_trigger) or (llm_class in ("HIGH", "CRISIS")):
        response_text += "\n\n" + CRISIS_RESOURCE_CARD

    return response_text


def generate_search_keywords(user_input):
    text_lower = user_input.lower().strip()

    # Core greeting structural tokens
    greetings = [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good evening",
        "what's up",
        "howdy",
    ]

    # FIX: Check if the text *starts with* a greeting, or matches single word variations
    starts_with_greeting = any(text_lower.startswith(g) for g in greetings)
    is_pure_greeting = text_lower in greetings or text_lower.strip(".,!?") in greetings

    # Catch casual checking-in filler phrases that carry no clinical value
    casual_filler = [
        "just checking in",
        "wanted to say hi",
        "say hello",
        "just saying hello",
    ]
    contains_filler = any(filler in text_lower for filler in casual_filler)

    # Tight conditional trigger for the SKIP path
    if is_pure_greeting or (starts_with_greeting and contains_filler):
        return "SKIP"

    # Keep your existing memory-recall array block...
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

    # FIX: Run a clean utility call instead of overloading the emotional companion prompt
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

    # Test 2: Safety Check
    msg2 = "I want to kill myself."
    print(Fore.YELLOW + f"User: {msg2}")
    print(Fore.RED + f"Bot:  {get_response(msg2)}")

    # Test 3: The Memory Test
    print(Fore.CYAN + "--- Testing Memory ---")

    # We pretend Anshuman's database sent us this history
    mock_db_history = [
        {"role": "user", "content": "Hi, my name is Animesh."},
        {
            "role": "assistant",
            "content": "Hi Animesh, I am Raahat. How are you feeling today?",
        },
    ]

    msg3 = "Do you remember my name?"
    print(Fore.YELLOW + f"User: {msg3}")

    # We pass BOTH the new message AND the history
    print(Fore.GREEN + f"Bot:  {get_response(msg3, mock_db_history)}\n")

    # Test 4: The RAG / Context Verification Test
    print(Fore.CYAN + "\n--- Testing Vector Context (RAG) ---")

    # We pretend knowledge.py fetched this highly specific paragraph from your PDF.
    # (I added a fake "Code Blue-Indigo" protocol to prove it reads THIS text, not the internet).
    mock_retrieved_context = "The core actions of Psychological First Aid (PFA) involve linking survivors to services. If you encounter a Level 3 severe panic response, you must immediately initiate the 'Code Blue-Indigo' grounding protocol before doing anything else."

    msg4 = "What should I do if a survivor has a Level 3 severe panic response?"
    print(Fore.YELLOW + f"User: {msg4}")

    # We pass the message, empty history, and our mock CONTEXT
    print(
        Fore.GREEN
        + f"Bot:  {get_response(msg4, history=[], context=mock_retrieved_context)}\n"
    )
