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

# Import appropriate UI
if SERVER_MODE:
    from tui import TUI
    ui = TUI()
else:
    # Desktop mode - use colorama
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
{Fore.GREEN}[1]{Style.RESET_ALL} Boost all resumes (update to increase visibility)
{Fore.GREEN}[2]{Style.RESET_ALL} Mass apply to vacancies
{Fore.GREEN}[3]{Style.RESET_ALL} Mass apply with custom search
{Fore.GREEN}[4]{Style.RESET_ALL} Show session stats
{Fore.GREEN}[5]{Style.RESET_ALL} Check login status
{Fore.GREEN}[6]{Style.RESET_ALL} Clear session (logout)
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

        query = input(f"  Search query [empty]: ").strip()
        if query:
            params["text"] = query

        print("  Regions: 1=Moscow, 2=St.Petersburg, 113=Russia")
        area = input(f"  Region ID [1]: ").strip()
        params["area"] = area if area else "1"

        print("  Experience: noExperience, between1And3, between3And6, moreThan6")
        exp = input(f"  Experience [any]: ").strip()
        if exp:
            params["experience"] = exp

        print("  Schedule: fullDay, shift, flexible, remote, flyInFlyOut")
        schedule = input(f"  Schedule [any]: ").strip()
        if schedule:
            params["schedule"] = schedule

        max_apps = input(f"  Max applications [200]: ").strip()
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

    # Pass TUI callbacks in server mode
    callbacks = None
    if SERVER_MODE:
        callbacks = {
            "on_vacancy": ui.log_vacancy,
            "on_page": ui.log_page,
        }

    results = applier.mass_apply(search_params=params, max_applications=max_apps, callbacks=callbacks)

    status(f"Mass apply complete! Applied: {len(results['applied'])}, Skipped: {len(results['skipped'])}", "success")

    if SERVER_MODE:
        ui.show_vacancies_table(results['applied'])
    elif results['applied']:
        print(f"\n{Fore.CYAN}[*] Applied to:{Style.RESET_ALL}")
        for v in results['applied'][:10]:
            print(f"  - {v['title']} @ {v['employer']}")
        if len(results['applied']) > 10:
            print(f"  ... and {len(results['applied']) - 10} more")


def show_stats(applier: VacancyApplier, booster: ResumeBooster):
    """Show session statistics."""
    if SERVER_MODE:
        ui.show_stats()
    else:
        stats = applier.get_stats()
        print(f"\n{Fore.CYAN}[*] Session Statistics:{Style.RESET_ALL}")
        print(f"  Vacancies applied: {stats['applied']}")
        print(f"  Vacancies skipped: {stats['skipped']}")
        print(f"  Total processed: {stats['total_processed']}")

        if booster.last_update_time:
            print(f"  Last resume update: {booster.last_update_time.strftime('%H:%M:%S')}")
            print(f"  Next update in: {booster.minutes_until_next_update()} minutes")


def main():
    """Main entry point."""
    print_banner()

    if SERVER_MODE:
        ui.status("Running in SERVER MODE (headless browser)", "info")
        ui.start_session()

    # Setup signal handler for graceful exit
    browser_manager = BrowserManager()

    def signal_handler(sig, frame):
        status("Shutting down...", "warning")
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
            status("In server mode, you need to login once with GUI first, or copy cookies.", "warning")
            status("Run with HH_SERVER_MODE=false to login, then copy browser_data/ to server.", "info")
        browser_manager.wait_for_login()

    # Initialize modules
    booster = ResumeBooster(page)
    applier = VacancyApplier(page)

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
                show_stats(applier, booster)
            elif choice == "5":
                if browser_manager.is_logged_in():
                    status("Logged in to HH.ru", "success")
                else:
                    status("Not logged in", "error")
            elif choice == "6":
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
    status("Closing browser...", "info")
    browser_manager.stop()
    status("Goodbye!", "success")


if __name__ == "__main__":
    main()
