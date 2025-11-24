# Database handler for conversation persistence

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    """Handles SQLite database operations for conversation storage"""
    
    def __init__(self, db_path: str = "study_buddy.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                course_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                response_tier INTEGER DEFAULT 0,
                citations TEXT,
                timestamp TEXT NOT NULL,
                token_count INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES conversations(session_id)
            )
        """)
        
        # Learning metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_metrics (
                session_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                mastery_signal TEXT DEFAULT 'novice',
                last_assessed TEXT NOT NULL,
                misconceptions TEXT,
                FOREIGN KEY (session_id) REFERENCES conversations(session_id)
            )
        """)
        
        # Course materials table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS course_materials (
                material_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES conversations(session_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_conversation(self, session_id: str, user_id: str = "default_user", 
                          course_id: Optional[str] = None) -> str:
        """Create a new conversation session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO conversations (session_id, user_id, course_id, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, course_id, now, now, json.dumps({})))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str, 
                   response_tier: int = 0, citations: List[Dict] = None) -> str:
        """Add a message to conversation history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Ensure conversation exists
        cursor.execute("SELECT session_id FROM conversations WHERE session_id = ?", 
                      (session_id,))
        if not cursor.fetchone():
            self.create_conversation(session_id)
        
        # Insert message
        cursor.execute("""
            INSERT INTO messages (message_id, session_id, role, content, response_tier, 
                                citations, timestamp, token_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id, 
            session_id, 
            role, 
            content, 
            response_tier,
            json.dumps(citations or []),
            timestamp,
            len(content.split())  # Simple word count as token estimate
        ))
        
        # Update conversation timestamp
        cursor.execute("""
            UPDATE conversations 
            SET updated_at = ? 
            WHERE session_id = ?
        """, (timestamp, session_id))
        
        conn.commit()
        conn.close()
        
        return message_id
    
    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Retrieve conversation history for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT message_id, role, content, response_tier, citations, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (session_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "message_id": row[0],
                "role": row[1],
                "content": row[2],
                "tier": row[3],
                "citations": json.loads(row[4]) if row[4] else [],
                "timestamp": row[5]
            })
        
        conn.close()
        return messages
    
    def save_course_material(self, session_id: str, file_name: str, 
                           content: str, summary: Optional[str] = None) -> str:
        """Save uploaded course material"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        material_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO course_materials (material_id, session_id, file_name, 
                                         content, summary, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (material_id, session_id, file_name, content, summary, timestamp))
        
        conn.commit()
        conn.close()
        
        return material_id
    
    def get_course_materials(self, session_id: str) -> List[Dict]:
        """Retrieve course materials for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT material_id, file_name, content, summary, uploaded_at
            FROM course_materials
            WHERE session_id = ?
            ORDER BY uploaded_at DESC
        """, (session_id,))
        
        materials = []
        for row in cursor.fetchall():
            materials.append({
                "material_id": row[0],
                "file_name": row[1],
                "content": row[2],
                "summary": row[3],
                "uploaded_at": row[4]
            })
        
        conn.close()
        return materials
    
    def update_learning_metrics(self, session_id: str, topic: str, 
                               mastery_signal: str, misconceptions: List[str] = None):
        """Update or insert learning metrics for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO learning_metrics 
            (session_id, topic, mastery_signal, last_assessed, misconceptions)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id, 
            topic, 
            mastery_signal, 
            timestamp,
            json.dumps(misconceptions or [])
        ))
        
        conn.commit()
        conn.close()
    
    def get_learning_metrics(self, session_id: str) -> Optional[Dict]:
        """Retrieve learning metrics for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT topic, mastery_signal, last_assessed, misconceptions
            FROM learning_metrics
            WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "topic": row[0],
                "mastery_signal": row[1],
                "last_assessed": row[2],
                "misconceptions": json.loads(row[3]) if row[3] else []
            }
        return None
    
    def export_session(self, session_id: str) -> Dict:
        """Export entire session data for download"""
        conversation_history = self.get_conversation_history(session_id)
        course_materials = self.get_course_materials(session_id)
        learning_metrics = self.get_learning_metrics(session_id)
        
        return {
            "session_id": session_id,
            "exported_at": datetime.now().isoformat(),
            "conversation_history": conversation_history,
            "course_materials": course_materials,
            "learning_metrics": learning_metrics
        }
