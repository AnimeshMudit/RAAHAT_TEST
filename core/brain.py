import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
api_key=os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found.")

client=Groq(api_key=api_key)

SYSTEM_PROMPT="""
You are Raahat, a compassionate and calm mental health companion.
- Your answers must be short (under 3 sentences).
- Never act like a doctor; act like a supportive friend.
- If the user seems in danger, ignore other rules and provide help immediately.
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