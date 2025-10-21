from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import sqlite3


BASE_DIR = Path(__file__).resolve().parents[3]
CATALOGO_DB = BASE_DIR / "data" / "catalogo.db"
CATALOGO_DB.parent.mkdir(parents=True, exist_ok=True)


class TicketsRepo:
    """
    Repositorio SQLite para tickets de soporte generados por la IA.
    """

    def _conn(self):
        conn = sqlite3.connect(str(CATALOGO_DB))
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_schema(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  question TEXT NOT NULL,
                  answer TEXT,
                  status TEXT NOT NULL DEFAULT 'open',
                  user_email TEXT,
                  provider TEXT,
                  error TEXT,
                  priority TEXT,
                  tags TEXT,
                  notes TEXT,
                  assigned_to TEXT,
                  assigned_by TEXT,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # Índices auxiliares
            c.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tickets_created ON tickets(created_at)")

    # CRUD ------------------------------------------------------
    def crear(
        self,
        question: str,
        *,
        user_email: Optional[str] = None,
        provider: Optional[str] = None,
        error: Optional[str] = None,
        priority: Optional[str] = None,
        tags: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        with self._conn() as c:
            cur = c.execute(
                """
                INSERT INTO tickets(question, user_email, provider, error, priority, tags, notes)
                VALUES(?,?,?,?,?,?,?)
                """,
                (question, user_email, provider, error, priority, tags, notes),
            )
            return int(cur.lastrowid)

    def listar(self, *, status: Optional[str] = None, limit: int = 50, page: int = 1) -> List[Dict[str, Any]]:
        offset = max(0, (int(page) - 1) * int(limit))
        with self._conn() as c:
            if status:
                rows = c.execute(
                    "SELECT * FROM tickets WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (status, int(limit), offset),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM tickets ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (int(limit), offset),
                ).fetchall()
            return [dict(r) for r in rows]

    def obtener(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM tickets WHERE id = ?", (int(ticket_id),)).fetchone()
            return dict(row) if row else None

    def asignar(self, ticket_id: int, assigned_to: str, *, assigned_by: Optional[str] = None, notes: Optional[str] = None, priority: Optional[str] = None) -> bool:
        with self._conn() as c:
            cur = c.execute(
                """
                UPDATE tickets
                   SET assigned_to = ?, assigned_by = ?, status = 'assigned',
                       notes = COALESCE(?, notes),
                       priority = COALESCE(?, priority),
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?
                """,
                (assigned_to, assigned_by, notes, priority, int(ticket_id)),
            )
            return cur.rowcount > 0

    def actualizar_estado(self, ticket_id: int, status: str, *, answer: Optional[str] = None, notes: Optional[str] = None) -> bool:
        with self._conn() as c:
            cur = c.execute(
                """
                UPDATE tickets
                   SET status = ?,
                       answer = COALESCE(?, answer),
                       notes = COALESCE(?, notes),
                       updated_at = CURRENT_TIMESTAMP
                 WHERE id = ?
                """,
                (status, answer, notes, int(ticket_id)),
            )
            return cur.rowcount > 0
