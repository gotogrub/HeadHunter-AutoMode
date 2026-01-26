"""
HeadHunter Destroyer V2 - User-Friendly версия
Автоматизация поиска работы на HH.ru
"""

import sys
import signal
import argparse
import os
from datetime import datetime

from config import SERVER_MODE, IS_WINDOWS
from browser import BrowserManager
from resume_booster import ResumeBooster
from vacancy_applier import VacancyApplier
from database import Database
from filters import VacancyFilter, setup_default_filters
from cover_letters import CoverLetterManager
from ai_assistant import get_ai_assistant
from logger import setup_logger, get_logger
from response_tracker import ResponseTracker

# Telegram bot (опционально)
try:
    from telegram_bot import run_standalone_bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# Colorama
try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    class Fore:
        GREEN = YELLOW = RED = CYAN = MAGENTA = WHITE = BLUE = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = DIM = ""

# Global state
browser_manager = None
logger = None
shutdown_in_progress = False


def clear_screen():
    """Очистить экран."""
    os.system('cls' if IS_WINDOWS else 'clear')


def print_banner():
    """Баннер программы."""
    banner = f"""{Fore.CYAN}{Style.BRIGHT}
╔═══════════════════════════════════════════════════════╗
║     HeadHunter Destroyer - Автоматизация HH.ru        ║
╚═══════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
    print(banner)


def log_and_print(message, level="info"):
    """Логировать и выводить в консоль."""
    if logger:
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "debug":
            logger.debug(message)
        else:
            logger.info(message)

    colors = {
        "info": Fore.CYAN,
        "success": Fore.GREEN,
        "warning": Fore.YELLOW,
        "error": Fore.RED,
        "debug": Fore.WHITE + Style.DIM
    }

    color = colors.get(level, Fore.WHITE)
    print(f"{color}[•] {message}{Style.RESET_ALL}")


def print_menu():
    """Главное меню."""
    print(f"""
{Fore.GREEN}╔═══════════════════════════════════════════════════════╗
║                    ГЛАВНОЕ МЕНЮ                       ║
╚═══════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.GREEN}[1]{Style.RESET_ALL} 📄 Обновить все резюме
{Fore.GREEN}[2]{Style.RESET_ALL} 🚀 Массовая рассылка откликов
{Fore.GREEN}[3]{Style.RESET_ALL} 🔍 Поиск и отклик на вакансии (интерактивно)
{Fore.GREEN}[4]{Style.RESET_ALL} 📊 Статистика
{Fore.GREEN}[5]{Style.RESET_ALL} ⚙️  Настройки фильтров
{Fore.GREEN}[6]{Style.RESET_ALL} 💾 Экспорт данных
{Fore.GREEN}[7]{Style.RESET_ALL} 🔑 Проверить авторизацию
{Fore.GREEN}[8]{Style.RESET_ALL} 📝 Шаблоны писем
{Fore.GREEN}[9]{Style.RESET_ALL} 📬 Проверить отклики (статусы)
{Fore.GREEN}[10]{Style.RESET_ALL} 🗑️  Очистить сессию
{Fore.GREEN}[0]{Style.RESET_ALL} 🚪 Выход
""")
    return input(f"{Fore.GREEN}➤ Ваш выбор: {Style.RESET_ALL}").strip()


def format_salary(salary_from, salary_to):
    """Форматировать зарплату."""
    if salary_from and salary_to:
        return f"{salary_from:,} - {salary_to:,} ₽".replace(',', ' ')
    elif salary_from:
        return f"от {salary_from:,} ₽".replace(',', ' ')
    elif salary_to:
        return f"до {salary_to:,} ₽".replace(',', ' ')
    return "не указана"


def display_vacancy(vacancy, index=None):
    """Красиво отобразить вакансию."""
    prefix = f"{Fore.CYAN}[{index}]{Style.RESET_ALL} " if index is not None else ""

    title = vacancy.get('title', 'Без названия')
    employer = vacancy.get('employer', 'Неизвестно')
    salary = format_salary(vacancy.get('salary_from'), vacancy.get('salary_to'))
    url = vacancy.get('url', '')

    print(f"\n{prefix}{Fore.YELLOW}{Style.BRIGHT}{title}{Style.RESET_ALL}")
    print(f"    {Fore.WHITE}Компания:{Style.RESET_ALL} {employer}")
    print(f"    {Fore.GREEN}Зарплата:{Style.RESET_ALL} {salary}")
    if url:
        print(f"    {Fore.BLUE}Ссылка:{Style.RESET_ALL} https://hh.ru{url}")


def interactive_vacancy_selection(vacancies):
    """Интерактивный выбор вакансий для отклика."""
    if not vacancies:
        log_and_print("Вакансии не найдены", "warning")
        return []

    clear_screen()
    print_banner()
    print(f"\n{Fore.CYAN}{Style.BRIGHT}Найдено вакансий: {len(vacancies)}{Style.RESET_ALL}\n")

    # Показать первые 10
    display_count = min(10, len(vacancies))
    for i, vacancy in enumerate(vacancies[:display_count], 1):
        display_vacancy(vacancy, i)

    if len(vacancies) > display_count:
        print(f"\n{Fore.YELLOW}... и еще {len(vacancies) - display_count} вакансий{Style.RESET_ALL}")

    print(f"\n{Fore.GREEN}╔════════════════════════════════════════╗")
    print(f"║          ВЫБОР ДЕЙСТВИЯ                ║")
    print(f"╚════════════════════════════════════════╝{Style.RESET_ALL}")
    print(f"{Fore.GREEN}[a]{Style.RESET_ALL} Откликнуться на ВСЕ")
    print(f"{Fore.GREEN}[s]{Style.RESET_ALL} Выбрать вакансии по номерам (1,3,5)")
    print(f"{Fore.GREEN}[n]{Style.RESET_ALL} Показать следующие 10")
    print(f"{Fore.GREEN}[0]{Style.RESET_ALL} Отмена")

    choice = input(f"\n{Fore.GREEN}➤ Ваш выбор: {Style.RESET_ALL}").strip().lower()

    if choice == 'a':
        return vacancies
    elif choice == 's':
        numbers = input(f"{Fore.GREEN}➤ Введите номера через запятую: {Style.RESET_ALL}").strip()
        try:
            indices = [int(n.strip()) - 1 for n in numbers.split(',')]
            return [vacancies[i] for i in indices if 0 <= i < len(vacancies)]
        except:
            log_and_print("Неверный формат", "error")
            return []
    elif choice == 'n':
        # TODO: pagination
        return []
    else:
        return []


def run_resume_boost(booster):
    """Обновление резюме."""
    clear_screen()
    print_banner()
    print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ ОБНОВЛЕНИЕ РЕЗЮМЕ ═══{Style.RESET_ALL}\n")

    log_and_print("Проверка возможности обновления...")

    if not booster.can_update():
        mins = booster.minutes_until_next_update()
        log_and_print(f"⏰ HH.ru ограничивает обновления до 1 раза в 4 часа", "warning")
        log_and_print(f"⏰ Следующее обновление возможно через {mins} минут", "warning")
        input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")
        return

    log_and_print("Начинаю обновление резюме...", "info")

    try:
        results = booster.boost_all_resumes()

        success_count = len(results.get('success', []))
        failed_count = len(results.get('failed', []))

        print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ Результаты обновления:{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}Успешно обновлено:{Style.RESET_ALL} {success_count}")
        print(f"  {Fore.RED}Ошибок:{Style.RESET_ALL} {failed_count}")

        if results.get('success'):
            print(f"\n{Fore.GREEN}Обновленные резюме:{Style.RESET_ALL}")
            for title in results['success']:
                print(f"  ✓ {title}")

        if results.get('failed'):
            print(f"\n{Fore.RED}Ошибки:{Style.RESET_ALL}")
            for title, error in results['failed']:
                print(f"  ✗ {title}: {error}")
                log_and_print(f"Ошибка обновления {title}: {error}", "error")

        log_and_print(f"Обновление завершено. Успешно: {success_count}, Ошибок: {failed_count}", "success")

    except Exception as e:
        log_and_print(f"Критическая ошибка при обновлении: {e}", "error")
        print(f"\n{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")

    input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")


def run_mass_apply(applier, params=None):
    """Массовая рассылка."""
    clear_screen()
    print_banner()
    print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ МАССОВАЯ РАССЫЛКА ═══{Style.RESET_ALL}\n")

    if params:
        print(f"{Fore.CYAN}Параметры поиска:{Style.RESET_ALL}")
        for key, value in params.items():
            if not key.startswith('_'):
                print(f"  • {key}: {value}")
        print()

    max_apps = params.pop("_max_applications", 200) if params else 200

    log_and_print(f"Начинаю поиск и рассылку (макс. {max_apps} откликов)...", "info")

    try:
        # Счетчики для отображения
        applied = 0
        skipped = 0
        filtered = 0

        def on_vacancy(title, employer, status):
            nonlocal applied, skipped, filtered
            if status == "applied":
                applied += 1
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} [{applied}] {title[:50]} @ {employer[:30]}")
            elif status == "skipped":
                skipped += 1
                log_and_print(f"⊘ Пропущено: {title[:50]}", "debug")
            elif status == "filtered":
                filtered += 1
                log_and_print(f"⊗ Отфильтровано: {title[:50]}", "debug")

        def on_page(page_num, count):
            log_and_print(f"Страница {page_num}: найдено {count} вакансий", "debug")

        callbacks = {
            "on_vacancy": on_vacancy,
            "on_page": on_page
        }

        results = applier.mass_apply(
            search_params=params,
            max_applications=max_apps,
            callbacks=callbacks
        )

        print(f"\n{Fore.GREEN}{Style.BRIGHT}═══ ИТОГИ РАССЫЛКИ ═══{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}✓ Откликов отправлено:{Style.RESET_ALL} {len(results['applied'])}")
        print(f"  {Fore.YELLOW}⊘ Пропущено:{Style.RESET_ALL} {len(results['skipped'])}")
        print(f"  {Fore.CYAN}⊗ Отфильтровано:{Style.RESET_ALL} {len(results.get('filtered', []))}")
        print(f"  {Fore.BLUE}📄 Страниц просмотрено:{Style.RESET_ALL} {results.get('pages_scanned', 0)}")

        log_and_print(
            f"Рассылка завершена. Откликов: {len(results['applied'])}, "
            f"Пропущено: {len(results['skipped'])}, "
            f"Отфильтровано: {len(results.get('filtered', []))}",
            "success"
        )

    except Exception as e:
        log_and_print(f"Ошибка при рассылке: {e}", "error")
        print(f"\n{Fore.RED}✗ Ошибка: {e}{Style.RESET_ALL}")

    input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")


def run_interactive_apply(applier):
    """Интерактивный поиск и отклик."""
    clear_screen()
    print_banner()
    print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ ИНТЕРАКТИВНЫЙ ПОИСК ═══{Style.RESET_ALL}\n")

    # Параметры поиска
    print(f"{Fore.CYAN}Введите параметры поиска:{Style.RESET_ALL}")
    query = input(f"  Запрос (например, 'python developer'): ").strip()

    print(f"\n  Регион: {Fore.WHITE}1{Style.RESET_ALL}=Москва, {Fore.WHITE}2{Style.RESET_ALL}=СПб, {Fore.WHITE}113{Style.RESET_ALL}=Россия")
    area = input(f"  ID региона [1]: ").strip() or "1"

    params = {}
    if query:
        params["text"] = query
    params["area"] = area

    log_and_print("Поиск вакансий...", "info")

    # Получить вакансии с первой страницы
    search_url = applier.build_search_url(params)
    applier.page.goto(search_url, wait_until="domcontentloaded")

    import time
    import random
    time.sleep(random.uniform(1, 2))

    vacancies = applier.get_vacancies_on_page()

    if not vacancies:
        log_and_print("Вакансии не найдены", "warning")
        input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")
        return

    # Интерактивный выбор
    selected = interactive_vacancy_selection(vacancies)

    if not selected:
        log_and_print("Отклики отменены", "info")
        input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")
        return

    # Откликнуться на выбранные
    clear_screen()
    print_banner()
    print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ ОТПРАВКА ОТКЛИКОВ ═══{Style.RESET_ALL}\n")

    applied_count = 0
    for i, vacancy in enumerate(selected, 1):
        print(f"\n[{i}/{len(selected)}] {vacancy['title'][:50]}")

        status_result, reason = applier.apply_to_vacancy(vacancy)

        if status_result == "applied":
            applied_count += 1
            print(f"  {Fore.GREEN}✓ Отклик отправлен{Style.RESET_ALL}")
            log_and_print(f"Отклик: {vacancy['title']} @ {vacancy['employer']}", "success")
        elif status_result == "skipped":
            print(f"  {Fore.YELLOW}⊘ Пропущено: {reason}{Style.RESET_ALL}")
        elif status_result == "filtered":
            print(f"  {Fore.CYAN}⊗ Отфильтровано: {reason}{Style.RESET_ALL}")
        else:
            print(f"  {Fore.RED}✗ Ошибка: {reason}{Style.RESET_ALL}")

        # Задержка между откликами
        if status_result == "applied" and i < len(selected):
            time.sleep(random.uniform(2, 4))

    print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ Завершено!{Style.RESET_ALL}")
    print(f"  Откликов отправлено: {applied_count} из {len(selected)}")

    input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")


def show_stats(applier, db):
    """Показать статистику."""
    clear_screen()
    print_banner()
    print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ СТАТИСТИКА ═══{Style.RESET_ALL}\n")

    # Статистика сессии
    print(f"{Fore.CYAN}Текущая сессия:{Style.RESET_ALL}")
    print(f"  Откликов: {applier.applied_count}")
    print(f"  Пропущено: {applier.skipped_count}")
    print(f"  Отфильтровано: {applier.filtered_count}")

    # Статистика из БД
    db_stats = db.get_stats()
    print(f"\n{Fore.CYAN}Всего (база данных):{Style.RESET_ALL}")
    print(f"  Всего откликов: {db_stats.get('total_applications', 0)}")
    print(f"  Сегодня: {db_stats.get('today_applications', 0)}")
    print(f"  За неделю: {db_stats.get('week_applications', 0)}")

    # Статусы откликов
    by_status = db_stats.get('by_status', {})
    if by_status:
        print(f"\n{Fore.CYAN}По статусам:{Style.RESET_ALL}")
        print(f"  📤 Отправлено:    {by_status.get('applied', 0)}")
        print(f"  📖 Просмотрено:   {by_status.get('viewed', 0)}")
        print(f"  ✉️  Приглашений:   {by_status.get('invited', 0)}")
        print(f"  ❌ Отказов:       {by_status.get('rejected', 0)}")

        # Конверсия
        total = db_stats.get('total_applications', 0)
        if total > 0:
            viewed_rate = round(by_status.get('viewed', 0) / total * 100, 1)
            invited_rate = round(by_status.get('invited', 0) / total * 100, 1)
            rejected_rate = round(by_status.get('rejected', 0) / total * 100, 1)

            print(f"\n{Fore.CYAN}Конверсия:{Style.RESET_ALL}")
            print(f"  Просмотрено:  {Fore.BLUE}{viewed_rate}%{Style.RESET_ALL}")
            print(f"  Приглашений:  {Fore.GREEN}{invited_rate}%{Style.RESET_ALL}")
            print(f"  Отказов:      {Fore.RED}{rejected_rate}%{Style.RESET_ALL}")

    # Фильтры
    if applier.filters:
        filter_stats = applier.filters.get_filter_stats()
        print(f"\n{Fore.CYAN}Фильтры:{Style.RESET_ALL}")
        print(f"  Черный список: {len(filter_stats.get('blacklist_companies', []))} компаний")
        print(f"  Белый список: {len(filter_stats.get('whitelist_companies', []))} компаний")

    input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")


def manage_filters(filters):
    """Управление фильтрами."""
    while True:
        clear_screen()
        print_banner()
        print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ УПРАВЛЕНИЕ ФИЛЬТРАМИ ═══{Style.RESET_ALL}\n")

        filter_stats = filters.get_filter_stats()

        print(f"{Fore.CYAN}Текущие фильтры:{Style.RESET_ALL}")
        print(f"  Черный список компаний: {len(filter_stats['blacklist_companies'])}")
        if filter_stats['blacklist_companies']:
            for company in list(filter_stats['blacklist_companies'])[:5]:
                print(f"    • {company}")
            if len(filter_stats['blacklist_companies']) > 5:
                print(f"    ... и еще {len(filter_stats['blacklist_companies']) - 5}")

        print(f"\n  Белый список компаний: {len(filter_stats['whitelist_companies'])}")
        if filter_stats['whitelist_companies']:
            for company in list(filter_stats['whitelist_companies'])[:5]:
                print(f"    • {company}")

        print(f"\n  Черный список слов: {len(filter_stats['blacklist_words'])}")
        if filter_stats['blacklist_words']:
            words = ', '.join(list(filter_stats['blacklist_words'])[:10])
            print(f"    {words}")

        if filter_stats['min_salary']:
            print(f"\n  Мин. зарплата: {filter_stats['min_salary']:,}₽".replace(',', ' '))
        if filter_stats['max_salary']:
            print(f"  Макс. зарплата: {filter_stats['max_salary']:,}₽".replace(',', ' '))

        print(f"\n{Fore.GREEN}╔═══════════════════════════════════════╗")
        print(f"║              ДЕЙСТВИЯ                 ║")
        print(f"╚═══════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[1]{Style.RESET_ALL} Добавить компанию в черный список")
        print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Добавить компанию в белый список")
        print(f"{Fore.GREEN}[3]{Style.RESET_ALL} Добавить слово в черный список")
        print(f"{Fore.GREEN}[4]{Style.RESET_ALL} Настроить фильтр зарплаты")
        print(f"{Fore.GREEN}[5]{Style.RESET_ALL} Очистить черный список компаний")
        print(f"{Fore.GREEN}[0]{Style.RESET_ALL} Назад")

        choice = input(f"\n{Fore.GREEN}➤ Ваш выбор: {Style.RESET_ALL}").strip()

        if choice == "1":
            company = input(f"  Название компании: ").strip()
            if company:
                filters.add_blacklist_company(company)
                log_and_print(f"Компания '{company}' добавлена в черный список", "success")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")

        elif choice == "2":
            company = input(f"  Название компании: ").strip()
            if company:
                filters.add_whitelist_company(company)
                log_and_print(f"Компания '{company}' добавлена в белый список", "success")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")

        elif choice == "3":
            word = input(f"  Слово для черного списка: ").strip()
            if word:
                filters.add_blacklist_word(word)
                log_and_print(f"Слово '{word}' добавлено в черный список", "success")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")

        elif choice == "4":
            print(f"\n{Fore.CYAN}Настройка фильтра зарплаты:{Style.RESET_ALL}")
            min_sal = input(f"  Минимальная зарплата [пусто=любая]: ").strip()
            max_sal = input(f"  Максимальная зарплата [пусто=любая]: ").strip()
            require = input(f"  Требовать указание зарплаты? (y/n) [n]: ").strip().lower() == 'y'

            filters.set_salary_filter(
                min_salary=int(min_sal) if min_sal.isdigit() else None,
                max_salary=int(max_sal) if max_sal.isdigit() else None,
                require=require
            )
            log_and_print("Фильтр зарплаты обновлен", "success")
            input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")

        elif choice == "5":
            confirm = input(f"  Очистить черный список компаний? (y/n): ").strip().lower()
            if confirm == 'y':
                # TODO: добавить метод clear в filters
                log_and_print("Черный список очищен", "success")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")

        elif choice == "0":
            break


def export_data(db):
    """Экспорт данных в CSV."""
    clear_screen()
    print_banner()
    print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ ЭКСПОРТ ДАННЫХ ═══{Style.RESET_ALL}\n")

    filepath = input(f"  Путь для экспорта [applications.csv]: ").strip() or "applications.csv"

    log_and_print(f"Экспорт данных в {filepath}...", "info")

    try:
        db.export_to_csv(filepath)
        log_and_print(f"✓ Данные экспортированы в {filepath}", "success")

        # Показать что экспортировано
        db_stats = db.get_stats()
        print(f"\n{Fore.CYAN}Экспортировано:{Style.RESET_ALL}")
        print(f"  Откликов: {db_stats.get('total_applications', 0)}")

    except Exception as e:
        log_and_print(f"Ошибка экспорта: {e}", "error")

    input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")


def manage_cover_letters(cover_letters):
    """Управление шаблонами сопроводительных писем."""
    while True:
        clear_screen()
        print_banner()
        print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ ШАБЛОНЫ СОПРОВОДИТЕЛЬНЫХ ПИСЕМ ═══{Style.RESET_ALL}\n")

        templates = cover_letters.get_all_templates()

        if not templates:
            log_and_print("Нет доступных шаблонов", "warning")
        else:
            for i, t in enumerate(templates, 1):
                default_mark = f" {Fore.GREEN}[ПО УМОЛЧАНИЮ]{Style.RESET_ALL}" if t["is_default"] else ""
                print(f"{Fore.CYAN}[{i}]{Style.RESET_ALL} {t['name']}{default_mark} (использовано {t['use_count']}x)")

        print(f"\n{Fore.GREEN}╔═══════════════════════════════════════╗")
        print(f"║              ДЕЙСТВИЯ                 ║")
        print(f"╚═══════════════════════════════════════╝{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[a]{Style.RESET_ALL} Добавить новый шаблон")
        print(f"{Fore.GREEN}[v]{Style.RESET_ALL} Просмотреть шаблон")
        print(f"{Fore.GREEN}[d]{Style.RESET_ALL} Установить по умолчанию")
        print(f"{Fore.GREEN}[p]{Style.RESET_ALL} Показать доступные плейсхолдеры")
        print(f"{Fore.GREEN}[0]{Style.RESET_ALL} Назад")

        choice = input(f"\n{Fore.GREEN}➤ Ваш выбор: {Style.RESET_ALL}").strip().lower()

        if choice == "a":
            print(f"\n{Fore.CYAN}Создание нового шаблона:{Style.RESET_ALL}")
            name = input(f"  Название шаблона: ").strip()
            if not name:
                continue

            print(f"\n  Введите текст шаблона (пустая строка = конец):")
            print(f"  {Fore.YELLOW}Доступные плейсхолдеры: {{company}}, {{position}}, {{salary}}, {{name}}{Style.RESET_ALL}\n")

            lines = []
            while True:
                line = input("  ")
                if line == "":
                    break
                lines.append(line)

            if lines:
                content = "\n".join(lines)
                cover_letters.add_template(name, content)
                log_and_print(f"Шаблон '{name}' добавлен", "success")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")

        elif choice == "v":
            if not templates:
                continue

            num = input(f"  Номер шаблона для просмотра: ").strip()
            if num.isdigit() and 0 < int(num) <= len(templates):
                t = templates[int(num) - 1]
                print(f"\n{Fore.CYAN}╔═══ {t['name']} ═══╗{Style.RESET_ALL}")
                print(t["content"])
                print(f"{Fore.CYAN}╚{'═' * (len(t['name']) + 8)}╝{Style.RESET_ALL}")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")

        elif choice == "d":
            if not templates:
                continue

            num = input(f"  Номер шаблона для установки по умолчанию: ").strip()
            if num.isdigit() and 0 < int(num) <= len(templates):
                template_name = templates[int(num) - 1]["name"]
                cover_letters.set_default(template_name)
                log_and_print(f"Шаблон '{template_name}' установлен по умолчанию", "success")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")

        elif choice == "p":
            print(f"\n{Fore.CYAN}Доступные плейсхолдеры:{Style.RESET_ALL}")
            print(f"  {{company}}   - Название компании")
            print(f"  {{position}}  - Название вакансии")
            print(f"  {{salary}}    - Зарплата")
            print(f"  {{name}}      - Ваше имя")
            print(f"  {{date}}      - Текущая дата")
            input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")

        elif choice == "0":
            break


def check_responses(tracker):
    """Проверка статусов откликов."""
    clear_screen()
    print_banner()
    print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ ПРОВЕРКА ОТКЛИКОВ ═══{Style.RESET_ALL}\n")

    log_and_print("Начинаю проверку статусов откликов на HH.ru...")
    log_and_print("Это может занять несколько минут...\n", "warning")

    stats = tracker.check_all_responses()

    # Результаты
    print(f"\n{Fore.GREEN}╔═══════════════════════════════════════════════════════╗")
    print(f"║              РЕЗУЛЬТАТЫ ПРОВЕРКИ                      ║")
    print(f"╚═══════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")

    print(f"Всего откликов проверено: {Fore.CYAN}{stats['total']}{Style.RESET_ALL}")
    print(f"Обновлено статусов:       {Fore.GREEN}{stats['updated']}{Style.RESET_ALL}\n")

    print(f"Из них:")
    print(f"  {Fore.BLUE}📖 Просмотрено:{Style.RESET_ALL}      {stats['viewed']}")
    print(f"  {Fore.GREEN}✉️  Приглашений:{Style.RESET_ALL}     {stats['invited']}")
    print(f"  {Fore.RED}❌ Отказов:{Style.RESET_ALL}          {stats['rejected']}")

    if stats['errors'] > 0:
        print(f"\n{Fore.YELLOW}⚠️  Ошибок: {stats['errors']}{Style.RESET_ALL}")

    # Показать conversion stats
    print(f"\n{Fore.CYAN}Конверсия откликов:{Style.RESET_ALL}")
    conversion = tracker.get_conversion_stats()
    if conversion:
        print(f"  Просмотрено:  {Fore.BLUE}{conversion['viewed_rate']}%{Style.RESET_ALL} ({conversion['viewed']}/{conversion['total']})")
        print(f"  Приглашений:  {Fore.GREEN}{conversion['invited_rate']}%{Style.RESET_ALL} ({conversion['invited']}/{conversion['total']})")
        print(f"  Отказов:      {Fore.RED}{conversion['rejected_rate']}%{Style.RESET_ALL} ({conversion['rejected']}/{conversion['total']})")

    # Показать последние обновления
    recent = tracker.get_recent_updates(days=7)
    if recent:
        print(f"\n{Fore.CYAN}Последние обновления (за 7 дней):{Style.RESET_ALL}\n")
        for i, resp in enumerate(recent[:5], 1):
            status_icon = {
                'viewed': '📖',
                'invited': '✉️',
                'rejected': '❌',
                'applied': '📤'
            }.get(resp['status'], '•')

            status_color = {
                'viewed': Fore.BLUE,
                'invited': Fore.GREEN,
                'rejected': Fore.RED,
                'applied': Fore.YELLOW
            }.get(resp['status'], Fore.WHITE)

            print(f"  {i}. {status_icon} {status_color}{resp['status'].upper()}{Style.RESET_ALL} - {resp['title'][:50]}")
            print(f"     {Fore.DIM}{resp['employer']}{Style.RESET_ALL}")

    log_and_print("\nПроверка завершена!", "success")
    input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")


def select_browser():
    """Выбор браузера."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}═══ ВЫБОР БРАУЗЕРА ═══{Style.RESET_ALL}\n")
    print(f"{Fore.GREEN}[1]{Style.RESET_ALL} Chrome (Google Chrome)")
    print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Edge (Microsoft Edge)")
    print(f"{Fore.GREEN}[3]{Style.RESET_ALL} Firefox (Mozilla Firefox)")
    print(f"{Fore.GREEN}[4]{Style.RESET_ALL} Авто (попробовать все по порядку)")

    choice = input(f"\n{Fore.GREEN}➤ Выберите [4]: {Style.RESET_ALL}").strip()

    browser_map = {"1": "chrome", "2": "edge", "3": "firefox", "4": "auto"}
    return browser_map.get(choice, "auto")


def parse_args():
    """Аргументы командной строки."""
    parser = argparse.ArgumentParser(description="HeadHunter Destroyer V2")
    parser.add_argument("--browser", choices=["chrome", "edge", "firefox", "auto"],
                        help="Выбор браузера")
    parser.add_argument("--boost", action="store_true",
                        help="Обновить резюме (одноразово)")
    parser.add_argument("--apply", action="store_true",
                        help="Массовая рассылка откликов")
    parser.add_argument("--apply-query", type=str,
                        help="Поисковый запрос для вакансий")
    parser.add_argument("--max-apply", type=int, default=200,
                        help="Максимальное количество откликов")
    parser.add_argument("--cover-letter", action="store_true",
                        help="Использовать сопроводительные письма")
    parser.add_argument("--ai-letters", action="store_true",
                        help="Генерировать письма через AI")
    parser.add_argument("--daemon", action="store_true",
                        help="Daemon режим (бесконечный цикл)")
    parser.add_argument("--telegram", action="store_true",
                        help="Запустить Telegram бота")
    parser.add_argument("--profile", type=str,
                        help="Имя профиля для мультиаккаунта (default, work, etc.)")
    parser.add_argument("--check-responses", action="store_true",
                        help="Проверить статусы откликов")
    return parser.parse_args()


def safe_cleanup():
    """Безопасная очистка ресурсов."""
    global shutdown_in_progress

    if shutdown_in_progress:
        return

    shutdown_in_progress = True

    log_and_print("Завершение работы...", "info")

    if logger:
        try:
            logger.log_session_end()
        except:
            pass

    if browser_manager:
        try:
            browser_manager.stop()
        except:
            pass


def main():
    """Главная функция."""
    global browser_manager, logger, shutdown_in_progress

    args = parse_args()

    # Multi-account support через профили
    if args.profile:
        profile_name = args.profile
        # Установить профиль в переменную окружения для browser.py
        os.environ["HH_PROFILE"] = profile_name
        print(f"{Fore.CYAN}Использование профиля: {profile_name}{Style.RESET_ALL}")

    # Telegram бот (не требует браузера)
    if args.telegram:
        if not TELEGRAM_AVAILABLE:
            print(f"{Fore.RED}Ошибка: Telegram bot не доступен. Установите: pip install python-telegram-bot{Style.RESET_ALL}")
            sys.exit(1)

        print(f"{Fore.CYAN}Запуск Telegram бота...{Style.RESET_ALL}")
        run_standalone_bot()
        return

    # Логгер
    logger = setup_logger()
    logger.log_session_start()

    # Выбор браузера
    if not args.browser and not (args.boost or args.apply):
        clear_screen()
        print_banner()
        selected_browser = select_browser()
    else:
        selected_browser = args.browser or "auto"

    clear_screen()
    print_banner()

    log_and_print("Инициализация базы данных...")
    db = Database()
    setup_default_filters(db)

    filters = VacancyFilter(db)
    cover_letters = CoverLetterManager(db)
    ai_assistant = get_ai_assistant(db)

    if ai_assistant.is_enabled():
        log_and_print(f"AI помощник активен: {ai_assistant.provider} ({ai_assistant.model})", "success")

    # Signal handler - ИСПРАВЛЕН
    def signal_handler(sig, frame):
        if not shutdown_in_progress:
            print(f"\n\n{Fore.YELLOW}Прерывание пользователем...{Style.RESET_ALL}")
            safe_cleanup()
            sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Запуск браузера
    log_and_print(f"Запуск браузера ({selected_browser})...")
    browser_manager = BrowserManager(browser=selected_browser)

    try:
        page = browser_manager.start(use_existing_session=True)
        log_and_print("Браузер запущен", "success")
    except Exception as e:
        log_and_print(f"Ошибка запуска браузера: {e}", "error")
        if IS_WINDOWS:
            log_and_print("Закройте все окна браузера и попробуйте снова", "warning")
        safe_cleanup()
        sys.exit(1)

    # Проверка авторизации
    log_and_print("Проверка авторизации...")
    if browser_manager.is_logged_in():
        log_and_print("✓ Авторизация успешна!", "success")
    else:
        log_and_print("Требуется авторизация на HH.ru", "warning")
        browser_manager.wait_for_login()

    # Инициализация модулей
    booster = ResumeBooster(page)
    applier = VacancyApplier(
        page,
        db=db,
        filters=filters,
        cover_letters=cover_letters,
        ai_assistant=ai_assistant,
        logger=logger
    )
    tracker = ResponseTracker(page, db=db, logger=logger)

    # CLI режимы
    if args.boost:
        run_resume_boost(booster)
        safe_cleanup()
        return

    if args.apply:
        params = {"_max_applications": args.max_apply}

        # Поисковый запрос
        if args.apply_query:
            params["text"] = args.apply_query

        # Cover letters
        if args.cover_letter:
            applier.use_cover_letter = True
            log_and_print("Включены сопроводительные письма (шаблоны)", "info")

        # AI letters
        if args.ai_letters:
            if ai_assistant.is_enabled():
                applier.use_ai_letters = True
                log_and_print(f"Включена AI-генерация писем ({ai_assistant.provider})", "info")
            else:
                log_and_print("AI помощник не доступен, используются обычные шаблоны", "warning")
                applier.use_cover_letter = True

        run_mass_apply(applier, params)
        safe_cleanup()
        return

    if args.check_responses:
        log_and_print("Проверка статусов откликов...")
        stats = tracker.check_all_responses()

        log_and_print(f"\nРезультаты: проверено {stats['total']}, обновлено {stats['updated']}", "info")
        log_and_print(f"Просмотрено: {stats['viewed']}, Приглашений: {stats['invited']}, Отказов: {stats['rejected']}", "info")

        conversion = tracker.get_conversion_stats()
        if conversion and conversion['total'] > 0:
            log_and_print(f"\nКонверсия: просмотрено {conversion['viewed_rate']}%, приглашений {conversion['invited_rate']}%", "success")

        safe_cleanup()
        return

    # Daemon режим
    if args.daemon:
        log_and_print("Запуск в daemon режиме...", "info")
        log_and_print("Бот будет обновлять резюме каждые 4 часа и искать новые вакансии", "info")

        import time

        try:
            while not shutdown_in_progress:
                # Обновить резюме
                log_and_print("\n=== Обновление резюме ===", "info")
                run_resume_boost(booster)

                # Массовая рассылка
                log_and_print("\n=== Массовая рассылка ===", "info")
                params = {
                    "_max_applications": args.max_apply,
                    "text": args.apply_query if args.apply_query else ""
                }

                if args.cover_letter:
                    applier.use_cover_letter = True
                if args.ai_letters and ai_assistant.is_enabled():
                    applier.use_ai_letters = True

                run_mass_apply(applier, params)

                # Ждать 4 часа
                log_and_print("\n=== Следующий запуск через 4 часа ===", "info")
                time.sleep(4 * 60 * 60)  # 4 часа

        except KeyboardInterrupt:
            log_and_print("\nDaemon режим остановлен", "warning")
        finally:
            safe_cleanup()
        return

    # Интерактивный режим
    while not shutdown_in_progress:
        try:
            clear_screen()
            print_banner()
            choice = print_menu()

            if choice == "1":
                run_resume_boost(booster)
            elif choice == "2":
                run_mass_apply(applier)
            elif choice == "3":
                run_interactive_apply(applier)
            elif choice == "4":
                show_stats(applier, db)
            elif choice == "5":
                manage_filters(filters)
            elif choice == "6":
                export_data(db)
            elif choice == "7":
                if browser_manager.is_logged_in():
                    log_and_print("✓ Авторизован на HH.ru", "success")
                else:
                    log_and_print("✗ Не авторизован", "error")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")
            elif choice == "8":
                manage_cover_letters(cover_letters)
            elif choice == "9":
                check_responses(tracker)
            elif choice == "10":
                confirm = input(f"\n{Fore.YELLOW}Очистить сессию? Потребуется повторный вход. (y/n): {Style.RESET_ALL}").strip().lower()
                if confirm == 'y':
                    browser_manager.clear_session()
                    log_and_print("Сессия очищена. Перезапустите программу.", "success")
                    input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")
            elif choice == "0":
                break
            else:
                log_and_print("Неверный выбор", "warning")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            log_and_print(f"Ошибка: {e}", "error")
            input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")

    # Завершение
    safe_cleanup()
    print(f"\n{Fore.GREEN}До свидания!{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
