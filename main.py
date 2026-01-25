"""
HeadHunter Destroyer - Main Entry Point
Automates resume boosting and vacancy applications on HH.ru
"""

import sys
import time
import signal
from datetime import datetime

try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        GREEN = YELLOW = RED = CYAN = MAGENTA = WHITE = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""

from browser import BrowserManager
from resume_booster import ResumeBooster
from vacancy_applier import VacancyApplier


def print_banner():
    """Print application banner."""
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
    print(f"""
{Fore.GREEN}[1]{Style.RESET_ALL} Boost all resumes (update to increase visibility)
{Fore.GREEN}[2]{Style.RESET_ALL} Mass apply to vacancies
{Fore.GREEN}[3]{Style.RESET_ALL} Mass apply with custom search
{Fore.GREEN}[4]{Style.RESET_ALL} Show session stats
{Fore.GREEN}[5]{Style.RESET_ALL} Check login status
{Fore.GREEN}[0]{Style.RESET_ALL} Exit
""")


def get_search_params() -> dict:
    """Get custom search parameters from user."""
    print(f"\n{Fore.CYAN}[*] Enter search parameters (press Enter for default):{Style.RESET_ALL}")

    params = {}

    # Search query
    query = input(f"  Search query [empty]: ").strip()
    if query:
        params["text"] = query

    # Region
    print("  Regions: 1=Moscow, 2=St.Petersburg, 113=Russia")
    area = input(f"  Region ID [1]: ").strip()
    params["area"] = area if area else "1"

    # Experience
    print("  Experience: noExperience, between1And3, between3And6, moreThan6")
    exp = input(f"  Experience [any]: ").strip()
    if exp:
        params["experience"] = exp

    # Schedule
    print("  Schedule: fullDay, shift, flexible, remote, flyInFlyOut")
    schedule = input(f"  Schedule [any]: ").strip()
    if schedule:
        params["schedule"] = schedule

    # Max applications
    max_apps = input(f"  Max applications [200]: ").strip()
    if max_apps and max_apps.isdigit():
        params["_max_applications"] = int(max_apps)

    return params


def run_resume_boost(booster: ResumeBooster):
    """Run resume boost routine."""
    print(f"\n{Fore.CYAN}[*] Starting resume boost...{Style.RESET_ALL}")

    if not booster.can_update():
        mins = booster.minutes_until_next_update()
        print(f"{Fore.YELLOW}[!] HH.ru limits updates to every 4 hours.")
        print(f"[!] Next update available in {mins} minutes.{Style.RESET_ALL}")
        return

    results = booster.boost_all_resumes()

    print(f"\n{Fore.GREEN}[+] Resume boost complete!{Style.RESET_ALL}")
    print(f"  Success: {len(results['success'])}")
    print(f"  Failed: {len(results['failed'])}")


def run_mass_apply(applier: VacancyApplier, params: dict = None):
    """Run mass apply routine."""
    print(f"\n{Fore.CYAN}[*] Starting mass apply...{Style.RESET_ALL}")

    max_apps = params.pop("_max_applications", None) if params else None

    results = applier.mass_apply(search_params=params, max_applications=max_apps)

    print(f"\n{Fore.GREEN}[+] Mass apply complete!{Style.RESET_ALL}")
    print(f"  Applied: {len(results['applied'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Pages scanned: {results['pages_scanned']}")

    if results['applied']:
        print(f"\n{Fore.CYAN}[*] Applied to:{Style.RESET_ALL}")
        for v in results['applied'][:10]:  # Show first 10
            print(f"  - {v['title']} @ {v['employer']}")
        if len(results['applied']) > 10:
            print(f"  ... and {len(results['applied']) - 10} more")


def show_stats(applier: VacancyApplier, booster: ResumeBooster):
    """Show session statistics."""
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

    # Setup signal handler for graceful exit
    browser_manager = BrowserManager()

    def signal_handler(sig, frame):
        print(f"\n{Fore.YELLOW}[!] Shutting down...{Style.RESET_ALL}")
        browser_manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Start browser
    print(f"{Fore.CYAN}[*] Starting browser...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}[!] Using Edge browser with your existing session{Style.RESET_ALL}")

    try:
        page = browser_manager.start(use_existing_session=True)
    except Exception as e:
        print(f"{Fore.RED}[!] Failed to start browser: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[!] Make sure Edge is closed before running this script{Style.RESET_ALL}")
        sys.exit(1)

    # Check login status
    print(f"{Fore.CYAN}[*] Checking login status...{Style.RESET_ALL}")
    if browser_manager.is_logged_in():
        print(f"{Fore.GREEN}[+] Successfully connected to HH.ru!{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}[!] Not logged in to HH.ru{Style.RESET_ALL}")
        browser_manager.wait_for_login()

    # Initialize modules
    booster = ResumeBooster(page)
    applier = VacancyApplier(page)

    # Main loop
    while True:
        print_menu()
        choice = input(f"{Fore.GREEN}Select option: {Style.RESET_ALL}").strip()

        try:
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
                    print(f"{Fore.GREEN}[+] Logged in to HH.ru{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[-] Not logged in{Style.RESET_ALL}")
            elif choice == "0":
                break
            else:
                print(f"{Fore.YELLOW}[!] Invalid option{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}[!] Error: {e}{Style.RESET_ALL}")

    # Cleanup
    print(f"\n{Fore.CYAN}[*] Closing browser...{Style.RESET_ALL}")
    browser_manager.stop()
    print(f"{Fore.GREEN}[+] Goodbye!{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
