"""
HeadHunter Destroyer - Главный файл
Автоматизация поиска работы на HH.ru

Режимы:
- Desktop Mode (Windows/Linux с GUI): Видимый браузер
- Server Mode (Linux headless): TUI интерфейс, headless браузер

CLI флаги:
  --daemon      Демон режим (авто boost + apply циклом)
  --boost       Разовое обновление резюме
  --apply       Разовая массовая рассылка
  --telegram    Запуск с Telegram ботом
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

# Import appropriate UI
if SERVER_MODE:
    from tui import TUI
    ui = TUI()
else:
    try:
        from colorama import init, Fore, Style
        init()
    except ImportError:
        class Fore:
            GREEN = YELLOW = RED = CYAN = MAGENTA = WHITE = RESET = ""
        class Style:
            BRIGHT = RESET_ALL = ""
    ui = None


def clear_screen():
    """Очистить экран консоли."""
    os.system('cls' if IS_WINDOWS else 'clear')


def print_banner():
    """Вывести баннер приложения."""
    if SERVER_MODE:
        ui.print_banner()
    else:
        banner = f"""
{Fore.CYAN}{Style.BRIGHT}
  _   _ _   _   ____            _
 | | | | | | | |  _ \\  ___  ___| |_ _ __ ___  _   _  ___ _ __
 | |_| | |_| | | | | |/ _ \\/ __| __| '__/ _ \\| | | |/ _ \\ '__|
 |  _  |  _  | | |_| |  __/\\__ \\ |_| | | (_) | |_| |  __/ |
 |_| |_|_| |_| |____/ \\___||___/\\__|_|  \\___/ \\__, |\\___|_|
                                              |___/
{Style.RESET_ALL}
{Fore.YELLOW}  Автоматизация поиска работы на HeadHunter{Style.RESET_ALL}
{Fore.WHITE}  ==========================================={Style.RESET_ALL}
"""
        print(banner)


def print_menu():
    """Вывести главное меню."""
    if SERVER_MODE:
        return ui.print_menu()
    else:
        print(f"""
{Fore.GREEN}[1]{Style.RESET_ALL} Обновить все резюме
{Fore.GREEN}[2]{Style.RESET_ALL} Массовая рассылка откликов
{Fore.GREEN}[3]{Style.RESET_ALL} Рассылка с настройкой поиска
{Fore.GREEN}[4]{Style.RESET_ALL} Показать статистику
{Fore.GREEN}[5]{Style.RESET_ALL} Управление фильтрами (черный/белый список)
{Fore.GREEN}[6]{Style.RESET_ALL} Экспорт данных в CSV
{Fore.GREEN}[7]{Style.RESET_ALL} Проверить авторизацию
{Fore.GREEN}[8]{Style.RESET_ALL} Очистить сессию (выйти)
{Fore.GREEN}[9]{Style.RESET_ALL} Шаблоны сопроводительных писем
{Fore.GREEN}[0]{Style.RESET_ALL} Выход
""")
        return input(f"{Fore.GREEN}Выберите опцию: {Style.RESET_ALL}").strip()


def get_search_params():
    """Получить параметры поиска от пользователя."""
    if SERVER_MODE:
        return ui.get_search_params()

    params = {}
    print(f"\n{Fore.CYAN}=== Параметры поиска ==={Style.RESET_ALL}")

    query = input("  Поисковый запрос [пусто]: ").strip()
    if query:
        params["text"] = query

    print("  Регион: 1=Москва, 2=СПб, 113=Россия")
    area = input("  ID региона [1]: ").strip()
    params["area"] = area if area else "1"

    print("  Опыт: noExperience, between1And3, between3And6, moreThan6")
    exp = input("  Опыт [любой]: ").strip()
    if exp:
        params["experience"] = exp

    print("  График: fullDay, shift, flexible, remote, flyInFlyOut")
    schedule = input("  График [любой]: ").strip()
    if schedule:
        params["schedule"] = schedule

    max_apps = input("  Макс. откликов [200]: ").strip()
    if max_apps and max_apps.isdigit():
        params["_max_applications"] = int(max_apps)

    return params


def status(message: str, status_type: str = "info"):
    """Вывести статусное сообщение."""
    logger = get_logger()

    # Логируем
    if status_type == "error":
        logger.error(message)
    elif status_type == "warning":
        logger.warning(message)
    else:
        logger.info(message)

    # Выводим в консоль
    if SERVER_MODE:
        ui.status(message, status_type)
    else:
        colors = {
            "info": Fore.CYAN,
            "success": Fore.GREEN,
            "warning": Fore.YELLOW,
            "error": Fore.RED,
        }
        color = colors.get(status_type, Fore.WHITE)
        print(f"{color}[*] {message}{Style.RESET_ALL}")


def run_resume_boost(booster: ResumeBooster):
    """Запустить обновление резюме."""
    logger = get_logger()
    status("Запуск обновления резюме...", "info")

    if not booster.can_update():
        mins = booster.minutes_until_next_update()
        status(f"HH.ru ограничивает обновления до 1 раза в 4 часа. Следующее обновление через {mins} мин.", "warning")
        return

    try:
        results = booster.boost_all_resumes(callback=ui.log_resume if SERVER_MODE else None)

        success_count = len(results['success'])
        failed_count = len(results['failed'])

        for resume_title in results['success']:
            logger.log_resume_update("", resume_title, "success")

        status(f"Обновление завершено! Успешно: {success_count}, Ошибок: {failed_count}", "success")
    except Exception as e:
        logger.error(f"Ошибка при обновлении резюме: {e}")
        status(f"Ошибка: {e}", "error")


def run_mass_apply(applier: VacancyApplier, params: dict = None):
    """Запустить массовую рассылку откликов."""
    logger = get_logger()
    status("Запуск массовой рассылки...", "info")

    max_apps = params.pop("_max_applications", None) if params else None

    callbacks = None
    if SERVER_MODE:
        callbacks = {
            "on_vacancy": ui.log_vacancy,
            "on_page": ui.log_page,
        }

    try:
        results = applier.mass_apply(search_params=params, max_applications=max_apps, callbacks=callbacks)

        # Summary
        applied_count = len(results['applied'])
        skipped_count = len(results['skipped'])
        filtered_count = len(results.get('filtered', []))

        msg = f"Откликов: {applied_count}, Пропущено: {skipped_count}"
        if filtered_count > 0:
            msg += f", Отфильтровано: {filtered_count}"

        status(msg, "success")

    except Exception as e:
        logger.error(f"Ошибка при массовой рассылке: {e}")
        status(f"Ошибка: {e}", "error")


def show_stats(applier: VacancyApplier, booster: ResumeBooster, db: Database):
    """Показать статистику."""
    print(f"\n{Fore.CYAN}=== Статистика сессии ==={Style.RESET_ALL}")
    print(f"  Откликов за сессию: {applier.applied_count}")
    print(f"  Пропущено: {applier.skipped_count}")
    print(f"  Отфильтровано: {applier.filtered_count}")

    print(f"\n{Fore.CYAN}=== Статистика из БД ==={Style.RESET_ALL}")
    db_stats = db.get_stats()
    print(f"  Всего откликов: {db_stats.get('total_applications', 0)}")
    print(f"  Сегодня: {db_stats.get('today_applications', 0)}")
    print(f"  За неделю: {db_stats.get('week_applications', 0)}")

    print(f"\n{Fore.CYAN}=== Фильтры ==={Style.RESET_ALL}")
    filter_stats = applier.filters.get_filter_stats() if applier.filters else {}
    print(f"  Компаний в черном списке: {len(filter_stats.get('blacklist_companies', []))}")
    print(f"  Компаний в белом списке: {len(filter_stats.get('whitelist_companies', []))}")

    if booster.last_update_time:
        print(f"\n{Fore.CYAN}=== Резюме ==={Style.RESET_ALL}")
        print(f"  Последнее обновление: {booster.last_update_time.strftime('%H:%M:%S')}")
        print(f"  Следующее обновление через: {booster.minutes_until_next_update()} мин")


def manage_filters(filters: VacancyFilter):
    """Управление фильтрами."""
    if SERVER_MODE:
        while ui.manage_filters_menu(filters):
            pass
        return

    while True:
        clear_screen()
        print_banner()
        print(f"\n{Fore.CYAN}=== Управление фильтрами ==={Style.RESET_ALL}")
        print(f"{Fore.GREEN}[1]{Style.RESET_ALL} Добавить компанию в черный список")
        print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Добавить компанию в белый список")
        print(f"{Fore.GREEN}[3]{Style.RESET_ALL} Добавить слово в черный список")
        print(f"{Fore.GREEN}[4]{Style.RESET_ALL} Показать текущие фильтры")
        print(f"{Fore.GREEN}[5]{Style.RESET_ALL} Настроить фильтр зарплаты")
        print(f"{Fore.GREEN}[0]{Style.RESET_ALL} Назад")

        choice = input(f"{Fore.GREEN}Выберите: {Style.RESET_ALL}").strip()

        if choice == "1":
            company = input("  Название компании: ").strip()
            if company:
                filters.add_blacklist_company(company)
                status(f"Добавлено в черный список: {company}", "success")
                input("\nНажмите Enter...")

        elif choice == "2":
            company = input("  Название компании: ").strip()
            if company:
                filters.add_whitelist_company(company)
                status(f"Добавлено в белый список: {company}", "success")
                input("\nНажмите Enter...")

        elif choice == "3":
            word = input("  Слово для черного списка: ").strip()
            if word:
                filters.add_blacklist_word(word)
                status(f"Слово добавлено: {word}", "success")
                input("\nНажмите Enter...")

        elif choice == "4":
            filter_stats = filters.get_filter_stats()
            print(f"\n{Fore.CYAN}=== Текущие фильтры ==={Style.RESET_ALL}")
            print(f"  Черный список компаний: {', '.join(filter_stats['blacklist_companies']) or 'нет'}")
            print(f"  Белый список компаний: {', '.join(filter_stats['whitelist_companies']) or 'нет'}")
            print(f"  Черный список слов: {', '.join(filter_stats['blacklist_words']) or 'нет'}")
            if filter_stats['min_salary']:
                print(f"  Мин. зарплата: {filter_stats['min_salary']:,}₽")
            if filter_stats['max_salary']:
                print(f"  Макс. зарплата: {filter_stats['max_salary']:,}₽")
            input("\nНажмите Enter...")

        elif choice == "5":
            min_sal = input("  Минимальная зарплата [пусто=любая]: ").strip()
            max_sal = input("  Максимальная зарплата [пусто=любая]: ").strip()
            require = input("  Требовать указание зарплаты? (y/n) [n]: ").strip().lower() == 'y'

            filters.set_salary_filter(
                min_salary=int(min_sal) if min_sal.isdigit() else None,
                max_salary=int(max_sal) if max_sal.isdigit() else None,
                require=require
            )
            status("Фильтр зарплаты обновлен", "success")
            input("\nНажмите Enter...")

        elif choice == "0":
            break


def export_data(db: Database):
    """Экспорт данных в CSV."""
    filepath = input("  Путь для экспорта [applications.csv]: ").strip() or "applications.csv"
    try:
        db.export_to_csv(filepath)
        status(f"Данные экспортированы в {filepath}", "success")
    except Exception as e:
        status(f"Ошибка экспорта: {e}", "error")
    input("\nНажмите Enter...")


def manage_cover_letters(cover_letters: CoverLetterManager):
    """Управление шаблонами писем."""
    while True:
        clear_screen()
        print_banner()
        print(f"\n{Fore.CYAN}=== Шаблоны сопроводительных писем ==={Style.RESET_ALL}")
        templates = cover_letters.get_all_templates()

        for i, t in enumerate(templates, 1):
            default_mark = " [ПО УМОЛЧАНИЮ]" if t["is_default"] else ""
            print(f"  {i}. {t['name']}{default_mark} (использовано {t['use_count']}x)")

        print(f"\n{Fore.GREEN}[a]{Style.RESET_ALL} Добавить шаблон")
        print(f"{Fore.GREEN}[d]{Style.RESET_ALL} Установить по умолчанию")
        print(f"{Fore.GREEN}[v]{Style.RESET_ALL} Просмотреть шаблон")
        print(f"{Fore.GREEN}[p]{Style.RESET_ALL} Показать плейсхолдеры")
        print(f"{Fore.GREEN}[0]{Style.RESET_ALL} Назад")

        choice = input(f"{Fore.GREEN}Выберите: {Style.RESET_ALL}").strip().lower()

        if choice == "a":
            name = input("  Название шаблона: ").strip()
            if name:
                print("  Введите текст шаблона (пустая строка = конец):")
                lines = []
                while True:
                    line = input()
                    if line == "":
                        break
                    lines.append(line)
                if lines:
                    cover_letters.add_template(name, "\n".join(lines))
                    status(f"Шаблон '{name}' добавлен", "success")
                    input("\nНажмите Enter...")

        elif choice == "d":
            num = input("  Номер шаблона: ").strip()
            if num.isdigit() and 0 < int(num) <= len(templates):
                template_name = templates[int(num) - 1]["name"]
                cover_letters.set_default(template_name)
                status(f"'{template_name}' установлен по умолчанию", "success")
                input("\nНажмите Enter...")

        elif choice == "v":
            num = input("  Номер шаблона: ").strip()
            if num.isdigit() and 0 < int(num) <= len(templates):
                t = templates[int(num) - 1]
                print(f"\n{Fore.CYAN}--- {t['name']} ---{Style.RESET_ALL}")
                print(t["content"])
                print(f"{Fore.CYAN}---{Style.RESET_ALL}")
                input("\nНажмите Enter...")

        elif choice == "p":
            print(f"\n{cover_letters.get_placeholders_help()}")
            input("\nНажмите Enter...")

        elif choice == "0":
            break


def select_browser():
    """Выбор браузера при запуске."""
    print(f"\n{Fore.CYAN}=== Выбор браузера ==={Style.RESET_ALL}")
    print(f"{Fore.GREEN}[1]{Style.RESET_ALL} Chrome (Google Chrome)")
    print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Edge (Microsoft Edge)")
    print(f"{Fore.GREEN}[3]{Style.RESET_ALL} Firefox (Mozilla Firefox)")
    print(f"{Fore.GREEN}[4]{Style.RESET_ALL} Авто (попробовать все)")

    choice = input(f"{Fore.GREEN}Выберите браузер [4]: {Style.RESET_ALL}").strip()

    browser_map = {
        "1": "chrome",
        "2": "edge",
        "3": "firefox",
        "4": "auto",
    }

    return browser_map.get(choice, "auto")


def parse_args():
    """Разбор аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="HeadHunter Destroyer - Автоматизация поиска работы",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python main.py                    Интерактивное меню
  python main.py --boost            Разовое обновление резюме
  python main.py --apply            Разовая рассылка
  python main.py --apply-query "python developer"
  python main.py --daemon           Демон режим (цикл)
  python main.py --telegram         С Telegram ботом
        """
    )

    parser.add_argument("--boost", action="store_true",
                        help="Разовое обновление резюме")
    parser.add_argument("--apply", action="store_true",
                        help="Разовая массовая рассылка")
    parser.add_argument("--apply-query", type=str, metavar="QUERY",
                        help="Рассылка с поисковым запросом")
    parser.add_argument("--daemon", action="store_true",
                        help="Демон режим (бесконечный цикл)")
    parser.add_argument("--telegram", action="store_true",
                        help="Запустить с Telegram ботом")
    parser.add_argument("--cover-letter", action="store_true",
                        help="Включить сопроводительные письма")
    parser.add_argument("--ai-letters", action="store_true",
                        help="Использовать AI для писем")
    parser.add_argument("--max-apply", type=int, default=200,
                        help="Максимум откликов (по умолчанию: 200)")
    parser.add_argument("--browser", type=str, choices=["chrome", "edge", "firefox", "auto"],
                        help="Выбор браузера")

    return parser.parse_args()


def run_daemon_mode(booster, applier, db, logger):
    """Демон режим - бесконечный цикл."""
    import time as time_module

    logger.info("Запуск демон режима...")
    status("Демон режим запущен. Ctrl+C для остановки.", "info")

    while True:
        try:
            # Boost if possible
            if booster.can_update():
                logger.info("Авто-обновление резюме...")
                run_resume_boost(booster)
            else:
                mins = booster.minutes_until_next_update()
                logger.debug(f"Следующий boost через {mins} минут")

            # Mass apply
            logger.info("Запуск авто-рассылки...")
            run_mass_apply(applier)

            # Wait 4 hours
            logger.info("Цикл завершен. Ожидание 4 часа...")
            time_module.sleep(4 * 60 * 60)

        except KeyboardInterrupt:
            logger.info("Демон остановлен пользователем")
            break
        except Exception as e:
            logger.error(f"Ошибка демона: {e}")
            time_module.sleep(60)


def main():
    """Главная функция."""
    args = parse_args()

    # Инициализация логгера
    logger = setup_logger()
    logger.log_session_start()

    # Выбор браузера
    if not args.browser and not (args.boost or args.apply or args.apply_query or args.daemon or args.telegram):
        clear_screen()
        print_banner()
        selected_browser = select_browser()
    else:
        selected_browser = args.browser or "auto"

    clear_screen()
    print_banner()

    # Инициализация БД
    status("Инициализация базы данных...", "info")
    db = Database()
    setup_default_filters(db)

    # Инициализация фильтров
    filters = VacancyFilter(db)

    # Инициализация сопроводительных писем
    cover_letters = CoverLetterManager(db)

    # Инициализация AI (опционально)
    ai_assistant = get_ai_assistant(db)
    if ai_assistant.is_enabled():
        status(f"AI помощник: {ai_assistant.provider} ({ai_assistant.model})", "info")

    if SERVER_MODE:
        ui.status("Запуск в SERVER MODE (headless браузер)", "info")
        ui.start_session()

    # Browser manager
    browser_manager = BrowserManager(browser=selected_browser)

    def signal_handler(sig, frame):
        logger.log_session_end()
        status("Завершение работы...", "warning")
        try:
            db.close()
        except:
            pass
        try:
            browser_manager.stop()
        except:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Запуск браузера
    status("Запуск браузера...", "info")

    try:
        page = browser_manager.start(use_existing_session=True)
    except Exception as e:
        logger.error(f"Не удалось запустить браузер: {e}")
        status(f"Ошибка запуска браузера: {e}", "error")
        if IS_WINDOWS:
            status("Убедитесь что браузер закрыт перед запуском", "warning")
        sys.exit(1)

    # Проверка авторизации
    status("Проверка авторизации...", "info")
    if browser_manager.is_logged_in():
        status("Успешное подключение к HH.ru!", "success")
        logger.info("Авторизован на HH.ru")
    else:
        status("Не авторизован на HH.ru", "warning")
        if SERVER_MODE:
            status("В server mode сначала войдите с GUI, затем скопируйте browser_data/ на сервер.", "warning")
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

    # Настройка писем
    if args.cover_letter or args.ai_letters:
        applier.set_cover_letter_mode(
            enabled=True,
            use_ai=args.ai_letters
        )
        status("Сопроводительные письма включены", "info")

    # Telegram бот
    telegram_bot = None
    if args.telegram:
        try:
            from telegram_bot import HHDestroyerBot, TELEGRAM_AVAILABLE
            if not TELEGRAM_AVAILABLE:
                status("Библиотека Telegram не установлена. Установите: pip install python-telegram-bot", "error")
            else:
                def do_boost():
                    return booster.boost_all_resumes()

                def do_apply(query=None):
                    params = {"text": query} if query else None
                    return applier.mass_apply(search_params=params)

                telegram_bot = HHDestroyerBot(
                    on_boost=do_boost,
                    on_apply=do_apply,
                    get_stats=applier.get_stats,
                    filters_manager=filters,
                    db=db
                )
                telegram_bot.run_async()
                status(f"Telegram бот запущен! Owner ID: {telegram_bot.owner_id}", "success")
        except ValueError as e:
            status(f"Ошибка Telegram бота: {e}", "error")
            status("Установите TELEGRAM_BOT_TOKEN и TELEGRAM_OWNER_ID", "warning")
        except Exception as e:
            status(f"Не удалось запустить Telegram бот: {e}", "error")

    # CLI режимы
    if args.daemon:
        run_daemon_mode(booster, applier, db, logger)
        logger.log_session_end()
        db.close()
        browser_manager.stop()
        return

    if args.boost:
        run_resume_boost(booster)
        logger.log_session_end()
        db.close()
        browser_manager.stop()
        return

    if args.apply or args.apply_query:
        params = {}
        if args.apply_query:
            params["text"] = args.apply_query
        params["_max_applications"] = args.max_apply
        run_mass_apply(applier, params if params else None)
        logger.log_session_end()
        db.close()
        browser_manager.stop()
        return

    # Интерактивный режим
    while True:
        try:
            clear_screen()
            print_banner()
            choice = print_menu()

            if choice == "1":
                run_resume_boost(booster)
                input("\nНажмите Enter для продолжения...")
            elif choice == "2":
                run_mass_apply(applier)
                input("\nНажмите Enter для продолжения...")
            elif choice == "3":
                params = get_search_params()
                run_mass_apply(applier, params)
                input("\nНажмите Enter для продолжения...")
            elif choice == "4":
                show_stats(applier, booster, db)
                input("\nНажмите Enter для продолжения...")
            elif choice == "5":
                manage_filters(filters)
            elif choice == "6":
                export_data(db)
            elif choice == "7":
                if browser_manager.is_logged_in():
                    status("Авторизован на HH.ru", "success")
                else:
                    status("Не авторизован", "error")
                input("\nНажмите Enter для продолжения...")
            elif choice == "8":
                browser_manager.clear_session()
                status("Сессия очищена. Перезапустите для входа.", "success")
                input("\nНажмите Enter для продолжения...")
            elif choice == "9":
                manage_cover_letters(cover_letters)
            elif choice == "0":
                break
            else:
                status("Неверная опция", "warning")
                input("\nНажмите Enter для продолжения...")

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            status(f"Ошибка: {e}", "error")
            input("\nНажмите Enter для продолжения...")

    # Завершение
    logger.log_session_end()
    status("Завершение работы...", "info")
    db.close()
    try:
        browser_manager.stop()
    except:
        pass
    status("До свидания!", "success")


if __name__ == "__main__":
    main()
