"""
HeadHunter Destroyer - Vacancy Applier
Automatically applies to vacancies matching search criteria.
"""

import time
import random
import re
from urllib.parse import urlencode
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from config import SELECTORS, HH_VACANCY_SEARCH_URL, TIMEOUTS, LIMITS, DEFAULT_SEARCH_PARAMS


class VacancyApplier:
    """Handles mass vacancy applications."""

    def __init__(self, page: Page):
        self.page = page
        self.applied_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.applied_ids = set()

    def build_search_url(self, params: dict = None) -> str:
        """Build vacancy search URL with parameters."""
        search_params = DEFAULT_SEARCH_PARAMS.copy()
        if params:
            search_params.update(params)

        search_params = {k: v for k, v in search_params.items() if v}
        return f"{HH_VACANCY_SEARCH_URL}?{urlencode(search_params)}"

    def get_vacancies_on_page(self) -> list:
        """Get all vacancy cards on current page."""
        vacancies = []

        try:
            self.page.wait_for_selector(SELECTORS["vacancy_card"], timeout=TIMEOUTS["element_wait"])
        except PlaywrightTimeout:
            return vacancies

        vacancy_cards = self.page.query_selector_all(SELECTORS["vacancy_card"])

        for card in vacancy_cards:
            try:
                vacancy_id = card.get_attribute("data-vacancy-id")
                if not vacancy_id:
                    link_el = card.query_selector("a[href*='/vacancy/']")
                    if link_el:
                        href = link_el.get_attribute("href")
                        match = re.search(r'/vacancy/(\d+)', href)
                        if match:
                            vacancy_id = match.group(1)

                title_el = card.query_selector("a[data-qa*='title'], span[data-qa*='title']")
                title = title_el.inner_text() if title_el else "Unknown"

                employer_el = card.query_selector(SELECTORS["vacancy_employer"])
                employer = employer_el.inner_text() if employer_el else "Unknown"

                response_btn = card.query_selector(SELECTORS["vacancy_response_button"])

                vacancies.append({
                    "id": vacancy_id,
                    "title": title.strip(),
                    "employer": employer.strip(),
                    "response_button": response_btn,
                    "card": card
                })

            except Exception:
                pass

        return vacancies

    def apply_to_vacancy(self, vacancy: dict) -> str:
        """
        Apply to a single vacancy.
        Returns: 'applied', 'skipped', or 'failed'
        """
        if not vacancy.get("response_button"):
            return "skipped"

        if vacancy["id"] in self.applied_ids:
            return "skipped"

        try:
            vacancy["response_button"].scroll_into_view_if_needed()
            time.sleep(random.uniform(0.3, 0.6))

            btn_text = vacancy["response_button"].inner_text().lower()
            if "откликнулись" in btn_text or "responded" in btn_text:
                self.applied_ids.add(vacancy["id"])
                return "skipped"

            vacancy["response_button"].click()
            time.sleep(random.uniform(1, 2))

            self._handle_response_modal()

            self.applied_ids.add(vacancy["id"])
            return "applied"

        except PlaywrightTimeout:
            return "failed"
        except Exception:
            return "failed"

    def _handle_response_modal(self):
        """Handle the response modal/dialog that appears after clicking apply."""
        try:
            time.sleep(random.uniform(0.5, 1))

            resume_select = self.page.query_selector('[data-qa="resume-select"]')
            if resume_select:
                first_resume = self.page.query_selector('[data-qa="resume-select-item"]')
                if first_resume:
                    first_resume.click()
                    time.sleep(random.uniform(0.3, 0.5))

            submit_btn = self.page.query_selector('[data-qa="vacancy-response-submit-popup"]')
            if submit_btn:
                submit_btn.click()
                time.sleep(random.uniform(0.5, 1))
                return

            submit_btn = self.page.query_selector('button[data-qa*="response-submit"]')
            if submit_btn:
                submit_btn.click()
                time.sleep(random.uniform(0.5, 1))
                return

            close_btn = self.page.query_selector(SELECTORS["modal_close"])
            if close_btn:
                close_btn.click()

        except Exception:
            pass

    def has_next_page(self) -> bool:
        """Check if there's a next page of results."""
        next_btn = self.page.query_selector(SELECTORS["pager_next"])
        return next_btn is not None and next_btn.is_enabled()

    def go_to_next_page(self) -> bool:
        """Navigate to next page of results."""
        try:
            next_btn = self.page.query_selector(SELECTORS["pager_next"])
            if next_btn and next_btn.is_enabled():
                next_btn.click()
                time.sleep(random.uniform(1, 2))
                return True
        except Exception:
            pass
        return False

    def mass_apply(self, search_params: dict = None, max_applications: int = None, callbacks: dict = None) -> dict:
        """
        Apply to vacancies matching search criteria.

        Args:
            search_params: Search filter parameters
            max_applications: Maximum number of applications
            callbacks: Dict with 'on_vacancy' and 'on_page' callback functions
        """
        if max_applications is None:
            max_applications = LIMITS["max_responses_per_session"]

        results = {
            "applied": [],
            "skipped": [],
            "failed": [],
            "pages_scanned": 0
        }

        # Callbacks for TUI
        on_vacancy = callbacks.get("on_vacancy") if callbacks else None
        on_page = callbacks.get("on_page") if callbacks else None

        search_url = self.build_search_url(search_params)
        self.page.goto(search_url, wait_until="domcontentloaded")
        time.sleep(random.uniform(1, 2))

        current_page = 1

        while (self.applied_count < max_applications and
               current_page <= LIMITS["max_pages_to_scan"]):

            results["pages_scanned"] = current_page
            vacancies = self.get_vacancies_on_page()

            if on_page:
                on_page(current_page, len(vacancies))

            for vacancy in vacancies:
                if self.applied_count >= max_applications:
                    break

                status = self.apply_to_vacancy(vacancy)

                # Call TUI callback
                if on_vacancy:
                    on_vacancy(vacancy["title"], vacancy["employer"], status)

                if status == "applied":
                    self.applied_count += 1
                    results["applied"].append({
                        "id": vacancy["id"],
                        "title": vacancy["title"],
                        "employer": vacancy["employer"],
                        "status": status
                    })
                elif status == "skipped":
                    self.skipped_count += 1
                    results["skipped"].append(vacancy["title"])
                else:
                    self.failed_count += 1
                    results["failed"].append(vacancy["title"])

                delay = random.uniform(*TIMEOUTS["between_responses"])
                time.sleep(delay)

            if self.applied_count < max_applications and self.has_next_page():
                if not self.go_to_next_page():
                    break
                current_page += 1
            else:
                break

        return results

    def get_stats(self) -> dict:
        """Get current session statistics."""
        return {
            "applied": self.applied_count,
            "skipped": self.skipped_count,
            "failed": self.failed_count,
            "total_processed": len(self.applied_ids)
        }
