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

def get_response(text,history=[]):
    if not is_safe(text):
        return "⚠️ I am concerned about your safety.Please call the helpline: 14416."
    
    messages = [{"role":"system","content":SYSTEM_PROMPT}]

    for msg in history:
         messages.append({"role":msg["role"],"content":msg["content"]})

    messages.append({"role":"user","content":text})

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=messages,
            temperature=0.6,
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