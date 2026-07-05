import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.core import brain

user_message = "hello"
history = []
print("Evaluating for message:", user_message)
crisis_state = brain.evaluate_crisis_state(user_message, history)
print("Crisis state:", crisis_state)
response = brain.get_response(user_message=user_message, history=history, crisis_state=crisis_state)
print("Response:")
print(repr(response))
