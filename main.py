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
{Fore.GREEN}[9]{Style.RESET_ALL} 🗑️  Очистить сессию
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

    # Фильтры
    if applier.filters:
        filter_stats = applier.filters.get_filter_stats()
        print(f"\n{Fore.CYAN}Фильтры:{Style.RESET_ALL}")
        print(f"  Черный список: {len(filter_stats.get('blacklist_companies', []))} компаний")
        print(f"  Белый список: {len(filter_stats.get('whitelist_companies', []))} компаний")

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
    parser.add_argument("--browser", choices=["chrome", "edge", "firefox", "auto"])
    parser.add_argument("--boost", action="store_true", help="Обновить резюме")
    parser.add_argument("--apply", action="store_true", help="Массовая рассылка")
    parser.add_argument("--max-apply", type=int, default=200)
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

    # CLI режимы
    if args.boost:
        run_resume_boost(booster)
        safe_cleanup()
        return

    if args.apply:
        params = {"_max_applications": args.max_apply}
        run_mass_apply(applier, params)
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
                log_and_print("Функция в разработке", "warning")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")
            elif choice == "6":
                log_and_print("Функция в разработке", "warning")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")
            elif choice == "7":
                if browser_manager.is_logged_in():
                    log_and_print("✓ Авторизован на HH.ru", "success")
                else:
                    log_and_print("✗ Не авторизован", "error")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")
            elif choice == "8":
                log_and_print("Функция в разработке", "warning")
                input(f"\n{Fore.YELLOW}Нажмите Enter...{Style.RESET_ALL}")
            elif choice == "9":
                browser_manager.clear_session()
                log_and_print("Сессия очищена", "success")
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
