"""
HeadHunter Destroyer - Vacancy Applier
Automatically applies to vacancies matching search criteria.
"""

import time
import random
import re
from urllib.parse import urlencode, urlparse, parse_qs
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from config import SELECTORS, HH_VACANCY_SEARCH_URL, TIMEOUTS, LIMITS, DEFAULT_SEARCH_PARAMS


class VacancyApplier:
    """Handles mass vacancy applications."""

    def __init__(self, page: Page):
        self.page = page
        self.applied_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.applied_ids = set()  # Track applied vacancy IDs

    def build_search_url(self, params: dict = None) -> str:
        """Build vacancy search URL with parameters."""
        search_params = DEFAULT_SEARCH_PARAMS.copy()
        if params:
            search_params.update(params)

        # Filter out empty values
        search_params = {k: v for k, v in search_params.items() if v}

        return f"{HH_VACANCY_SEARCH_URL}?{urlencode(search_params)}"

    def get_vacancies_on_page(self) -> list:
        """Get all vacancy cards on current page."""
        vacancies = []

        # Wait for vacancy cards to load
        try:
            self.page.wait_for_selector(SELECTORS["vacancy_card"], timeout=TIMEOUTS["element_wait"])
        except PlaywrightTimeout:
            print("[!] No vacancies found on page")
            return vacancies

        vacancy_cards = self.page.query_selector_all(SELECTORS["vacancy_card"])

        for card in vacancy_cards:
            try:
                # Get vacancy ID from card
                vacancy_id = card.get_attribute("data-vacancy-id")
                if not vacancy_id:
                    # Try to extract from link
                    link_el = card.query_selector("a[href*='/vacancy/']")
                    if link_el:
                        href = link_el.get_attribute("href")
                        match = re.search(r'/vacancy/(\d+)', href)
                        if match:
                            vacancy_id = match.group(1)

                # Get vacancy title
                title_el = card.query_selector("a[data-qa*='title'], span[data-qa*='title']")
                title = title_el.inner_text() if title_el else "Unknown"

                # Get employer name
                employer_el = card.query_selector(SELECTORS["vacancy_employer"])
                employer = employer_el.inner_text() if employer_el else "Unknown"

                # Get response button
                response_btn = card.query_selector(SELECTORS["vacancy_response_button"])

                vacancies.append({
                    "id": vacancy_id,
                    "title": title.strip(),
                    "employer": employer.strip(),
                    "response_button": response_btn,
                    "card": card
                })

            except Exception as e:
                print(f"[!] Error parsing vacancy card: {e}")

        return vacancies

    def apply_to_vacancy(self, vacancy: dict) -> bool:
        """Apply to a single vacancy."""
        if not vacancy.get("response_button"):
            print(f"  [-] No response button for: {vacancy['title']}")
            return False

        if vacancy["id"] in self.applied_ids:
            print(f"  [~] Already applied: {vacancy['title']}")
            return False

        try:
            # Scroll to button
            vacancy["response_button"].scroll_into_view_if_needed()
            time.sleep(random.uniform(0.3, 0.6))

            # Check button text - might be "Responded" or "Apply"
            btn_text = vacancy["response_button"].inner_text().lower()
            if "откликнулись" in btn_text or "responded" in btn_text:
                print(f"  [~] Already responded: {vacancy['title']}")
                self.applied_ids.add(vacancy["id"])
                return False

            # Click response button
            vacancy["response_button"].click()
            time.sleep(random.uniform(1, 2))

            # Handle response modal if appears
            self._handle_response_modal()

            self.applied_ids.add(vacancy["id"])
            return True

        except PlaywrightTimeout:
            print(f"  [!] Timeout applying to: {vacancy['title']}")
            return False
        except Exception as e:
            print(f"  [!] Error applying to {vacancy['title']}: {e}")
            return False

    def _handle_response_modal(self):
        """Handle the response modal/dialog that appears after clicking apply."""
        try:
            # Wait a bit for modal to appear
            time.sleep(random.uniform(0.5, 1))

            # Check for resume selection modal
            resume_select = self.page.query_selector('[data-qa="resume-select"]')
            if resume_select:
                # Click first available resume if multiple
                first_resume = self.page.query_selector('[data-qa="resume-select-item"]')
                if first_resume:
                    first_resume.click()
                    time.sleep(random.uniform(0.3, 0.5))

            # Check for cover letter field (optional)
            cover_letter = self.page.query_selector('textarea[data-qa="vacancy-response-letter-text"]')
            # We'll skip cover letter for now - can be added later

            # Check for submit button
            submit_btn = self.page.query_selector('[data-qa="vacancy-response-submit-popup"]')
            if submit_btn:
                submit_btn.click()
                time.sleep(random.uniform(0.5, 1))
                return

            # Alternative submit button
            submit_btn = self.page.query_selector('button[data-qa*="response-submit"]')
            if submit_btn:
                submit_btn.click()
                time.sleep(random.uniform(0.5, 1))
                return

            # Close any modal that might be blocking
            close_btn = self.page.query_selector(SELECTORS["modal_close"])
            if close_btn:
                close_btn.click()

        except Exception as e:
            print(f"  [!] Error handling modal: {e}")

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
        except Exception as e:
            print(f"[!] Error navigating to next page: {e}")
        return False

    def mass_apply(self, search_params: dict = None, max_applications: int = None) -> dict:
        """
        Apply to vacancies matching search criteria.

        Args:
            search_params: Search filter parameters
            max_applications: Maximum number of applications (None = use config limit)
        """
        if max_applications is None:
            max_applications = LIMITS["max_responses_per_session"]

        results = {
            "applied": [],
            "skipped": [],
            "failed": [],
            "pages_scanned": 0
        }

        # Navigate to search page
        search_url = self.build_search_url(search_params)
        print(f"\n[*] Starting vacancy search: {search_url}")
        self.page.goto(search_url, wait_until="domcontentloaded")
        time.sleep(random.uniform(1, 2))

        current_page = 1

        while (self.applied_count < max_applications and
               current_page <= LIMITS["max_pages_to_scan"]):

            print(f"\n[*] Scanning page {current_page}...")
            results["pages_scanned"] = current_page

            vacancies = self.get_vacancies_on_page()
            print(f"[*] Found {len(vacancies)} vacancies on page")

            for vacancy in vacancies:
                if self.applied_count >= max_applications:
                    print(f"\n[*] Reached application limit: {max_applications}")
                    break

                print(f"\n[>] {vacancy['title']} @ {vacancy['employer']}")

                if self.apply_to_vacancy(vacancy):
                    print(f"  [+] Applied successfully!")
                    self.applied_count += 1
                    results["applied"].append({
                        "id": vacancy["id"],
                        "title": vacancy["title"],
                        "employer": vacancy["employer"]
                    })
                else:
                    self.skipped_count += 1
                    results["skipped"].append(vacancy["title"])

                # Random delay between applications
                delay = random.uniform(*TIMEOUTS["between_responses"])
                print(f"  [~] Waiting {delay:.1f}s...")
                time.sleep(delay)

            # Go to next page
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
