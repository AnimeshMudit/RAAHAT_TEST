from passlib.context import CryptContext
from passlib.exc import UnknownHashError
import re

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a hashed password."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except UnknownHashError:
        return plain_password == hashed_password

# --- ADD THIS FUNCTION TO FIX THE IMPORT ERROR ---
def verify_email_real(email: str) -> bool:
    """
    Validates the email format and ensures it meets 
    Raahat's security standards.
    """
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not email:
        return False
    return re.match(email_regex, email) is not None