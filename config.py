"""
HeadHunter Destroyer - Configuration
"""

import os
import platform

# Auto-detect platform and display mode
PLATFORM = platform.system().lower()
IS_LINUX = PLATFORM == "linux"
IS_WINDOWS = PLATFORM == "windows"

# Check if running in headless environment (no display)
HAS_DISPLAY = os.environ.get("DISPLAY") is not None or IS_WINDOWS

# Server mode: headless browser + TUI interface
# Auto-enabled on Linux without display, can be forced via env var
SERVER_MODE = os.environ.get("HH_SERVER_MODE", "auto")
if SERVER_MODE == "auto":
    SERVER_MODE = IS_LINUX and not HAS_DISPLAY
else:
    SERVER_MODE = SERVER_MODE.lower() in ("1", "true", "yes")

# Browser settings
HEADLESS = SERVER_MODE  # Headless when in server mode
SLOW_MO = 50 if SERVER_MODE else 100  # Faster in headless mode

# Browser selection: "chrome", "edge", "firefox", "auto"
# "auto" = Chrome on all platforms, Edge as fallback on Windows
# Can be overridden via HH_BROWSER env var
BROWSER = os.environ.get("HH_BROWSER", "auto").lower()

# HH.ru URLs
HH_BASE_URL = "https://hh.ru"
HH_RESUMES_URL = "https://hh.ru/applicant/resumes"
HH_VACANCY_SEARCH_URL = "https://hh.ru/search/vacancy"

# Selectors (data-qa attributes from HH.ru)
SELECTORS = {
    # Resume page
    "resume_card": '[data-qa="resume"]',
    "resume_update_button": '[data-qa="resume-update-button_actions"]',
    "resume_edit_position": '[data-qa="edit-position-button"]',
    "resume_edit_about": '[data-qa="resume-edit-button-about"]',
    "resume_title": '[data-qa="resume-title"]',

    # Vacancy search page
    "vacancy_card": '[data-qa="vacancy-serp__vacancy"]',
    "vacancy_response_button": '[data-qa="vacancy-serp__vacancy_response"]',
    "vacancy_title": '[data-qa^="serp-item__title"]',
    "vacancy_employer": '[data-qa="vacancy-serp__vacancy-employer"]',

    # Navigation
    "nav_resumes": '[data-qa="mainmenu_profileAndResumes"]',
    "nav_responses": '[data-qa="mainmenu_vacancyResponses"]',
    "nav_search": '[data-qa="mainmenu_myResumes"]',

    # Pagination
    "pager_next": '[data-qa="pager-next"]',

    # Modal/Dialog
    "modal_close": '[data-qa="bloko-modal-close"]',
    "submit_button": 'button[type="submit"]',
}

# Timing settings
TIMEOUTS = {
    "page_load": 30000,  # ms
    "element_wait": 10000,  # ms
    "between_actions": (1, 3) if SERVER_MODE else (2, 5),  # faster in server mode
    "between_responses": (2, 5) if SERVER_MODE else (3, 8),
    "resume_update_interval": 240,  # 4 hours in minutes (HH limit)
}

# Limits
LIMITS = {
    "max_responses_per_session": 200,
    "max_pages_to_scan": 50,
}

# Search filters (can be customized)
DEFAULT_SEARCH_PARAMS = {
    "text": "",
    "area": "1",  # 1 = Moscow, 2 = St. Petersburg
    "experience": "between1And3",
    "schedule": "remote",
    "order_by": "publication_time",
}

# User data directory for browser profile
USER_DATA_DIR = "./browser_data"
