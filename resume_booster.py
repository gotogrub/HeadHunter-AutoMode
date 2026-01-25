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
        self.page.goto(HH_RESUMES_URL, wait_until="domcontentloaded")
        time.sleep(random.uniform(1, 2))

        resumes = []
        resume_cards = self.page.query_selector_all(SELECTORS["resume_card"])

        for card in resume_cards:
            try:
                title_el = card.query_selector(SELECTORS["resume_title"])
                title = title_el.inner_text() if title_el else "Unknown"

                # Get resume link
                link_el = card.query_selector("a[href*='/resume/']")
                link = link_el.get_attribute("href") if link_el else None

                resumes.append({
                    "title": title,
                    "link": link,
                    "element": card
                })
            except Exception as e:
                print(f"[!] Error parsing resume card: {e}")

        return resumes

    def update_resume_touch(self, resume_url: str) -> bool:
        """
        Update resume by making a minimal edit (touch).
        This triggers HH.ru to refresh the resume's timestamp.
        """
        try:
            # Navigate to resume edit page
            edit_url = resume_url.replace("/resume/", "/resume/edit/")
            if "?" in edit_url:
                edit_url = edit_url.split("?")[0]

            self.page.goto(edit_url, wait_until="domcontentloaded")
            time.sleep(random.uniform(1, 2))

            # Find "About" section edit button and click
            about_btn = self.page.query_selector(SELECTORS["resume_edit_about"])
            if about_btn:
                about_btn.click()
                time.sleep(random.uniform(0.5, 1))

                # Find textarea and add/remove space
                textarea = self.page.query_selector("textarea")
                if textarea:
                    current_text = textarea.input_value()

                    # Toggle trailing space
                    if current_text.endswith(" "):
                        new_text = current_text.rstrip()
                    else:
                        new_text = current_text + " "

                    textarea.fill(new_text)
                    time.sleep(random.uniform(0.3, 0.5))

                    # Submit changes
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
            print("[!] Timeout while updating resume")
            return False
        except Exception as e:
            print(f"[!] Error updating resume: {e}")
            return False

    def boost_all_resumes(self) -> dict:
        """Update all user's resumes."""
        results = {
            "success": [],
            "failed": []
        }

        resumes = self.get_resumes()
        print(f"\n[*] Found {len(resumes)} resume(s)")

        for resume in resumes:
            if not resume["link"]:
                print(f"[!] Skipping resume without link: {resume['title']}")
                results["failed"].append(resume["title"])
                continue

            print(f"[*] Updating: {resume['title']}")

            if self.update_resume_touch(f"https://hh.ru{resume['link']}"):
                print(f"[+] Successfully updated: {resume['title']}")
                results["success"].append(resume["title"])
            else:
                print(f"[-] Failed to update: {resume['title']}")
                results["failed"].append(resume["title"])

            # Delay between updates
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
