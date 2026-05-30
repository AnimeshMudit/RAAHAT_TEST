import os
import requests
from dotenv import load_dotenv

def check_tokens():
    load_dotenv()
    
    print("Fetching token usage from Groq API...\n")
    
    for key_name in ['GROQ_API_KEY', 'FALLBACK_KEY']:
        key = os.getenv(key_name)
        if not key:
            print(f"--- {key_name} --- (Not found in .env)\n")
            continue
            
        print(f"--- {key_name} ---")
        try:
            # Make a minimal request to get the rate limit headers
            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={'Authorization': f'Bearer {key}'},
                json={'model': 'llama-3.3-70b-versatile', 'messages': [{'role': 'user', 'content': 'hi'}]}
            )
            
            if response.status_code == 200:
                headers = response.headers
                limit = headers.get("x-ratelimit-limit-tokens", "Unknown")
                remaining = headers.get("x-ratelimit-remaining-tokens", "Unknown")
                
                # Check for rate-limit-reset to see when it refreshes
                reset = headers.get("x-ratelimit-reset-tokens", "Unknown")
                
                print(f"Tokens Limit:     {limit}")
                print(f"Tokens Remaining: {remaining}")
                print(f"Tokens Reset In:  {reset}\n")
            else:
                error_msg = response.json().get('error', {}).get('message', 'Unknown Error')
                print(f"API Error: {error_msg}\n")
                
        except Exception as e:
            print(f"Request failed: {e}\n")

if __name__ == "__main__":
    check_tokens()