import sys
import numpy as np
from sentence_transformers import SentenceTransformer

# Reconfigure stdout to use UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Load model
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Reference phrases representing crisis / suicide / self-harm
CRISIS_REFERENCE_PHRASES = [
    # English
    "I want to kill myself",
    "I want to end my life",
    "I want to die",
    "I should just die",
    "There is no reason to live",
    "I want to commit suicide",
    "I am thinking of suicide",
    "I want to disappear forever",
    "I'm planning to take my life",
    "I'm standing on the edge, want to jump",
    "I want to jump off a bridge and end it all",
    "I want to end everything",
    
    # Hindi (Devanagari)
    "मैं मरना चाहता हूँ",
    "जीने का अब कोई मन नहीं है",
    "मैं अपनी जान दे दूंगा",
    "अब सब खत्म करना चाहता हूँ",
    "मैं खुदकुशी करने के बारे में सोच रहा हूँ",
    "मैं जीना नहीं चाहता",
    "आत्महत्या करने का मन कर रहा है",
    
    # Hinglish
    "Mera marne ka mann kar raha hai",
    "sab khatam karna hai ab mujhe",
    "khud ko maarne ki soch raha hoon",
    "apni jaan de dunga mai",
    "zindagi khatam ho gayi hai mar jana chahta hoon",
    "sucide karne ka mann kar raha hai",
    "jeena nahi hai ab",
]

# Embed references
ref_embeddings = model.encode(CRISIS_REFERENCE_PHRASES, convert_to_numpy=True, normalize_embeddings=True)

test_cases = [
    # Crisis cases (various languages/transliterations)
    ("I want to kill myself", True),
    ("I want to disappear forever", True),
    ("जीने का अब कोई मन नहीं है", True),
    ("मैं मरना चाहता हूँ", True),
    ("Mera marne ka mann kar raha hai", True),
    ("sab khatam karna hai ab mujhe", True),
    ("मैं जीना नहीं चाहता", True),  # Hindi
    ("I don't want to live", True),  # English
    ("enakku saaga thonuthu", True),  # Tamil transliterated: I feel like dying
    ("ami morar kotha bhabchi", True),  # Bengali transliterated: I am thinking of dying
    ("mala atmahatya karavishi vatate", True),  # Marathi transliterated: I feel like committing suicide
    ("naaku chaavali ani undi", True),  # Telugu transliterated: I want to die
    ("nannu naane champukovali ani undi", True),  # Kannada transliterated: I want to kill myself
    
    # Benign cases
    ("Hello, how are you today?", False),
    ("We are absolutely killing it in the project!", False),
    ("I am dying of laughter, this is so funny.", False),
    ("I'm feeling really stressed about my exams next week.", False),
    ("I had a very long and exhausting day at work.", False),
    ("I feel a bit lonely and just want someone to listen.", False),
    ("mujhe exam ki bohot tension ho rahi hai", False),
    ("aaj mai bohot thak gaya hoon", False),
    ("kal cricket match dekhne chalenge", False),
]

def cosine_similarity(a, b):
    return np.dot(a, b.T)

for text, is_crisis in test_cases:
    text_emb = model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
    sims = cosine_similarity(text_emb, ref_embeddings)[0]
    max_sim = float(np.max(sims))
    print(f"Text: {text:<50} | Expected: {str(is_crisis):<5} | Max Sim: {max_sim:.4f}")
