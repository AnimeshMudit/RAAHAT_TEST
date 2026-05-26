import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
api_key=os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found.")

client=Groq(api_key=api_key)

SYSTEM_PROMPT="""
You are RAAHAT, a compassionate "Safe House" companion and creative collaborator. 
You are a trusted keeper of secrets, not a doctor. Act like a supportive, grounded friend.

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

### EMERGENCY SAFETY FEATURE:
- You must distinguish between "Idioms of Joy" and "Actual Distress."
- The following phrases are ALWAYS considered SAFE when the user is laughing or joking:
    * "I am dying of laughter"
    * "You're killing me"
    * "I'm dead" (in response to a joke)
    * "This is killer"
- If the user just said "hahaha" or asked for a joke, IGNORE the words 'dying' or 'killing' as safety threats. 
- Only provide the helplines (Kiran, iCall, Vandrevala) if the user expresses hopelessness, self-harm intent, or genuine dark thoughts.
-If in any case you get an idea that the user is going to take some wrong step or going to harm themselves, respond with:
    *Some emotional connect with the user based on his text and then follow up with this line:
        **I am concerned about your safety. Please reach out to these helplines: Kiran (14416), iCall (9152987821), or Vandrevala Foundation (1860-2662-345).**
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
        "killing it"
    ]
    for idiom in safe_idioms:
        text_lower = text_lower.replace(idiom, "")

    danger_keywords=["suicide", "kill myself", "want to die", "end it all", "hopeless", "can't take it anymore", "better off without me"]
    for word in danger_keywords:
        if word in text_lower:
            return "I am concerned about your safety. Please reach out to these helplines: Kiran (14416), iCall (9152987821), or Vandrevala Foundation (1860-2662-345)."
    return None

def _llm_call(text, history=[], context=""):
    """Raw LLM call with no safety layer — internal use only."""
    dynamic_prompt = SYSTEM_PROMPT + f"""

### RETRIEVED CLINICAL CONTEXT (USE THIS):
The following is verified material from psychological first aid manuals. 
You MUST reference or draw from this when forming your response — do not ignore it:
---
{context}
---
Incorporate this knowledge naturally. Do not quote it directly."""
    messages = [{"role": "system", "content": dynamic_prompt}]
    for msg in history:
        role = "assistant" if msg["role"] == "ai" else msg["role"]
        messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": text})
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4,
            max_tokens=800
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"❌ Brain Error: {str(e)}"

def get_response(text, history=[], context=""):
    safety_warning = safety_check(text)
    if safety_warning:
        return safety_warning
    
    response_text = _llm_call(text, history, context)
    
    if len(history) <= 1 and not response_text.startswith("❌"):
        response_text = "⚠️ RAAHAT is not a substitute for professional mental health care.\n\n" + response_text
        
    return response_text

def generate_search_keywords(user_input):
    prompt = (
        f"The user said: '{user_input}'. "
        "Extract the core clinical or psychological concept as a 2-3 word phrase. "
        "Then add 2 synonym phrases. "
        "Example output: 'emotional exhaustion, mental fatigue, burnout' "
        "Return ONLY the phrases separated by commas. No explanation."
    )
    return _llm_call(prompt)
if __name__=="__main__":
    import colorama
    from colorama import Fore,Style
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
        {"role": "assistant", "content": "Hi Animesh, I am Raahat. How are you feeling today?"}
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
    print(Fore.GREEN + f"Bot:  {get_response(msg4, history=[], context=mock_retrieved_context)}\n")