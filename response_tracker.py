"""
HeadHunter Destroyer - Response Tracker
Tracks application statuses (viewed, invited, rejected).
"""

import time
import random
from datetime import datetime
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout
from config import SELECTORS, TIMEOUTS

# HH.ru responses page
HH_RESPONSES_URL = "https://hh.ru/applicant/negotiations"


class ResponseTracker:
    """Tracks application statuses on HH.ru."""

    def __init__(self, page: Page, db=None, logger=None):
        self.page = page
        self.db = db
        self.logger = logger

    def log(self, message: str, level: str = "info"):
        """Log message."""
        if self.logger:
            getattr(self.logger, level)(message)
        else:
            print(f"[{level.upper()}] {message}")

    def check_all_responses(self) -> dict:
        """
        Check all application statuses.

        Returns:
            dict: Statistics of updates
        """
        stats = {
            "total": 0,
            "updated": 0,
            "viewed": 0,
            "invited": 0,
            "rejected": 0,
            "errors": 0
        }

        try:
            self.log("Переход на страницу откликов...")
            self.page.goto(HH_RESPONSES_URL, wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 3))

            # Пагинация - получить все страницы откликов
            page_num = 1
            has_more = True

            while has_more:
                self.log(f"Обработка страницы {page_num}...")

                # Парсим отклики на текущей странице
                responses = self._parse_responses_on_page()
                stats["total"] += len(responses)

                # Обновляем статусы в БД
                for response in responses:
                    try:
                        if self._update_response_status(response):
                            stats["updated"] += 1
                            stats[response["status"]] += 1
                    except Exception as e:
                        self.log(f"Ошибка обновления отклика {response.get('vacancy_id')}: {e}", "error")
                        stats["errors"] += 1

                # Проверить есть ли следующая страница
                has_more = self._go_to_next_page()
                page_num += 1

                time.sleep(random.uniform(1, 2))

        except Exception as e:
            self.log(f"Ошибка проверки откликов: {e}", "error")
            stats["errors"] += 1

        return stats

    def _parse_responses_on_page(self) -> list:
        """Parse responses on current page."""
        responses = []

        try:
            # Селектор для карточек откликов
            # HH.ru использует разные селекторы в зависимости от статуса
            response_items = self.page.query_selector_all('[data-qa="negotiation-item"]')

            if not response_items:
                # Альтернативный селектор
                response_items = self.page.query_selector_all('.negotiation-item')

            self.log(f"Найдено откликов на странице: {len(response_items)}", "debug")

            for item in response_items:
                try:
                    response = self._parse_response_item(item)
                    if response:
                        responses.append(response)
                except Exception as e:
                    self.log(f"Ошибка парсинга отклика: {e}", "debug")
                    continue

        except Exception as e:
            self.log(f"Ошибка парсинга страницы откликов: {e}", "error")

        return responses

    def _parse_response_item(self, item) -> dict:
        """Parse single response item."""
        try:
            # Vacancy ID из ссылки
            link = item.query_selector('a[href*="/vacancy/"]')
            vacancy_id = None
            if link:
                href = link.get_attribute('href')
                # Извлечь ID из URL: /vacancy/123456 или https://hh.ru/vacancy/123456
                if '/vacancy/' in href:
                    vacancy_id = href.split('/vacancy/')[-1].split('?')[0]

            if not vacancy_id:
                return None

            # Название вакансии
            title_el = item.query_selector('[data-qa="negotiation-title"]')
            title = title_el.inner_text() if title_el else "Unknown"

            # Компания
            employer_el = item.query_selector('[data-qa="negotiation-employer"]')
            employer = employer_el.inner_text() if employer_el else "Unknown"

            # Статус отклика
            status = self._determine_status(item)

            return {
                "vacancy_id": vacancy_id,
                "title": title,
                "employer": employer,
                "status": status
            }

        except Exception as e:
            self.log(f"Ошибка парсинга элемента: {e}", "debug")
            return None

    def _determine_status(self, item) -> str:
        """Determine response status from item."""
        # HH.ru показывает статусы через разные индикаторы
        text = item.inner_text().lower()

        # Приглашение на собеседование
        if any(word in text for word in ['приглашение', 'собеседование', 'интервью', 'interview']):
            return 'invited'

        # Отказ
        if any(word in text for word in ['отказ', 'отклонен', 'rejected', 'не подходит']):
            return 'rejected'

        # Просмотрено работодателем
        if any(word in text for word in ['просмотрено', 'viewed', 'рассмотрено']):
            return 'viewed'

        # Статусы по data-qa атрибутам
        status_indicator = item.query_selector('[data-qa*="status"]')
        if status_indicator:
            status_text = status_indicator.inner_text().lower()
            if 'приглаш' in status_text or 'interview' in status_text:
                return 'invited'
            elif 'отказ' in status_text or 'reject' in status_text:
                return 'rejected'
            elif 'просмотр' in status_text or 'view' in status_text:
                return 'viewed'

        # По умолчанию - отправлено (applied)
        return 'applied'

    def _update_response_status(self, response: dict) -> bool:
        """Update response status in database."""
        if not self.db:
            return False

        vacancy_id = response["vacancy_id"]
        status = response["status"]

        # Проверить что отклик есть в БД
        if not self.db.is_already_applied(vacancy_id):
            self.log(f"Отклик {vacancy_id} не найден в БД", "debug")
            return False

        # Обновить статус
        self.db.update_application_status(vacancy_id, status)
        self.log(f"Обновлен статус: {response['title']} -> {status}", "debug")
        return True

    def _go_to_next_page(self) -> bool:
        """Navigate to next page of responses."""
        try:
            # Найти кнопку "Следующая страница"
            next_button = self.page.query_selector('[data-qa="pager-next"]')

            if not next_button:
                # Альтернативный селектор
                next_button = self.page.query_selector('a[rel="next"]')

            if next_button:
                next_button.click()
                time.sleep(random.uniform(1, 2))
                return True

            return False

        except Exception:
            return False

    def get_recent_updates(self, days: int = 7) -> list:
        """Get responses with recent status updates."""
        if not self.db:
            return []

        try:
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT vacancy_id, title, employer, status, applied_at, viewed_at, response_at
                FROM applications
                WHERE viewed_at IS NOT NULL
                   OR response_at IS NOT NULL
                ORDER BY COALESCE(response_at, viewed_at) DESC
                LIMIT 100
            """)

            results = []
            for row in cursor.fetchall():
                results.append({
                    "vacancy_id": row[0],
                    "title": row[1],
                    "employer": row[2],
                    "status": row[3],
                    "applied_at": row[4],
                    "viewed_at": row[5],
                    "response_at": row[6]
                })

            return results

        except Exception as e:
            self.log(f"Ошибка получения обновлений: {e}", "error")
            return []

    def get_conversion_stats(self) -> dict:
        """Calculate conversion statistics."""
        if not self.db:
            return {}

        try:
            stats = self.db.get_stats()
            total = stats.get('total_applications', 0)

            if total == 0:
                return {
                    "total": 0,
                    "viewed_rate": 0,
                    "invited_rate": 0,
                    "rejected_rate": 0
                }

            by_status = stats.get('by_status', {})
            viewed = by_status.get('viewed', 0)
            invited = by_status.get('invited', 0)
            rejected = by_status.get('rejected', 0)

            return {
                "total": total,
                "viewed": viewed,
                "invited": invited,
                "rejected": rejected,
                "viewed_rate": round(viewed / total * 100, 2),
                "invited_rate": round(invited / total * 100, 2),
                "rejected_rate": round(rejected / total * 100, 2)
            }

        except Exception as e:
            self.log(f"Ошибка расчета статистики: {e}", "error")
            return {}
