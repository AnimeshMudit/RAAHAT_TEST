import bcrypt

# Fix compatibility between passlib and bcrypt 4.x+
if not hasattr(bcrypt, "__about__"):
    class DummyAbout:
        __version__ = bcrypt.__version__
    bcrypt.__about__ = DummyAbout()

# Fix passlib wrap bug checking compatibility by truncating long password bytes
orig_hashpw = bcrypt.hashpw
def patched_hashpw(password, salt):
    if isinstance(password, bytes) and len(password) > 72:
        password = password[:72]
    return orig_hashpw(password, salt)
bcrypt.hashpw = patched_hashpw

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
    except (UnknownHashError, TypeError, ValueError):
        return False

# --- ADD THIS FUNCTION TO FIX THE IMPORT ERROR ---
def verify_email_real(email: str) -> tuple[bool, str]:
    """
    Validates the email format and ensures it meets 
    Raahat's security standards.
    """
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    normalized_email = email.strip().lower() if email else ""
    if not normalized_email:
        return False, normalized_email
    return re.match(email_regex, normalized_email) is not None, normalized_email