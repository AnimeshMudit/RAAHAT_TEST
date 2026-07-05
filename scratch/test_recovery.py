import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import brain

test_phrase = "i am alright now i contacted them and I am all cheared up"

print("Is recovery detected?", brain.detect_recovery(test_phrase))
print("Safety check result:", brain.safety_check(test_phrase))
print("Should run safety classifier?", brain.should_run_safety_classifier(test_phrase))
print("LLM safety classify:", brain.llm_safety_classify(test_phrase))
print("Evaluate crisis state:", brain.evaluate_crisis_state(test_phrase))
