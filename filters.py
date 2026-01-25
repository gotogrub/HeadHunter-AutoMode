"""
HeadHunter Destroyer - Smart Filters
Filter vacancies by various criteria.
"""

import re
from typing import Dict, List, Optional
from database import Database


class VacancyFilter:
    """Smart vacancy filtering system."""

    def __init__(self, db: Database = None):
        self.db = db or Database()

        # In-memory filters (loaded from DB + config)
        self._blacklist_companies = set()
        self._whitelist_companies = set()
        self._blacklist_words = set()

        # Configurable filters
        self.min_salary = None
        self.max_salary = None
        self.salary_currency = "RUR"
        self.max_days_old = None
        self.require_salary = False

        # Load from database
        self._load_from_db()

    def _load_from_db(self):
        """Load filters from database."""
        self._blacklist_companies = set(self.db.get_blacklisted_companies())
        self._whitelist_companies = set(self.db.get_whitelisted_companies())
        self._blacklist_words = set(self.db.get_blacklist_words())

    def reload(self):
        """Reload filters from database."""
        self._load_from_db()

    # ============ Company Filters ============

    def add_blacklist_company(self, name: str):
        """Add company to blacklist."""
        name_lower = name.lower().strip()
        self._blacklist_companies.add(name_lower)
        self.db.set_company_status(name, 'blacklist')

    def remove_blacklist_company(self, name: str):
        """Remove company from blacklist."""
        name_lower = name.lower().strip()
        self._blacklist_companies.discard(name_lower)
        self.db.set_company_status(name, 'normal')

    def add_whitelist_company(self, name: str):
        """Add company to whitelist (priority)."""
        name_lower = name.lower().strip()
        self._whitelist_companies.add(name_lower)
        self.db.set_company_status(name, 'whitelist')

    def remove_whitelist_company(self, name: str):
        """Remove company from whitelist."""
        name_lower = name.lower().strip()
        self._whitelist_companies.discard(name_lower)
        self.db.set_company_status(name, 'normal')

    def is_company_blacklisted(self, name: str) -> bool:
        """Check if company is blacklisted."""
        name_lower = name.lower().strip()
        for blacklisted in self._blacklist_companies:
            if blacklisted in name_lower or name_lower in blacklisted:
                return True
        return False

    def is_company_whitelisted(self, name: str) -> bool:
        """Check if company is whitelisted."""
        name_lower = name.lower().strip()
        for whitelisted in self._whitelist_companies:
            if whitelisted in name_lower or name_lower in whitelisted:
                return True
        return False

    # ============ Word Filters ============

    def add_blacklist_word(self, word: str):
        """Add word to blacklist."""
        word_lower = word.lower().strip()
        self._blacklist_words.add(word_lower)
        self.db.add_blacklist_word(word)

    def remove_blacklist_word(self, word: str):
        """Remove word from blacklist."""
        word_lower = word.lower().strip()
        self._blacklist_words.discard(word_lower)
        self.db.remove_blacklist_word(word)

    def contains_blacklist_word(self, text: str) -> bool:
        """Check if text contains blacklisted words."""
        text_lower = text.lower()
        for word in self._blacklist_words:
            if word in text_lower:
                return True
        return False

    # ============ Salary Filters ============

    def set_salary_filter(self, min_salary: int = None, max_salary: int = None,
                          currency: str = "RUR", require: bool = False):
        """Set salary filter parameters."""
        self.min_salary = min_salary
        self.max_salary = max_salary
        self.salary_currency = currency
        self.require_salary = require

    def check_salary(self, salary_from: int = None, salary_to: int = None) -> bool:
        """Check if salary matches filter."""
        # If no salary info and we require it
        if self.require_salary and salary_from is None and salary_to is None:
            return False

        # If no salary filter set
        if self.min_salary is None and self.max_salary is None:
            return True

        # If no salary info in vacancy but filter is set (but not required)
        if salary_from is None and salary_to is None:
            return not self.require_salary

        # Check minimum
        if self.min_salary is not None:
            vacancy_max = salary_to or salary_from
            if vacancy_max and vacancy_max < self.min_salary:
                return False

        # Check maximum
        if self.max_salary is not None:
            vacancy_min = salary_from or salary_to
            if vacancy_min and vacancy_min > self.max_salary:
                return False

        return True

    # ============ Main Filter ============

    def should_apply(self, vacancy: Dict) -> tuple[bool, str]:
        """
        Check if should apply to vacancy.

        Returns:
            (should_apply: bool, reason: str)
        """
        title = vacancy.get('title', '')
        employer = vacancy.get('employer', '')
        description = vacancy.get('description', '')
        salary_from = vacancy.get('salary_from')
        salary_to = vacancy.get('salary_to')

        # Check if already applied
        vacancy_id = vacancy.get('id')
        if vacancy_id and self.db.is_already_applied(vacancy_id):
            return False, "already_applied"

        # Whitelist companies have priority
        if self.is_company_whitelisted(employer):
            return True, "whitelisted"

        # Check blacklisted company
        if self.is_company_blacklisted(employer):
            return False, "blacklisted_company"

        # Check blacklisted words in title
        if self.contains_blacklist_word(title):
            return False, "blacklisted_word_title"

        # Check blacklisted words in description
        if description and self.contains_blacklist_word(description):
            return False, "blacklisted_word_description"

        # Check salary
        if not self.check_salary(salary_from, salary_to):
            return False, "salary_mismatch"

        return True, "ok"

    def get_priority(self, vacancy: Dict) -> int:
        """
        Get vacancy priority for sorting.
        Higher = better.
        """
        priority = 50  # Base priority

        employer = vacancy.get('employer', '')
        salary_from = vacancy.get('salary_from')

        # Whitelisted companies get highest priority
        if self.is_company_whitelisted(employer):
            priority += 100

        # Salary bonus
        if salary_from:
            if self.min_salary and salary_from >= self.min_salary:
                priority += 20
            if salary_from >= 200000:
                priority += 30
            elif salary_from >= 150000:
                priority += 20
            elif salary_from >= 100000:
                priority += 10

        return priority

    # ============ Bulk Operations ============

    def filter_vacancies(self, vacancies: List[Dict]) -> List[Dict]:
        """
        Filter and sort vacancies list.
        Returns filtered list sorted by priority.
        """
        filtered = []

        for vacancy in vacancies:
            should_apply, reason = self.should_apply(vacancy)
            if should_apply:
                vacancy['_priority'] = self.get_priority(vacancy)
                vacancy['_filter_reason'] = reason
                filtered.append(vacancy)

        # Sort by priority (highest first)
        filtered.sort(key=lambda v: v.get('_priority', 0), reverse=True)

        return filtered

    # ============ Stats ============

    def get_filter_stats(self) -> Dict:
        """Get filter statistics."""
        return {
            'blacklist_companies': list(self._blacklist_companies),
            'whitelist_companies': list(self._whitelist_companies),
            'blacklist_words': list(self._blacklist_words),
            'min_salary': self.min_salary,
            'max_salary': self.max_salary,
            'require_salary': self.require_salary,
        }


# ============ Default Blacklist Words ============

DEFAULT_BLACKLIST_WORDS = [
    "стажёр",
    "стажер",
    "intern",
    "internship",
    "неоплачиваемый",
    "волонтёр",
    "волонтер",
    "без оплаты",
    "unpaid",
]


def setup_default_filters(db: Database):
    """Setup default blacklist words."""
    for word in DEFAULT_BLACKLIST_WORDS:
        db.add_blacklist_word(word)
