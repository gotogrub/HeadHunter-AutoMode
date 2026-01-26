"""
HeadHunter Destroyer - Resume Booster
Automatically updates resume to boost its visibility in search.
"""

import time
import random
from datetime import datetime
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from config import SELECTORS, HH_RESUMES_URL, TIMEOUTS


class ResumeBooster:
    """Handles resume updates to boost visibility."""

    def __init__(self, page: Page):
        self.page = page
        self.last_update_time = None

    def get_resumes(self) -> list:
        """Get list of user's resumes."""
        print(f"[DEBUG] Переход на страницу резюме: {HH_RESUMES_URL}")
        self.page.goto(HH_RESUMES_URL, wait_until="domcontentloaded")
        time.sleep(random.uniform(1, 2))

        print(f"[DEBUG] Текущий URL: {self.page.url}")

        resumes = []
        resume_cards = self.page.query_selector_all(SELECTORS["resume_card"])
        print(f"[DEBUG] Найдено карточек резюме: {len(resume_cards)}")

        for i, card in enumerate(resume_cards):
            try:
                title_el = card.query_selector(SELECTORS["resume_title"])
                title = title_el.inner_text() if title_el else "Unknown"

                link_el = card.query_selector("a[href*='/resume/']")
                link = link_el.get_attribute("href") if link_el else None

                print(f"[DEBUG] Резюме {i+1}: {title}, link={link}")

                # Убедиться что ссылка полная
                if link and not link.startswith("http"):
                    link = f"https://hh.ru{link}"

                resumes.append({
                    "title": title,
                    "link": link,
                    "element": card
                })
            except Exception as e:
                print(f"[DEBUG] Ошибка парсинга карточки {i+1}: {e}")

        return resumes

    def update_resume_touch(self, resume_url: str) -> bool:
        """
        Update resume by making a minimal edit (touch).
        This triggers HH.ru to refresh the resume's timestamp.
        """
        try:
            # Построить edit URL
            if "/resume/edit/" in resume_url:
                edit_url = resume_url
            else:
                edit_url = resume_url.replace("/resume/", "/resume/edit/")

            # Убрать query параметры
            if "?" in edit_url:
                edit_url = edit_url.split("?")[0]

            # Убедиться что ссылка полная
            if not edit_url.startswith("http"):
                edit_url = f"https://hh.ru{edit_url}"

            print(f"[DEBUG] Переход на edit URL: {edit_url}")
            self.page.goto(edit_url, wait_until="domcontentloaded")
            time.sleep(random.uniform(1, 2))

            print(f"[DEBUG] Текущий URL после перехода: {self.page.url}")

            # Find "About" section edit button and click
            about_btn = self.page.query_selector(SELECTORS["resume_edit_about"])
            if about_btn:
                about_btn.click()
                time.sleep(random.uniform(0.5, 1))

                textarea = self.page.query_selector("textarea")
                if textarea:
                    current_text = textarea.input_value()

                    if current_text.endswith(" "):
                        new_text = current_text.rstrip()
                    else:
                        new_text = current_text + " "

                    textarea.fill(new_text)
                    time.sleep(random.uniform(0.3, 0.5))

                    submit_btn = self.page.query_selector(SELECTORS["submit_button"])
                    if submit_btn:
                        submit_btn.click()
                        time.sleep(random.uniform(1, 2))
                        self.last_update_time = datetime.now()
                        return True

            # Alternative: use the "Update" button if available
            update_btn = self.page.query_selector(SELECTORS["resume_update_button"])
            if update_btn:
                update_btn.click()
                time.sleep(random.uniform(1, 2))
                self.last_update_time = datetime.now()
                return True

            return False

        except PlaywrightTimeout:
            return False
        except Exception:
            return False

    def boost_all_resumes(self, callback=None) -> dict:
        """
        Update all user's resumes.

        Args:
            callback: Optional callback function(title, status) for TUI
        """
        results = {
            "success": [],
            "failed": []
        }

        resumes = self.get_resumes()

        for resume in resumes:
            if not resume["link"]:
                if callback:
                    callback(resume["title"], "failed")
                results["failed"].append(resume["title"])
                continue

            success = self.update_resume_touch(f"https://hh.ru{resume['link']}")

            if success:
                if callback:
                    callback(resume["title"], "success")
                results["success"].append(resume["title"])
            else:
                if callback:
                    callback(resume["title"], "failed")
                results["failed"].append(resume["title"])

            time.sleep(random.uniform(*TIMEOUTS["between_actions"]))

        return results

    def can_update(self) -> bool:
        """Check if enough time has passed since last update."""
        if not self.last_update_time:
            return True

        elapsed = (datetime.now() - self.last_update_time).total_seconds() / 60
        return elapsed >= TIMEOUTS["resume_update_interval"]

    def minutes_until_next_update(self) -> int:
        """Get minutes until next update is allowed."""
        if not self.last_update_time:
            return 0

        elapsed = (datetime.now() - self.last_update_time).total_seconds() / 60
        remaining = TIMEOUTS["resume_update_interval"] - elapsed
        return max(0, int(remaining))
