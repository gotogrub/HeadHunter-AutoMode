"""
HeadHunter Destroyer - Vacancy Applier
Automatically applies to vacancies matching search criteria.
With database tracking, smart filters, and cover letters.
"""

import time
import random
import re
from urllib.parse import urlencode
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from config import SELECTORS, HH_VACANCY_SEARCH_URL, TIMEOUTS, LIMITS, DEFAULT_SEARCH_PARAMS


class VacancyApplier:
    """Handles mass vacancy applications with filtering and tracking."""

    def __init__(self, page: Page, db=None, filters=None, cover_letters=None, ai_assistant=None, logger=None):
        self.page = page
        self.db = db
        self.filters = filters
        self.cover_letters = cover_letters
        self.ai_assistant = ai_assistant
        self.logger = logger

        # Cover letter settings
        self.use_cover_letter = False
        self.cover_letter_template = None  # None = default template
        self.use_ai_letters = False

        self.applied_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.filtered_count = 0
        self.applied_ids = set()

    def set_cover_letter_mode(self, enabled: bool, template_name: str = None, use_ai: bool = False):
        """
        Configure cover letter mode.

        Args:
            enabled: Enable cover letters
            template_name: Template name (None = default)
            use_ai: Use AI to generate letters (requires ai_assistant)
        """
        self.use_cover_letter = enabled
        self.cover_letter_template = template_name
        self.use_ai_letters = use_ai and self.ai_assistant and self.ai_assistant.is_enabled()

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

                # Try to get salary info
                salary_from, salary_to = self._parse_salary(card)

                # Get vacancy URL
                url = None
                link_el = card.query_selector("a[href*='/vacancy/']")
                if link_el:
                    url = link_el.get_attribute("href")

                response_btn = card.query_selector(SELECTORS["vacancy_response_button"])

                vacancies.append({
                    "id": vacancy_id,
                    "title": title.strip(),
                    "employer": employer.strip(),
                    "salary_from": salary_from,
                    "salary_to": salary_to,
                    "url": url,
                    "response_button": response_btn,
                    "card": card
                })

            except Exception:
                pass

        return vacancies

    def _parse_salary(self, card) -> tuple:
        """Parse salary from vacancy card."""
        try:
            salary_el = card.query_selector('[data-qa="vacancy-serp__vacancy-compensation"]')
            if salary_el:
                salary_text = salary_el.inner_text()
                # Parse salary range like "100 000 - 150 000 ₽"
                numbers = re.findall(r'[\d\s]+', salary_text)
                numbers = [int(n.replace(' ', '').strip()) for n in numbers if n.strip()]
                if len(numbers) >= 2:
                    return numbers[0], numbers[1]
                elif len(numbers) == 1:
                    if 'от' in salary_text.lower():
                        return numbers[0], None
                    elif 'до' in salary_text.lower():
                        return None, numbers[0]
                    return numbers[0], numbers[0]
        except Exception:
            pass
        return None, None

    def apply_to_vacancy(self, vacancy: dict) -> tuple[str, str]:
        """
        Apply to a single vacancy.
        Returns: (status, reason)
            status: 'applied', 'skipped', 'failed', 'filtered'
            reason: explanation
        """
        # Check filters first
        if self.filters:
            should_apply, reason = self.filters.should_apply(vacancy)
            if not should_apply:
                return "filtered", reason

        if not vacancy.get("response_button"):
            return "skipped", "no_button"

        if vacancy["id"] in self.applied_ids:
            return "skipped", "already_in_session"

        # Check database
        if self.db and self.db.is_already_applied(vacancy["id"]):
            self.applied_ids.add(vacancy["id"])
            return "skipped", "already_in_db"

        try:
            vacancy["response_button"].scroll_into_view_if_needed()
            time.sleep(random.uniform(0.3, 0.6))

            btn_text = vacancy["response_button"].inner_text().lower()
            if "откликнулись" in btn_text or "responded" in btn_text:
                self.applied_ids.add(vacancy["id"])
                # Save to DB as already applied
                if self.db:
                    self.db.add_application(
                        vacancy_id=vacancy["id"],
                        title=vacancy["title"],
                        employer=vacancy["employer"],
                        salary_from=vacancy.get("salary_from"),
                        salary_to=vacancy.get("salary_to"),
                        url=vacancy.get("url")
                    )
                return "skipped", "already_responded"

            vacancy["response_button"].click()
            time.sleep(random.uniform(1, 2))

            self._handle_response_modal(vacancy)

            self.applied_ids.add(vacancy["id"])

            # Save to database
            if self.db:
                self.db.add_application(
                    vacancy_id=vacancy["id"],
                    title=vacancy["title"],
                    employer=vacancy["employer"],
                    salary_from=vacancy.get("salary_from"),
                    salary_to=vacancy.get("salary_to"),
                    url=vacancy.get("url")
                )

            return "applied", "success"

        except PlaywrightTimeout:
            return "failed", "timeout"
        except Exception as e:
            return "failed", str(e)

    def _handle_response_modal(self, vacancy: dict = None):
        """Handle the response modal/dialog that appears after clicking apply."""
        try:
            time.sleep(random.uniform(0.5, 1))

            # Select resume if multiple available
            resume_select = self.page.query_selector('[data-qa="resume-select"]')
            if resume_select:
                first_resume = self.page.query_selector('[data-qa="resume-select-item"]')
                if first_resume:
                    first_resume.click()
                    time.sleep(random.uniform(0.3, 0.5))

            # Fill cover letter if enabled
            if self.use_cover_letter and vacancy:
                self._fill_cover_letter(vacancy)

            # Submit application
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

    def _fill_cover_letter(self, vacancy: dict):
        """Fill cover letter in the response modal."""
        try:
            # Find cover letter textarea
            letter_input = self.page.query_selector(
                'textarea[data-qa="vacancy-response-letter-text"], '
                'textarea[name="letter"], '
                '[data-qa="vacancy-response-popup-form-letter-input"] textarea'
            )

            if not letter_input:
                return

            # Generate letter text
            letter_text = self._generate_cover_letter(vacancy)
            if not letter_text:
                return

            # Clear existing text and fill new
            letter_input.click()
            letter_input.fill("")
            time.sleep(0.1)
            letter_input.fill(letter_text)
            time.sleep(random.uniform(0.3, 0.5))

            if self.logger:
                self.logger.debug(f"[LETTER] Filled cover letter for {vacancy.get('title', 'unknown')}")

        except Exception as e:
            if self.logger:
                self.logger.debug(f"[LETTER] Failed to fill cover letter: {e}")

    def _generate_cover_letter(self, vacancy: dict) -> str:
        """Generate cover letter for vacancy."""
        # Try AI generation first if enabled
        if self.use_ai_letters and self.ai_assistant:
            try:
                ai_letter = self.ai_assistant.generate_cover_letter(vacancy)
                if ai_letter:
                    # Add greeting
                    return f"Здравствуйте!\n\n{ai_letter}"
            except Exception:
                pass

        # Fall back to template
        if self.cover_letters:
            return self.cover_letters.render(self.cover_letter_template, vacancy)

        return ""

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
            callbacks: Dict with callback functions:
                - on_vacancy(title, employer, status, reason)
                - on_page(page_num, vacancies_count)
                - on_filtered(title, employer, reason)
        """
        if max_applications is None:
            max_applications = LIMITS["max_responses_per_session"]

        results = {
            "applied": [],
            "skipped": [],
            "failed": [],
            "filtered": [],
            "pages_scanned": 0
        }

        # Callbacks
        on_vacancy = callbacks.get("on_vacancy") if callbacks else None
        on_page = callbacks.get("on_page") if callbacks else None
        on_filtered = callbacks.get("on_filtered") if callbacks else None

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

            # Log page scan
            if self.logger:
                self.logger.log_page_scan(current_page, len(vacancies))

            for vacancy in vacancies:
                if self.applied_count >= max_applications:
                    break

                status, reason = self.apply_to_vacancy(vacancy)

                # Log application
                if self.logger:
                    self.logger.log_application(
                        vacancy.get("id", ""),
                        vacancy.get("title", ""),
                        vacancy.get("employer", ""),
                        status,
                        reason
                    )

                # Callbacks
                if status == "filtered" and on_filtered:
                    on_filtered(vacancy["title"], vacancy["employer"], reason)
                elif on_vacancy:
                    on_vacancy(vacancy["title"], vacancy["employer"], status)

                # Update counters and results
                if status == "applied":
                    self.applied_count += 1
                    results["applied"].append({
                        "id": vacancy["id"],
                        "title": vacancy["title"],
                        "employer": vacancy["employer"],
                        "salary_from": vacancy.get("salary_from"),
                        "salary_to": vacancy.get("salary_to"),
                        "status": status
                    })
                elif status == "filtered":
                    self.filtered_count += 1
                    results["filtered"].append({
                        "title": vacancy["title"],
                        "employer": vacancy["employer"],
                        "reason": reason
                    })
                elif status == "skipped":
                    self.skipped_count += 1
                    results["skipped"].append(vacancy["title"])
                else:
                    self.failed_count += 1
                    results["failed"].append(vacancy["title"])

                # Delay only if actually applied
                if status == "applied":
                    delay = random.uniform(*TIMEOUTS["between_responses"])
                    time.sleep(delay)
                else:
                    time.sleep(random.uniform(0.2, 0.5))

            if self.applied_count < max_applications and self.has_next_page():
                if not self.go_to_next_page():
                    break
                current_page += 1
            else:
                break

        return results

    def get_stats(self) -> dict:
        """Get current session statistics."""
        stats = {
            "applied": self.applied_count,
            "skipped": self.skipped_count,
            "failed": self.failed_count,
            "filtered": self.filtered_count,
            "total_processed": len(self.applied_ids)
        }

        # Add database stats if available
        if self.db:
            db_stats = self.db.get_stats()
            stats["db_total"] = db_stats.get("total_applications", 0)
            stats["db_today"] = db_stats.get("today_applications", 0)
            stats["db_week"] = db_stats.get("week_applications", 0)

        return stats
