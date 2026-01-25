"""
HeadHunter Destroyer - Cover Letter Templates
Support for customizable cover letter templates with placeholders.
"""

import re
from typing import Dict, List, Optional
from database import Database


class CoverLetterManager:
    """Manages cover letter templates with placeholder substitution."""

    # Available placeholders
    PLACEHOLDERS = {
        "{company}": "Название компании",
        "{position}": "Название вакансии",
        "{salary}": "Зарплата (если указана)",
        "{experience}": "Требуемый опыт",
        "{name}": "Ваше имя (из настроек)",
        "{date}": "Текущая дата",
    }

    def __init__(self, db: Database = None):
        self.db = db or Database()
        self._ensure_table()
        self._user_name = None

    def _ensure_table(self):
        """Create templates table if not exists."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cover_letter_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                is_default BOOLEAN DEFAULT 0,
                use_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.conn.commit()

        # Add default template if none exists
        cursor.execute("SELECT COUNT(*) FROM cover_letter_templates")
        if cursor.fetchone()[0] == 0:
            self._add_default_templates()

    def _add_default_templates(self):
        """Add default cover letter templates."""
        templates = [
            {
                "name": "Стандартный",
                "content": """Здравствуйте!

Меня заинтересовала вакансия "{position}" в компании {company}.

Готов обсудить детали сотрудничества.

С уважением""",
                "is_default": True
            },
            {
                "name": "Короткий",
                "content": "Добрый день! Заинтересовала вакансия {position}. Буду рад обсудить.",
                "is_default": False
            },
            {
                "name": "Развёрнутый",
                "content": """Здравствуйте!

Меня очень заинтересовала вакансия "{position}" в вашей компании {company}.

Мой опыт и навыки соответствуют вашим требованиям. Буду рад возможности обсудить, как я могу быть полезен вашей команде.

Готов к собеседованию в удобное для вас время.

С уважением""",
                "is_default": False
            },
            {
                "name": "IT специалист",
                "content": """Добрый день!

Рассмотрел вакансию "{position}" в {company} — интересный стек и задачи.

Имею релевантный опыт, готов обсудить детали на созвоне.

Best regards""",
                "is_default": False
            },
        ]

        for template in templates:
            self.add_template(template["name"], template["content"], template["is_default"])

    def set_user_name(self, name: str):
        """Set user name for {name} placeholder."""
        self._user_name = name

    def add_template(self, name: str, content: str, is_default: bool = False) -> bool:
        """Add new cover letter template."""
        try:
            cursor = self.db.conn.cursor()

            # If setting as default, unset other defaults
            if is_default:
                cursor.execute("UPDATE cover_letter_templates SET is_default = 0")

            cursor.execute("""
                INSERT INTO cover_letter_templates (name, content, is_default)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    content = ?, is_default = ?, updated_at = CURRENT_TIMESTAMP
            """, (name, content, is_default, content, is_default))

            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"[!] Error adding template: {e}")
            return False

    def get_template(self, name: str = None) -> Optional[Dict]:
        """Get template by name or default template."""
        cursor = self.db.conn.cursor()

        if name:
            cursor.execute(
                "SELECT * FROM cover_letter_templates WHERE name = ?",
                (name,)
            )
        else:
            # Get default template
            cursor.execute(
                "SELECT * FROM cover_letter_templates WHERE is_default = 1"
            )

        row = cursor.fetchone()
        if row:
            return dict(row)

        # Fallback to first template
        cursor.execute("SELECT * FROM cover_letter_templates LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_templates(self) -> List[Dict]:
        """Get all templates."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM cover_letter_templates ORDER BY is_default DESC, use_count DESC")
        return [dict(row) for row in cursor.fetchall()]

    def delete_template(self, name: str) -> bool:
        """Delete template by name."""
        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM cover_letter_templates WHERE name = ?", (name,))
        self.db.conn.commit()
        return cursor.rowcount > 0

    def set_default(self, name: str) -> bool:
        """Set template as default."""
        cursor = self.db.conn.cursor()
        cursor.execute("UPDATE cover_letter_templates SET is_default = 0")
        cursor.execute(
            "UPDATE cover_letter_templates SET is_default = 1 WHERE name = ?",
            (name,)
        )
        self.db.conn.commit()
        return cursor.rowcount > 0

    def render(self, template_name: str = None, vacancy: Dict = None) -> str:
        """
        Render cover letter with placeholders replaced.

        Args:
            template_name: Template name (None = default)
            vacancy: Vacancy data dict with keys: title, employer, salary_from, etc.

        Returns:
            Rendered cover letter text
        """
        template = self.get_template(template_name)
        if not template:
            return ""

        content = template["content"]
        vacancy = vacancy or {}

        # Build replacements
        from datetime import datetime
        replacements = {
            "{company}": vacancy.get("employer", "вашей компании"),
            "{position}": vacancy.get("title", "данную позицию"),
            "{name}": self._user_name or "",
            "{date}": datetime.now().strftime("%d.%m.%Y"),
        }

        # Salary
        salary_from = vacancy.get("salary_from")
        salary_to = vacancy.get("salary_to")
        if salary_from and salary_to:
            replacements["{salary}"] = f"{salary_from:,} - {salary_to:,} ₽"
        elif salary_from:
            replacements["{salary}"] = f"от {salary_from:,} ₽"
        elif salary_to:
            replacements["{salary}"] = f"до {salary_to:,} ₽"
        else:
            replacements["{salary}"] = "не указана"

        # Experience
        replacements["{experience}"] = vacancy.get("experience", "")

        # Apply replacements
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, str(value))

        # Increment use count
        self._increment_use_count(template["name"])

        return content

    def _increment_use_count(self, name: str):
        """Increment template use counter."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            "UPDATE cover_letter_templates SET use_count = use_count + 1 WHERE name = ?",
            (name,)
        )
        self.db.conn.commit()

    def get_placeholders_help(self) -> str:
        """Get help text for available placeholders."""
        lines = ["Доступные плейсхолдеры:"]
        for placeholder, description in self.PLACEHOLDERS.items():
            lines.append(f"  {placeholder} - {description}")
        return "\n".join(lines)


# Default instance
_default_manager = None


def get_cover_letter_manager(db: Database = None) -> CoverLetterManager:
    """Get or create default cover letter manager."""
    global _default_manager
    if _default_manager is None:
        _default_manager = CoverLetterManager(db)
    return _default_manager
