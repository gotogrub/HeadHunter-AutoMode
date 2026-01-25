"""
HeadHunter Destroyer - Database Module
SQLite database for storing applications, companies, and statistics.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from config import USER_DATA_DIR


class Database:
    """SQLite database manager for HH Destroyer."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            os.makedirs(USER_DATA_DIR, exist_ok=True)
            db_path = os.path.join(USER_DATA_DIR, "hh_destroyer.db")

        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access

    def _create_tables(self):
        """Create database tables if not exist."""
        cursor = self.conn.cursor()

        # Applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vacancy_id TEXT UNIQUE,
                title TEXT,
                employer TEXT,
                employer_id TEXT,
                salary_from INTEGER,
                salary_to INTEGER,
                salary_currency TEXT,
                url TEXT,
                status TEXT DEFAULT 'applied',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                viewed_at TIMESTAMP,
                response_at TIMESTAMP,
                notes TEXT
            )
        """)

        # Companies table (for blacklist/whitelist)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                hh_id TEXT,
                status TEXT DEFAULT 'normal',
                applications_count INTEGER DEFAULT 0,
                responses_count INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Resumes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hh_id TEXT UNIQUE,
                title TEXT,
                status TEXT,
                views_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Statistics table (daily aggregates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                applications_count INTEGER DEFAULT 0,
                views_count INTEGER DEFAULT 0,
                invitations_count INTEGER DEFAULT 0,
                rejections_count INTEGER DEFAULT 0
            )
        """)

        # Blacklist words
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklist_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.commit()

    # ============ Applications ============

    def add_application(self, vacancy_id: str, title: str, employer: str,
                        employer_id: str = None, salary_from: int = None,
                        salary_to: int = None, salary_currency: str = None,
                        url: str = None) -> bool:
        """Add new application record."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO applications
                (vacancy_id, title, employer, employer_id, salary_from, salary_to, salary_currency, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (vacancy_id, title, employer, employer_id, salary_from, salary_to, salary_currency, url))
            self.conn.commit()

            # Update company stats
            self._increment_company_applications(employer)

            return cursor.rowcount > 0
        except Exception as e:
            print(f"[DB] Error adding application: {e}")
            return False

    def get_application(self, vacancy_id: str) -> Optional[Dict]:
        """Get application by vacancy ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE vacancy_id = ?", (vacancy_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def is_already_applied(self, vacancy_id: str) -> bool:
        """Check if already applied to vacancy."""
        return self.get_application(vacancy_id) is not None

    def update_application_status(self, vacancy_id: str, status: str):
        """Update application status."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        if status == 'viewed':
            cursor.execute("""
                UPDATE applications SET status = ?, viewed_at = ?
                WHERE vacancy_id = ?
            """, (status, now, vacancy_id))
        elif status in ('invited', 'rejected'):
            cursor.execute("""
                UPDATE applications SET status = ?, response_at = ?
                WHERE vacancy_id = ?
            """, (status, now, vacancy_id))
        else:
            cursor.execute("""
                UPDATE applications SET status = ? WHERE vacancy_id = ?
            """, (status, vacancy_id))

        self.conn.commit()

    def get_applications(self, limit: int = 100, status: str = None) -> List[Dict]:
        """Get applications list."""
        cursor = self.conn.cursor()
        if status:
            cursor.execute("""
                SELECT * FROM applications WHERE status = ?
                ORDER BY applied_at DESC LIMIT ?
            """, (status, limit))
        else:
            cursor.execute("""
                SELECT * FROM applications ORDER BY applied_at DESC LIMIT ?
            """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def get_applications_count(self, days: int = None) -> int:
        """Get total applications count."""
        cursor = self.conn.cursor()
        if days:
            cursor.execute("""
                SELECT COUNT(*) FROM applications
                WHERE applied_at >= datetime('now', ?)
            """, (f'-{days} days',))
        else:
            cursor.execute("SELECT COUNT(*) FROM applications")
        return cursor.fetchone()[0]

    # ============ Companies ============

    def add_company(self, name: str, hh_id: str = None, status: str = 'normal') -> bool:
        """Add company to database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO companies (name, hh_id, status)
                VALUES (?, ?, ?)
            """, (name, hh_id, status))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

    def set_company_status(self, name: str, status: str):
        """Set company status (normal, blacklist, whitelist)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO companies (name, status)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET status = ?
        """, (name, status, status))
        self.conn.commit()

    def get_company_status(self, name: str) -> str:
        """Get company status."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT status FROM companies WHERE name = ?", (name,))
        row = cursor.fetchone()
        return row[0] if row else 'normal'

    def is_blacklisted(self, name: str) -> bool:
        """Check if company is blacklisted."""
        return self.get_company_status(name) == 'blacklist'

    def is_whitelisted(self, name: str) -> bool:
        """Check if company is whitelisted."""
        return self.get_company_status(name) == 'whitelist'

    def get_blacklisted_companies(self) -> List[str]:
        """Get list of blacklisted companies."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM companies WHERE status = 'blacklist'")
        return [row[0] for row in cursor.fetchall()]

    def get_whitelisted_companies(self) -> List[str]:
        """Get list of whitelisted companies."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM companies WHERE status = 'whitelist'")
        return [row[0] for row in cursor.fetchall()]

    def _increment_company_applications(self, name: str):
        """Increment applications count for company."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO companies (name, applications_count)
            VALUES (?, 1)
            ON CONFLICT(name) DO UPDATE SET applications_count = applications_count + 1
        """, (name,))
        self.conn.commit()

    # ============ Blacklist Words ============

    def add_blacklist_word(self, word: str) -> bool:
        """Add word to blacklist."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO blacklist_words (word) VALUES (?)
            """, (word.lower(),))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

    def remove_blacklist_word(self, word: str):
        """Remove word from blacklist."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM blacklist_words WHERE word = ?", (word.lower(),))
        self.conn.commit()

    def get_blacklist_words(self) -> List[str]:
        """Get all blacklisted words."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT word FROM blacklist_words")
        return [row[0] for row in cursor.fetchall()]

    def contains_blacklist_word(self, text: str) -> bool:
        """Check if text contains any blacklisted word."""
        text_lower = text.lower()
        for word in self.get_blacklist_words():
            if word in text_lower:
                return True
        return False

    # ============ Resumes ============

    def add_resume(self, hh_id: str, title: str, status: str = 'active'):
        """Add or update resume."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO resumes (hh_id, title, status, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(hh_id) DO UPDATE SET
                title = ?, status = ?, last_updated = ?
        """, (hh_id, title, status, datetime.now().isoformat(),
              title, status, datetime.now().isoformat()))
        self.conn.commit()

    def get_resumes(self) -> List[Dict]:
        """Get all resumes."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM resumes ORDER BY last_updated DESC")
        return [dict(row) for row in cursor.fetchall()]

    # ============ Statistics ============

    def get_stats(self) -> Dict:
        """Get overall statistics."""
        cursor = self.conn.cursor()

        stats = {}

        # Total applications
        cursor.execute("SELECT COUNT(*) FROM applications")
        stats['total_applications'] = cursor.fetchone()[0]

        # Today's applications
        cursor.execute("""
            SELECT COUNT(*) FROM applications
            WHERE date(applied_at) = date('now')
        """)
        stats['today_applications'] = cursor.fetchone()[0]

        # This week
        cursor.execute("""
            SELECT COUNT(*) FROM applications
            WHERE applied_at >= datetime('now', '-7 days')
        """)
        stats['week_applications'] = cursor.fetchone()[0]

        # By status
        cursor.execute("""
            SELECT status, COUNT(*) FROM applications GROUP BY status
        """)
        stats['by_status'] = {row[0]: row[1] for row in cursor.fetchall()}

        # Top employers
        cursor.execute("""
            SELECT employer, COUNT(*) as cnt FROM applications
            GROUP BY employer ORDER BY cnt DESC LIMIT 10
        """)
        stats['top_employers'] = [(row[0], row[1]) for row in cursor.fetchall()]

        # Companies count
        cursor.execute("SELECT COUNT(*) FROM companies WHERE status = 'blacklist'")
        stats['blacklisted_companies'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM companies WHERE status = 'whitelist'")
        stats['whitelisted_companies'] = cursor.fetchone()[0]

        return stats

    def export_to_csv(self, filepath: str):
        """Export applications to CSV."""
        import csv

        applications = self.get_applications(limit=10000)

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            if applications:
                writer = csv.DictWriter(f, fieldnames=applications[0].keys())
                writer.writeheader()
                writer.writerows(applications)

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
