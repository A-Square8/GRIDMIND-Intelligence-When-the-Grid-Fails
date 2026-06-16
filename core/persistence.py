import sqlite3
import json
import time
import uuid
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class GridMindDB:
    def __init__(self, db_path="data/gridmind.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self._init_tables()
            self.available = True
            logger.info("Database initialized at %s", self.db_path)
        except Exception as e:
            logger.warning("Database initialization failed: %s", e)
            self.conn = None
            self.available = False

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                metadata_json TEXT,
                timestamp REAL,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            );
            CREATE TABLE IF NOT EXISTS cache (
                query_hash TEXT PRIMARY KEY,
                query_embedding BLOB,
                response TEXT,
                created_at REAL,
                hit_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS system_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT,
                details TEXT,
                timestamp REAL
            );
        """)
        self.conn.commit()

    def create_conversation(self, title=None):
        if not self.available:
            return None
        cid = str(uuid.uuid4())[:8]
        self.conn.execute(
            "INSERT INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
            (cid, title, time.time())
        )
        self.conn.commit()
        return cid

    def clear_all_history(self):
        if not self.available:
            return
        self.conn.execute("DELETE FROM messages")
        self.conn.execute("DELETE FROM conversations")
        self.conn.execute("DELETE FROM cache")
        self.conn.commit()

    def clear_cache(self):
        if not self.available:
            return
        self.conn.execute("DELETE FROM cache")
        self.conn.commit()

    def save_message(self, conversation_id, role, content, metadata=None):
        if not self.available:
            return
        mid = str(uuid.uuid4())[:12]
        self.conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, metadata_json, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (mid, conversation_id, role, content, json.dumps(metadata or {}), time.time())
        )
        self.conn.commit()

    def get_conversation_history(self, conversation_id, limit=10):
        if not self.available:
            return []
        rows = self.conn.execute(
            "SELECT role, content, metadata_json, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp DESC LIMIT ?",
            (conversation_id, limit)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def list_conversations(self, limit=20):
        if not self.available:
            return []
        rows = self.conn.execute(
            "SELECT id, title, created_at FROM conversations ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def cache_get(self, query_hash):
        if not self.available:
            return None
        row = self.conn.execute(
            "SELECT response FROM cache WHERE query_hash = ?",
            (query_hash,)
        ).fetchone()
        if row:
            self.conn.execute(
                "UPDATE cache SET hit_count = hit_count + 1 WHERE query_hash = ?",
                (query_hash,)
            )
            self.conn.commit()
            return dict(row)["response"]
        return None

    def cache_put(self, query_hash, response, query_embedding=None):
        if not self.available:
            return
        embedding_blob = query_embedding.tobytes() if query_embedding is not None else None
        self.conn.execute(
            "INSERT OR REPLACE INTO cache (query_hash, query_embedding, response, created_at, hit_count) VALUES (?, ?, ?, ?, 0)",
            (query_hash, embedding_blob, response, time.time())
        )
        self.conn.commit()

    def get_all_cache_embeddings(self):
        if not self.available:
            return []
        rows = self.conn.execute(
            "SELECT query_hash, query_embedding, response FROM cache WHERE query_embedding IS NOT NULL"
        ).fetchall()
        results = []
        for r in rows:
            row_dict = dict(r)
            if row_dict["query_embedding"]:
                emb = np.frombuffer(row_dict["query_embedding"], dtype=np.float32).copy()
                results.append((row_dict["query_hash"], emb, row_dict["response"]))
        return results

    def log_event(self, event, details=""):
        if not self.available:
            return
        try:
            self.conn.execute(
                "INSERT INTO system_log (event, details, timestamp) VALUES (?, ?, ?)",
                (event, str(details)[:2000], time.time())
            )
            self.conn.commit()
        except Exception:
            pass

    def get_stats(self):
        if not self.available:
            return {}
        total_queries = self.conn.execute("SELECT COUNT(*) FROM messages WHERE role = 'user'").fetchone()[0]
        total_conversations = self.conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        cache_size = self.conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        total_cache_hits = self.conn.execute("SELECT COALESCE(SUM(hit_count), 0) FROM cache").fetchone()[0]
        return {
            "total_queries": total_queries,
            "total_conversations": total_conversations,
            "cache_size": cache_size,
            "total_cache_hits": total_cache_hits
        }

    def update_conversation_title(self, conversation_id, title):
        if not self.available:
            return
        self.conn.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title[:100], conversation_id)
        )
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
