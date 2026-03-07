import os
from dotenv import load_dotenv # this is to load the .env file
from supabase import create_client #this helps in executing supabase commands
from colorama import Fore

load_dotenv()       #this loads the .env file 
url = os.getenv("SUPABASE_URL")     #gets the url by looking at system active memory
key = os.getenv("SUPABASE_KEY")     #gets the key

supabase = create_client(url,key)   #i guess it establish the connection between database and my code 



def get_user_by_email(email):
    f = supabase.table("users").select("*").eq("username",email).execute() #returns the API response object and .data converts it to list
    if len(f.data):
        return f.data[0]
    return None

def create_user(email, hashed_password):
    d = {
        "username" : email,
        "password_hash" : hashed_password
    }
    new_user = supabase.table("users").insert(d).execute()
    return new_user.data[0]["id"]


def save_message(user_id, role, content):
    d={
        "user_id" : user_id,
        "role" : role,
        "content" : content
    }
    supabase.table("messages").insert(d).execute()
    
def fetch_history(user_id):
    response = supabase.table("messages").select("*").eq("user_id",user_id).order("created_at").execute()
    return response.data


if __name__ == "__main__":
    print("⏳ Testing the Relational Database Flow...")
    
    # 1. Test Authentication (This will create you if you don't exist, or log you in if you do)
    print("\n🔐 Attempting Login...")
    test_user_id = get_or_create_user("Anshuman", "my_secure_password")
    
    if test_user_id:
        print(f"✅ Login Successful! Your UUID is: {test_user_id}")
        
        # 2. Test saving a message (Notice we pass the UUID variable, not your name!)
        print("\n💾 Saving a test message to the 'messages' table...")
        save_message(test_user_id, "user", "Testing the new two-table architecture!")
        
        # 3. Test reading it back
        print("\n📜 Reading from Memory:")
        history = fetch_history(test_user_id)
        
        for row in history:
            # We slice the timestamp so it looks pretty in the terminal
            print(f"[{row['created_at'][:19]}] {row['role']}: {row['content']}")
    else:
        print(Fore.RED + "❌ Login failed. Wrong password.")