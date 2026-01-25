"""
HeadHunter Destroyer - Main Entry Point
Automates resume boosting and vacancy applications on HH.ru

Supports two modes:
- Desktop Mode (Windows/Linux with GUI): Visual browser window
- Server Mode (Linux headless): TUI interface, headless browser
"""

import sys
import signal
from datetime import datetime

from config import SERVER_MODE, IS_WINDOWS
from browser import BrowserManager
from resume_booster import ResumeBooster
from vacancy_applier import VacancyApplier
from database import Database
from filters import VacancyFilter, setup_default_filters

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


def print_banner():
    """Print application banner."""
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
{Fore.YELLOW}  HeadHunter Resume Booster & Vacancy Applier{Style.RESET_ALL}
{Fore.WHITE}  ============================================={Style.RESET_ALL}
"""
        print(banner)


def print_menu():
    """Print main menu."""
    if SERVER_MODE:
        return ui.print_menu()
    else:
        print(f"""
{Fore.GREEN}[1]{Style.RESET_ALL} Boost all resumes
{Fore.GREEN}[2]{Style.RESET_ALL} Mass apply to vacancies
{Fore.GREEN}[3]{Style.RESET_ALL} Mass apply with custom search
{Fore.GREEN}[4]{Style.RESET_ALL} Show statistics
{Fore.GREEN}[5]{Style.RESET_ALL} Manage filters (blacklist/whitelist)
{Fore.GREEN}[6]{Style.RESET_ALL} Export data to CSV
{Fore.GREEN}[7]{Style.RESET_ALL} Check login status
{Fore.GREEN}[8]{Style.RESET_ALL} Clear session (logout)
{Fore.GREEN}[0]{Style.RESET_ALL} Exit
""")
        return input(f"{Fore.GREEN}Select option: {Style.RESET_ALL}").strip()


def get_search_params() -> dict:
    """Get custom search parameters from user."""
    if SERVER_MODE:
        return ui.get_search_params()
    else:
        print(f"\n{Fore.CYAN}[*] Enter search parameters (press Enter for default):{Style.RESET_ALL}")

        params = {}

        query = input("  Search query [empty]: ").strip()
        if query:
            params["text"] = query

        print("  Regions: 1=Moscow, 2=St.Petersburg, 113=Russia")
        area = input("  Region ID [1]: ").strip()
        params["area"] = area if area else "1"

        print("  Experience: noExperience, between1And3, between3And6, moreThan6")
        exp = input("  Experience [any]: ").strip()
        if exp:
            params["experience"] = exp

        print("  Schedule: fullDay, shift, flexible, remote, flyInFlyOut")
        schedule = input("  Schedule [any]: ").strip()
        if schedule:
            params["schedule"] = schedule

        max_apps = input("  Max applications [200]: ").strip()
        if max_apps and max_apps.isdigit():
            params["_max_applications"] = int(max_apps)

        return params


def status(message: str, status_type: str = "info"):
    """Print status message."""
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
    """Run resume boost routine."""
    status("Starting resume boost...", "info")

    if not booster.can_update():
        mins = booster.minutes_until_next_update()
        status(f"HH.ru limits updates to every 4 hours. Next update in {mins} minutes.", "warning")
        return

    results = booster.boost_all_resumes(callback=ui.log_resume if SERVER_MODE else None)

    status(f"Resume boost complete! Success: {len(results['success'])}, Failed: {len(results['failed'])}", "success")


def run_mass_apply(applier: VacancyApplier, params: dict = None):
    """Run mass apply routine."""
    status("Starting mass apply...", "info")

    max_apps = params.pop("_max_applications", None) if params else None

    callbacks = None
    if SERVER_MODE:
        callbacks = {
            "on_vacancy": ui.log_vacancy,
            "on_page": ui.log_page,
        }

    results = applier.mass_apply(search_params=params, max_applications=max_apps, callbacks=callbacks)

    # Summary
    filtered_count = len(results.get('filtered', []))
    msg = f"Applied: {len(results['applied'])}, Skipped: {len(results['skipped'])}"
    if filtered_count > 0:
        msg += f", Filtered: {filtered_count}"
    status(f"Mass apply complete! {msg}", "success")

    if SERVER_MODE:
        ui.show_vacancies_table(results['applied'])
    elif results['applied']:
        print(f"\n{Fore.CYAN}[*] Applied to:{Style.RESET_ALL}")
        for v in results['applied'][:10]:
            salary_info = ""
            if v.get('salary_from'):
                salary_info = f" ({v['salary_from']:,}₽)"
            print(f"  - {v['title']}{salary_info} @ {v['employer']}")
        if len(results['applied']) > 10:
            print(f"  ... and {len(results['applied']) - 10} more")


def show_stats(applier: VacancyApplier, booster: ResumeBooster, db: Database):
    """Show session and database statistics."""
    stats = applier.get_stats()
    db_stats = db.get_stats()

    if SERVER_MODE:
        ui.show_stats()
    else:
        print(f"\n{Fore.CYAN}[*] Session Statistics:{Style.RESET_ALL}")
        print(f"  Applied this session: {stats['applied']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Filtered: {stats['filtered']}")

        print(f"\n{Fore.CYAN}[*] Database Statistics:{Style.RESET_ALL}")
        print(f"  Total applications: {db_stats['total_applications']}")
        print(f"  Today: {db_stats['today_applications']}")
        print(f"  This week: {db_stats['week_applications']}")

        if db_stats.get('top_employers'):
            print(f"\n{Fore.CYAN}[*] Top Employers:{Style.RESET_ALL}")
            for employer, count in db_stats['top_employers'][:5]:
                print(f"  {employer}: {count}")

        print(f"\n{Fore.CYAN}[*] Filters:{Style.RESET_ALL}")
        print(f"  Blacklisted companies: {db_stats['blacklisted_companies']}")
        print(f"  Whitelisted companies: {db_stats['whitelisted_companies']}")

        if booster.last_update_time:
            print(f"\n  Last resume update: {booster.last_update_time.strftime('%H:%M:%S')}")
            print(f"  Next update in: {booster.minutes_until_next_update()} minutes")


def manage_filters(filters: VacancyFilter):
    """Manage blacklist/whitelist."""
    if SERVER_MODE:
        # Use TUI version
        while ui.manage_filters_menu(filters):
            pass
        return

    # Desktop version
    while True:
        print(f"\n{Fore.CYAN}[*] Filter Management:{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[1]{Style.RESET_ALL} Add company to blacklist")
        print(f"{Fore.GREEN}[2]{Style.RESET_ALL} Add company to whitelist")
        print(f"{Fore.GREEN}[3]{Style.RESET_ALL} Add word to blacklist")
        print(f"{Fore.GREEN}[4]{Style.RESET_ALL} Show current filters")
        print(f"{Fore.GREEN}[5]{Style.RESET_ALL} Set salary filter")
        print(f"{Fore.GREEN}[0]{Style.RESET_ALL} Back to main menu")

        choice = input(f"{Fore.GREEN}Select: {Style.RESET_ALL}").strip()

        if choice == "1":
            company = input("  Company name to blacklist: ").strip()
            if company:
                filters.add_blacklist_company(company)
                status(f"Added '{company}' to blacklist", "success")

        elif choice == "2":
            company = input("  Company name to whitelist (priority): ").strip()
            if company:
                filters.add_whitelist_company(company)
                status(f"Added '{company}' to whitelist", "success")

        elif choice == "3":
            word = input("  Word to blacklist: ").strip()
            if word:
                filters.add_blacklist_word(word)
                status(f"Added '{word}' to word blacklist", "success")

        elif choice == "4":
            filter_stats = filters.get_filter_stats()
            print(f"\n{Fore.CYAN}[*] Current Filters:{Style.RESET_ALL}")
            print(f"  Blacklisted companies: {', '.join(filter_stats['blacklist_companies']) or 'none'}")
            print(f"  Whitelisted companies: {', '.join(filter_stats['whitelist_companies']) or 'none'}")
            print(f"  Blacklisted words: {', '.join(filter_stats['blacklist_words']) or 'none'}")
            if filter_stats['min_salary']:
                print(f"  Min salary: {filter_stats['min_salary']:,}₽")
            if filter_stats['max_salary']:
                print(f"  Max salary: {filter_stats['max_salary']:,}₽")

        elif choice == "5":
            min_sal = input("  Minimum salary (empty=any): ").strip()
            max_sal = input("  Maximum salary (empty=any): ").strip()
            require = input("  Require salary in vacancy? (y/n) [n]: ").strip().lower() == 'y'

            filters.set_salary_filter(
                min_salary=int(min_sal) if min_sal.isdigit() else None,
                max_salary=int(max_sal) if max_sal.isdigit() else None,
                require=require
            )
            status("Salary filter updated", "success")

        elif choice == "0":
            break


def export_data(db: Database):
    """Export data to CSV."""
    filepath = input("  Export path [applications.csv]: ").strip() or "applications.csv"
    try:
        db.export_to_csv(filepath)
        status(f"Data exported to {filepath}", "success")
    except Exception as e:
        status(f"Export failed: {e}", "error")


def main():
    """Main entry point."""
    print_banner()

    # Initialize database
    status("Initializing database...", "info")
    db = Database()
    setup_default_filters(db)

    # Initialize filters
    filters = VacancyFilter(db)

    if SERVER_MODE:
        ui.status("Running in SERVER MODE (headless browser)", "info")
        ui.start_session()

    # Setup signal handler
    browser_manager = BrowserManager()

    def signal_handler(sig, frame):
        status("Shutting down...", "warning")
        db.close()
        browser_manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Start browser
    status("Starting browser...", "info")

    try:
        page = browser_manager.start(use_existing_session=True)
    except Exception as e:
        status(f"Failed to start browser: {e}", "error")
        if IS_WINDOWS:
            status("Make sure Edge is closed before running this script", "warning")
        sys.exit(1)

    # Check login status
    status("Checking login status...", "info")
    if browser_manager.is_logged_in():
        status("Successfully connected to HH.ru!", "success")
    else:
        status("Not logged in to HH.ru", "warning")
        if SERVER_MODE:
            status("In server mode, login once with GUI first, then copy browser_data/ to server.", "warning")
        browser_manager.wait_for_login()

    # Initialize modules with database and filters
    booster = ResumeBooster(page)
    applier = VacancyApplier(page, db=db, filters=filters)

    # Main loop
    while True:
        try:
            choice = print_menu()

            if choice == "1":
                run_resume_boost(booster)
            elif choice == "2":
                run_mass_apply(applier)
            elif choice == "3":
                params = get_search_params()
                run_mass_apply(applier, params)
            elif choice == "4":
                show_stats(applier, booster, db)
            elif choice == "5":
                manage_filters(filters)
            elif choice == "6":
                export_data(db)
            elif choice == "7":
                if browser_manager.is_logged_in():
                    status("Logged in to HH.ru", "success")
                else:
                    status("Not logged in", "error")
            elif choice == "8":
                browser_manager.clear_session()
                status("Session cleared. Restart to login again.", "success")
            elif choice == "0":
                break
            else:
                status("Invalid option", "warning")

        except KeyboardInterrupt:
            break
        except Exception as e:
            status(f"Error: {e}", "error")

    # Cleanup
    status("Closing...", "info")
    db.close()
    browser_manager.stop()
    status("Goodbye!", "success")


if __name__ == "__main__":
    main()
