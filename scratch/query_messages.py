import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from app.core.memory import supabase
from app.core import brain

try:
    response = supabase.table("messages").select("role,content,created_at").order("created_at", desc=True).limit(10).execute()
    print("Messages fetched successfully:")
    for msg in reversed(response.data):
        print(f"[{msg['created_at']}] {msg['role']}: {msg['content']}")
        if msg['role'] == 'user':
            eval_state = brain.evaluate_crisis_state(msg['content'])
            print(f"  -> Evaluate Crisis State: {eval_state}")
except Exception as e:
    print("Error fetching messages:", e)

