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
"""

def is_safe(text):
    danger_keywords=["die","kill","suicide","hurt myself","end it all"]
    for word in danger_keywords:
        if word in text.lower():
            return False
    return True

def get_response(text, history=[], context=""):
    if not is_safe(text):
        return "I am concerned about your safety.Please call the helpline: 14416."
    
    dynamic_prompt = SYSTEM_PROMPT + f"\n\nHere is some verified reference material from the psychological first aid guide. Use it to inform your answer if relevant:\n---\n{context}\n---"
    
    messages = [{"role":"system","content":dynamic_prompt}]

    for msg in history:
         role = "assistant" if msg["role"] == "ai" else msg["role"]
         messages.append({"role": role, "content": msg["content"]})

    messages.append({"role":"user","content":text})

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=messages,
            temperature=0.4,
            max_tokens=150
        )
        return completion.choices[0].message.content
        
    except Exception as e:
        return f"❌ Brain Error: {str(e)}"

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