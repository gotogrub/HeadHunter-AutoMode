"""
HeadHunter Destroyer - Configuration
"""

# Browser settings
BROWSER_TYPE = "msedge"  # msedge, chromium, firefox
HEADLESS = False  # False = visible browser window
SLOW_MO = 100  # Delay between actions in ms (helps avoid detection)

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
    "between_actions": (2, 5),  # random delay range in seconds
    "between_responses": (3, 8),  # delay between vacancy responses
    "resume_update_interval": 240,  # 4 hours in minutes (HH limit)
}

# Limits
LIMITS = {
    "max_responses_per_session": 200,  # max vacancy responses per session
    "max_pages_to_scan": 50,  # max vacancy pages to scan
}

# Search filters (can be customized)
DEFAULT_SEARCH_PARAMS = {
    "text": "",  # search query
    "area": "1",  # 1 = Moscow, 2 = St. Petersburg
    "experience": "between1And3",  # noExperience, between1And3, between3And6, moreThan6
    "schedule": "remote",  # fullDay, shift, flexible, remote, flyInFlyOut
    "order_by": "publication_time",  # relevance, publication_time, salary_desc, salary_asc
}

# User data directory for browser profile
USER_DATA_DIR = "./browser_data"
