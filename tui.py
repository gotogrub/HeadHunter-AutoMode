"""
HeadHunter Destroyer - Text User Interface (TUI)
For headless/server environments (SSH, no GUI)
"""

import sys
import time
from datetime import datetime
from typing import Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class TUI:
    """Text-based User Interface for server/headless mode."""

    def __init__(self):
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None
        self.stats = {
            "applied": 0,
            "skipped": 0,
            "failed": 0,
            "resumes_updated": 0,
            "pages_scanned": 0,
            "start_time": None,
        }

    def print(self, message: str, style: str = None):
        """Print message to console."""
        if self.console:
            self.console.print(message, style=style)
        else:
            print(message)

    def print_banner(self):
        """Print application banner."""
        banner = """
 ██╗  ██╗██╗  ██╗    ██████╗ ███████╗███████╗████████╗██████╗  ██████╗ ██╗   ██╗███████╗██████╗
 ██║  ██║██║  ██║    ██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗╚██╗ ██╔╝██╔════╝██╔══██╗
 ███████║███████║    ██║  ██║█████╗  ███████╗   ██║   ██████╔╝██║   ██║ ╚████╔╝ █████╗  ██████╔╝
 ██╔══██║██╔══██║    ██║  ██║██╔══╝  ╚════██║   ██║   ██╔══██╗██║   ██║  ╚██╔╝  ██╔══╝  ██╔══██╗
 ██║  ██║██║  ██║    ██████╔╝███████╗███████║   ██║   ██║  ██║╚██████╔╝   ██║   ███████╗██║  ██║
 ╚═╝  ╚═╝╚═╝  ╚═╝    ╚═════╝ ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝╚═╝  ╚═╝
        """
        if self.console:
            self.console.print(Panel(banner, title="[bold cyan]SERVER MODE[/]", border_style="cyan"))
        else:
            print(banner)
            print("=" * 60)
            print("  SERVER MODE - Headless Browser")
            print("=" * 60)

    def print_menu(self) -> str:
        """Print menu and get user choice."""
        if self.console:
            table = Table(show_header=False, box=box.ROUNDED, border_style="green")
            table.add_column("Option", style="bold green", width=4)
            table.add_column("Description", style="white")

            table.add_row("1", "Boost all resumes")
            table.add_row("2", "Mass apply to vacancies (default search)")
            table.add_row("3", "Mass apply with custom search")
            table.add_row("4", "Show statistics")
            table.add_row("5", "Check login status")
            table.add_row("6", "Clear session (logout)")
            table.add_row("0", "Exit")

            self.console.print(table)
            return self.console.input("[bold green]Select option:[/] ")
        else:
            print("\n[1] Boost all resumes")
            print("[2] Mass apply to vacancies")
            print("[3] Mass apply with custom search")
            print("[4] Show statistics")
            print("[5] Check login status")
            print("[6] Clear session")
            print("[0] Exit")
            return input("Select option: ")

    def get_search_params(self) -> dict:
        """Get search parameters from user."""
        params = {}

        self.print("\n[bold cyan]Search Parameters[/]" if self.console else "\n=== Search Parameters ===")

        # Search query
        query = input("  Search query [empty]: ").strip()
        if query:
            params["text"] = query

        # Region
        self.print("  Regions: 1=Moscow, 2=St.Petersburg, 113=Russia")
        area = input("  Region ID [1]: ").strip()
        params["area"] = area if area else "1"

        # Experience
        self.print("  Experience: noExperience, between1And3, between3And6, moreThan6")
        exp = input("  Experience [any]: ").strip()
        if exp:
            params["experience"] = exp

        # Schedule
        self.print("  Schedule: fullDay, shift, flexible, remote, flyInFlyOut")
        schedule = input("  Schedule [any]: ").strip()
        if schedule:
            params["schedule"] = schedule

        # Salary
        salary = input("  Min salary [any]: ").strip()
        if salary and salary.isdigit():
            params["salary"] = salary
            params["only_with_salary"] = "true"

        # Max applications
        max_apps = input("  Max applications [200]: ").strip()
        if max_apps and max_apps.isdigit():
            params["_max_applications"] = int(max_apps)

        return params

    def show_progress(self, description: str, total: int = 100):
        """Create and return a progress context manager."""
        if self.console and RICH_AVAILABLE:
            return Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
            )
        return None

    def log_vacancy(self, title: str, employer: str, status: str):
        """Log vacancy processing result."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        if status == "applied":
            self.stats["applied"] += 1
            style = "bold green"
            icon = "✓"
        elif status == "skipped":
            self.stats["skipped"] += 1
            style = "yellow"
            icon = "~"
        else:
            self.stats["failed"] += 1
            style = "red"
            icon = "✗"

        if self.console:
            self.console.print(f"[dim]{timestamp}[/] [{style}]{icon}[/] {title[:50]} @ {employer[:30]}")
        else:
            print(f"{timestamp} [{icon}] {title[:50]} @ {employer[:30]}")

    def log_resume(self, title: str, status: str):
        """Log resume update result."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        if status == "success":
            self.stats["resumes_updated"] += 1
            style = "bold green"
            icon = "✓"
        else:
            style = "red"
            icon = "✗"

        if self.console:
            self.console.print(f"[dim]{timestamp}[/] [{style}]{icon}[/] Resume: {title}")
        else:
            print(f"{timestamp} [{icon}] Resume: {title}")

    def log_page(self, page_num: int, vacancies_count: int):
        """Log page scan."""
        self.stats["pages_scanned"] = page_num
        if self.console:
            self.console.print(f"[dim]───[/] Page {page_num}: found {vacancies_count} vacancies")
        else:
            print(f"--- Page {page_num}: found {vacancies_count} vacancies")

    def show_stats(self):
        """Display current statistics."""
        if self.console:
            table = Table(title="Session Statistics", box=box.ROUNDED)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Vacancies Applied", str(self.stats["applied"]))
            table.add_row("Vacancies Skipped", str(self.stats["skipped"]))
            table.add_row("Failed", str(self.stats["failed"]))
            table.add_row("Resumes Updated", str(self.stats["resumes_updated"]))
            table.add_row("Pages Scanned", str(self.stats["pages_scanned"]))

            if self.stats["start_time"]:
                elapsed = datetime.now() - self.stats["start_time"]
                table.add_row("Session Time", str(elapsed).split(".")[0])

            self.console.print(table)
        else:
            print("\n=== Statistics ===")
            print(f"  Applied: {self.stats['applied']}")
            print(f"  Skipped: {self.stats['skipped']}")
            print(f"  Failed: {self.stats['failed']}")
            print(f"  Resumes: {self.stats['resumes_updated']}")
            print(f"  Pages: {self.stats['pages_scanned']}")

    def show_vacancies_table(self, vacancies: list):
        """Display vacancies in a table format."""
        if not vacancies:
            self.print("[yellow]No vacancies found[/]" if self.console else "No vacancies found")
            return

        if self.console:
            table = Table(title=f"Found {len(vacancies)} vacancies", box=box.SIMPLE)
            table.add_column("#", style="dim", width=4)
            table.add_column("Title", style="cyan", max_width=40)
            table.add_column("Employer", style="green", max_width=25)
            table.add_column("Status", style="yellow", width=10)

            for i, v in enumerate(vacancies[:20], 1):  # Show first 20
                table.add_row(
                    str(i),
                    v.get("title", "N/A")[:40],
                    v.get("employer", "N/A")[:25],
                    v.get("status", "pending")
                )

            if len(vacancies) > 20:
                table.add_row("...", f"and {len(vacancies) - 20} more", "", "")

            self.console.print(table)
        else:
            print(f"\n=== Found {len(vacancies)} vacancies ===")
            for i, v in enumerate(vacancies[:20], 1):
                print(f"  {i}. {v.get('title', 'N/A')[:40]} @ {v.get('employer', 'N/A')[:25]}")

    def status(self, message: str, status_type: str = "info"):
        """Print status message."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        styles = {
            "info": ("blue", "ℹ"),
            "success": ("green", "✓"),
            "warning": ("yellow", "⚠"),
            "error": ("red", "✗"),
        }

        style, icon = styles.get(status_type, ("white", "•"))

        if self.console:
            self.console.print(f"[dim]{timestamp}[/] [bold {style}]{icon}[/] {message}")
        else:
            print(f"{timestamp} [{icon}] {message}")

    def wait_for_input(self, prompt: str = "Press Enter to continue..."):
        """Wait for user input."""
        input(prompt)

    def confirm(self, message: str) -> bool:
        """Ask for confirmation."""
        if self.console:
            response = self.console.input(f"[yellow]{message} (y/n):[/] ")
        else:
            response = input(f"{message} (y/n): ")
        return response.lower() in ("y", "yes")

    def start_session(self):
        """Mark session start."""
        self.stats["start_time"] = datetime.now()

    def clear(self):
        """Clear screen."""
        if self.console:
            self.console.clear()
        else:
            print("\033[2J\033[H", end="")
