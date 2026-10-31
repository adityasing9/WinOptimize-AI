"""
WinOptimize AI - SQLite Database Storage Manager
Handles persistent storage for scan history, user preferences, and backup/rollback snapshots.
"""

from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional


class DatabaseManager:
    """
    Manages local SQLite storage for WinOptimize AI.
    Zero cloud dependencies, strictly local and private.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            self.db_path = str(base_dir / "winop.db")
        else:
            self.db_path = db_path

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes database schema with required tables and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Scan history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    used_memory_mb REAL,
                    total_memory_mb REAL,
                    cpu_percent REAL,
                    proc_count INTEGER,
                    startup_count INTEGER,
                    task_count INTEGER,
                    service_count INTEGER,
                    candidates_count INTEGER
                )
            """)

            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    target_identifier TEXT PRIMARY KEY,
                    component_name TEXT,
                    policy TEXT NOT NULL, -- 'keep_enabled', 'optimize_when_safe', 'ignore', 'ask_always'
                    updated_at TEXT NOT NULL
                )
            """)

            # Optimization sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimization_sessions (
                    session_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    user_authorized INTEGER NOT NULL,
                    total_actions INTEGER NOT NULL,
                    status TEXT NOT NULL -- 'completed', 'partial_failure', 'rolled_back'
                )
            """)

            # Backup snapshots table for atomic rollbacks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backup_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    component_name TEXT NOT NULL,
                    target_type TEXT NOT NULL, -- 'registry_startup', 'scheduled_task', 'service'
                    target_identifier TEXT NOT NULL,
                    original_state_json TEXT NOT NULL,
                    target_state_json TEXT NOT NULL,
                    status TEXT NOT NULL, -- 'applied', 'verified', 'reverted', 'failed'
                    applied_at TEXT,
                    verified_at TEXT,
                    reverted_at TEXT,
                    FOREIGN KEY(session_id) REFERENCES optimization_sessions(session_id)
                )
            """)

            conn.commit()

    # -------------------------------------------------------------------------
    # Scan History Methods
    # -------------------------------------------------------------------------
    def record_scan(
        self,
        used_memory_mb: float,
        total_memory_mb: float,
        cpu_percent: float,
        proc_count: int,
        startup_count: int,
        task_count: int,
        service_count: int,
        candidates_count: int,
    ) -> int:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO scan_history (
                    timestamp, used_memory_mb, total_memory_mb, cpu_percent,
                    proc_count, startup_count, task_count, service_count, candidates_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now_iso, used_memory_mb, total_memory_mb, cpu_percent,
                    proc_count, startup_count, task_count, service_count, candidates_count
                )
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_scans(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM scan_history ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # User Preferences Methods
    # -------------------------------------------------------------------------
    def set_user_preference(self, target_identifier: str, component_name: str, policy: str) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_preferences (target_identifier, component_name, policy, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(target_identifier) DO UPDATE SET
                    component_name=excluded.component_name,
                    policy=excluded.policy,
                    updated_at=excluded.updated_at
                """,
                (target_identifier, component_name, policy, now_iso)
            )
            conn.commit()

    def get_user_preference(self, target_identifier: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT policy FROM user_preferences WHERE target_identifier = ?",
                (target_identifier,)
            )
            row = cursor.fetchone()
            return row["policy"] if row else None

    def get_all_preferences(self) -> Dict[str, str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT target_identifier, policy FROM user_preferences")
            return {row["target_identifier"]: row["policy"] for row in cursor.fetchall()}

    # -------------------------------------------------------------------------
    # Optimization & Backup Snapshot Methods
    # -------------------------------------------------------------------------
    def create_optimization_session(self, session_id: str, total_actions: int, user_authorized: bool = True) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO optimization_sessions (session_id, timestamp, user_authorized, total_actions, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, now_iso, 1 if user_authorized else 0, total_actions, "in_progress")
            )
            conn.commit()

    def update_session_status(self, session_id: str, status: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE optimization_sessions SET status = ? WHERE session_id = ?",
                (status, session_id)
            )
            conn.commit()

    def record_backup_snapshot(
        self,
        snapshot_id: str,
        session_id: str,
        component_name: str,
        target_type: str,
        target_identifier: str,
        original_state: Dict[str, Any],
        target_state: Dict[str, Any],
        status: str = "applied"
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        orig_json = json.dumps(original_state)
        target_json = json.dumps(target_state)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO backup_snapshots (
                    snapshot_id, session_id, component_name, target_type, target_identifier,
                    original_state_json, target_state_json, status, applied_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id, session_id, component_name, target_type, target_identifier,
                    orig_json, target_json, status, now_iso
                )
            )
            conn.commit()

    def update_snapshot_status(self, snapshot_id: str, status: str) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        timestamp_col = "verified_at" if status == "verified" else "reverted_at"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE backup_snapshots SET status = ?, {timestamp_col} = ? WHERE snapshot_id = ?",
                (status, now_iso, snapshot_id)
            )
            conn.commit()

    def get_snapshots_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM backup_snapshots WHERE session_id = ? ORDER BY applied_at ASC",
                (session_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_all_snapshots(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM backup_snapshots ORDER BY applied_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
