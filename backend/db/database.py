"""
BugHunter — Database layer using aiosqlite.
Stores scan sessions, findings, and run history.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    config_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    pages_crawled INTEGER DEFAULT 0,
    findings_count INTEGER DEFAULT 0,
    tests_total INTEGER DEFAULT 0,
    tests_passed INTEGER DEFAULT 0,
    tests_failed INTEGER DEFAULT 0,
    wcag_score REAL DEFAULT 100.0,
    report_html_path TEXT,
    report_json_path TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    finding_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'MEDIUM',
    title TEXT NOT NULL,
    description TEXT,
    url TEXT,
    selector TEXT,
    evidence_json TEXT DEFAULT '{}',
    screenshot_path TEXT,
    reproduction_steps_json TEXT DEFAULT '[]',
    recommended_fix TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (scan_id) REFERENCES scans(id)
);

CREATE INDEX IF NOT EXISTS idx_findings_scan_id ON findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);
"""


class BugHunterDB:
    """Async SQLite database manager for BugHunter."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(_SCHEMA)
            await db.commit()
        logger.info("Database initialized: %s", self._db_path)

    async def create_scan(self, scan_id: str, url: str, config: dict[str, Any]) -> None:
        """Create a new scan record."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """INSERT INTO scans (id, url, status, config_json, started_at)
                   VALUES (?, ?, 'running', ?, ?)""",
                (scan_id, url, json.dumps(config), datetime.now(timezone.utc).isoformat()),
            )
            await db.commit()

    async def update_scan(self, scan_id: str, **fields: Any) -> None:
        """Update scan fields by id."""
        if not fields:
            return
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [scan_id]
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                f"UPDATE scans SET {set_clause} WHERE id = ?", values
            )
            await db.commit()

    async def finish_scan(
        self,
        scan_id: str,
        status: str = "completed",
        pages_crawled: int = 0,
        findings_count: int = 0,
        tests_total: int = 0,
        tests_passed: int = 0,
        tests_failed: int = 0,
        wcag_score: float = 100.0,
        report_html_path: str | None = None,
        report_json_path: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Mark a scan as finished."""
        await self.update_scan(
            scan_id,
            status=status,
            finished_at=datetime.now(timezone.utc).isoformat(),
            pages_crawled=pages_crawled,
            findings_count=findings_count,
            tests_total=tests_total,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            wcag_score=wcag_score,
            report_html_path=report_html_path,
            report_json_path=report_json_path,
            error_message=error_message,
        )

    async def add_finding(
        self,
        finding_id: str,
        scan_id: str,
        finding_type: str,
        severity: str,
        title: str,
        description: str = "",
        url: str = "",
        selector: str = "",
        evidence: dict[str, Any] | None = None,
        screenshot_path: str | None = None,
        reproduction_steps: list[str] | None = None,
        recommended_fix: str = "",
    ) -> None:
        """Add a single finding to the database."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """INSERT INTO findings
                   (id, scan_id, finding_type, severity, title, description, url, selector,
                    evidence_json, screenshot_path, reproduction_steps_json, recommended_fix, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    finding_id,
                    scan_id,
                    finding_type,
                    severity,
                    title,
                    description,
                    url,
                    selector,
                    json.dumps(evidence or {}),
                    screenshot_path,
                    json.dumps(reproduction_steps or []),
                    recommended_fix,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()

    async def get_scan(self, scan_id: str) -> dict[str, Any] | None:
        """Get scan by id."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)) as cur:
                row = await cur.fetchone()
                if row:
                    d = dict(row)
                    d["config"] = json.loads(d.pop("config_json", "{}"))
                    return d
                return None

    async def list_scans(self, limit: int = 50) -> list[dict[str, Any]]:
        """List most recent scans."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM scans ORDER BY started_at DESC LIMIT ?", (limit,)
            ) as cur:
                rows = await cur.fetchall()
                result = []
                for row in rows:
                    d = dict(row)
                    d["config"] = json.loads(d.pop("config_json", "{}"))
                    result.append(d)
                return result

    async def get_findings(self, scan_id: str) -> list[dict[str, Any]]:
        """Get all findings for a scan."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM findings WHERE scan_id = ? ORDER BY severity, created_at",
                (scan_id,),
            ) as cur:
                rows = await cur.fetchall()
                result = []
                for row in rows:
                    d = dict(row)
                    d["evidence"] = json.loads(d.pop("evidence_json", "{}"))
                    d["reproduction_steps"] = json.loads(d.pop("reproduction_steps_json", "[]"))
                    result.append(d)
                return result
