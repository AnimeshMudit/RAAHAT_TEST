import sqlite3
import hashlib
from datetime import datetime, timezone
import os
import logging
import json

logger = logging.getLogger(__name__)

# Locate the database file at the root of the workspace
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../raahat_audit.db"))

def init_audit_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create audit_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                content_hash TEXT NOT NULL
            )
        """)
        
        # Create phq9_scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS phq9_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                score INTEGER NOT NULL
            )
        """)
        
        # Add responses column to phq9_scores if it doesn't exist
        try:
            cursor.execute("ALTER TABLE phq9_scores ADD COLUMN responses TEXT")
        except sqlite3.OperationalError:
            # Column already exists
            pass
            
        # Migrate existing rows where responses is NULL
        try:
            cursor.execute("UPDATE phq9_scores SET responses = '[0,0,0,0,0,0,0,0,0]' WHERE responses IS NULL")
        except Exception as migration_err:
            logger.warning("Failed to migrate existing rows: %s", str(migration_err))
            
        conn.commit()
        conn.close()
    except Exception as e:
        logger.exception("Failed to initialize audit database")

# Ensure table creation on load
init_audit_db()

def log_audit_event(user_id: str, event_type: str, risk_level: str, content: str):
    """
    Log an event to the audit trail.
    Hashes the content with SHA256 before storage to avoid storing raw sensitive text.
    """
    if not user_id:
        user_id = "anonymous"
    
    # Calculate SHA256 hash of the content
    content_bytes = (content or "").encode("utf-8")
    content_hash = hashlib.sha256(content_bytes).hexdigest()
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (timestamp, user_id, event_type, risk_level, content_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (timestamp, str(user_id), event_type, risk_level, content_hash))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.exception("Failed to write to audit log database")

def save_phq9_score(user_id: str, score: int, responses: list[int]) -> int:
    """
    Saves a PHQ-9 assessment score to the database.
    """
    if not user_id:
        user_id = "anonymous"
        
    timestamp = datetime.now(timezone.utc).isoformat()
    responses_str = json.dumps(responses)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO phq9_scores (timestamp, user_id, score, responses)
            VALUES (?, ?, ?, ?)
        """, (timestamp, str(user_id), score, responses_str))
        inserted_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return inserted_id
    except Exception as e:
        logger.exception("Failed to save PHQ-9 score to database")
        raise e

def get_severity(score: int) -> str:
    """
    Returns the severity category for a given PHQ-9 score.
    """
    if score <= 4:
        return "Minimal"
    elif score <= 9:
        return "Mild"
    elif score <= 14:
        return "Moderate"
    elif score <= 19:
        return "Moderately Severe"
    else:
        return "Severe"

def get_phq9_entry(assessment_id: int) -> dict | None:
    """
    Retrieves a single PHQ-9 assessment by its ID.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, score, responses
            FROM phq9_scores
            WHERE id = ?
        """, (assessment_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            row_id, timestamp, score, responses_str = row
            q9_flag = False
            if responses_str:
                try:
                    responses = json.loads(responses_str)
                    if isinstance(responses, list) and len(responses) == 9:
                        q9_flag = responses[8] > 0
                except Exception:
                    pass
            severity = get_severity(score)
            return {
                "id": row_id,
                "timestamp": timestamp,
                "score": score,
                "severity": severity,
                "q9_flag": q9_flag
            }
    except Exception as e:
        logger.exception("Failed to get PHQ-9 entry")
    return None

def get_phq9_history(user_id: str, limit: int = 20) -> list[dict]:
    """
    Returns the most-recent-first list of PHQ-9 assessments for a user.
    """
    if not user_id:
        return []
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, score, responses
            FROM phq9_scores
            WHERE user_id = ?
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
        """, (str(user_id), limit))
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            row_id, timestamp, score, responses_str = row
            q9_flag = False
            if responses_str:
                try:
                    responses = json.loads(responses_str)
                    if isinstance(responses, list) and len(responses) == 9:
                        q9_flag = responses[8] > 0
                except Exception:
                    pass
            severity = get_severity(score)
            history.append({
                "id": row_id,
                "timestamp": timestamp,
                "score": score,
                "severity": severity,
                "q9_flag": q9_flag
            })
        return history
    except Exception as e:
        logger.exception("Failed to get PHQ-9 history from database")
        return []
