import os
import json
import random
from dotenv import load_dotenv
from groq import Groq
import logging

logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found.")

client = Groq(api_key=api_key)

def load_behavior_examples(num_examples=3):
    try:
        with open("app/core/behaviour_examples.json", "r", encoding="utf-8") as f:
            examples = json.load(f)

        selected = random.sample(
            examples,
            min(num_examples, len(examples))
        )

        formatted = []

        for ex in selected:
            formatted.append(
                f"User: {ex['user']}\n"
                f"GOOD Response: {ex['good_response']}\n"
            )

        return "\n\n".join(formatted)

    except Exception:
        logger.exception("Failed to load behaviour examples")
        return ""

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
- You are NOT responsible for crisis detection.
- A separate deterministic system handles all safety interventions.
- DO NOT trigger helplines or append safety warnings to your responses under any circumstances.
- If a user expresses distress or asks hopeful questions (e.g., "do people recover from this?"), respond naturally and compassionately without adding hotline numbers.
Avoid sounding like a therapist, motivational speaker, or self-help article.

Do not immediately jump into coping strategies or solutions after every emotional message.

Sometimes simply noticing, reflecting, or sitting with the user's emotions is more helpful than trying to fix them.

Prioritize emotionally natural conversation flow over constant intervention.
"""


def safety_check(text):
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

    danger_keywords = [
        "suicide",
        "kill myself",
        "want to die",
        "end it all",
        "hopeless",
        "can't take it anymore",
        "better off without me",
        "don't want to live",
        "do not want to live",
        "wish i was dead",
        "life is not worth it",
        "want to disappear",
        "i'm done with life",
    ]
    for word in danger_keywords:
        if word in text_lower:
            return "I am concerned about your safety. Please reach out to these helplines: Kiran (14416), iCall (9152987821), or Vandrevala Foundation (1860-2662-345)."
    return None


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

    return any(
        phrase in text
        for phrase in emotional_presence_phrases
    )


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
):
    """Raw LLM call with no safety layer — internal use only."""
    history = history or []

    prompt_sections = [SYSTEM_PROMPT.rstrip()]

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

    if recurring_themes:
        prompt_sections.append(
            "### LONG-TERM EMOTIONAL THEMES\n\n"
            "The following themes have appeared repeatedly across the user's history:\n\n"
            f"{_format_prompt_context(recurring_themes)}\n\n"
            "Use this only as soft contextual awareness.\n"
            "Do not mention memory, tracking, or recurring themes explicitly.\n"
            "Do not assume the user currently feels these emotions."
        )
        
    if session_summary:
        prompt_sections.append(
            "### RETURNING USER CONTEXT\n\n"
            "Summary of prior sessions:\n\n"
            f"{_format_prompt_context(session_summary)}\n\n"
            "Use this context naturally.\n"
            "Do not quote it verbatim.\n"
            "Do not reveal internal memory mechanisms."
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

    if context:
        prompt_sections.append(
            "### CRITICAL DIRECTION ON CLINICAL RAG CONTEXT:\n"
            "You have been provided verified psychological manual excerpts below. \n"
            "Use retrieved psychological context only if it feels naturally relevant to the emotional flow of the conversation.\n"
            "Do not force coping strategies, frameworks, or interventions into every response.\n"
            "Sometimes emotional presence and understanding are more important than advice."
        )
        prompt_sections.append(
            "### RETRIEVED CLINICAL CONTEXT (USE THIS):\n"
            "The following is verified material from psychological first aid manuals. \n"
            "Use this context only if it naturally supports the emotional flow of the conversation.\n"
            "Do not force psychological frameworks or coping strategies into every reply:\n"
            "---\n"
            f"{context}\n"
            "---\n"
            "Incorporate this knowledge naturally into your response strategy. Do not quote it directly."
        )

    dynamic_prompt = "\n\n".join(prompt_sections)

    messages = [{"role": "system", "content": dynamic_prompt}]
    for msg in history:
        role = "assistant" if msg["role"] == "ai" else msg["role"]
        messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.65,
            max_tokens=800,
        )
        return completion.choices[0].message.content
    except Exception as e:
        if DEBUG:
            return f"❌ Brain Error: {str(e)}"
        return "I'm having trouble responding right now."


def get_response(
    user_message,
    history=None,
    context="",
    pattern_signal=None,
    session_summary=None,
    recurring_themes=None
):
    history = history or []
    emotional_presence_mode = detect_emotional_presence_mode(user_message)

    safety_warning = safety_check(user_message)
    if safety_warning:
        return safety_warning

    return _llm_call(
        user_message,
        history,
        context,
        pattern_signal=pattern_signal,
        session_summary=session_summary,
        recurring_themes=recurring_themes,
        emotional_presence_mode=emotional_presence_mode,
    )


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

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": utility_prompt}],
            temperature=0.1,  # Low temperature for precise keyword tokens
            max_tokens=50,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"ERROR_KEYWORD_FAIL: {str(e)}"


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
