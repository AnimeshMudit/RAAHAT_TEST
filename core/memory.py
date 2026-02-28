import os
from dotenv import load_dotenv # this is to load the .env file
from supabase import create_client #this helps in executing supabase commands

load_dotenv()       #this loads the .env file 
url = os.getenv("SUPABASE_URL")     #gets the url by looking at system active memory
key = os.getenv("SUPABASE_KEY")     #gets the key

supabase = create_client(url,key)   #i guess it establish the connection between database and my code 


def save_message(user_id,role,content):
    d = {
        "user_id" : user_id,
        "role" : role,
        "content" : content
    }
    supabase.table("chats").insert(d).execute()

def fetch_history(user_id):
    response = supabase.table("chats").select("*").eq("user_id",user_id).execute()
    return response.data

if __name__ == "__main__":
    print("⏳ Sending data to the cloud...")
    
    # 1. Test saving a message
    save_message("Anshuman", "user", "Hello Raahat, this is my first cloud memory!")
    
    # 2. Test reading it back
    history = fetch_history("Anshuman")
    
    print("\n📜 Reading from Memory:")
    for row in history:
        print(f"[{row['created_at'][:10]}] {row['role']}: {row['content']}")