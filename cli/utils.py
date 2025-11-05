"""
Utility functions for the CLI
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / '.data'
PROGRESS_FILE = DATA_DIR / 'progress.json'
CONFIG_FILE = DATA_DIR / 'config.json'

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


def load_progress() -> Dict[str, Any]:
    """Load progress data from JSON file"""
    if not PROGRESS_FILE.exists():
        return {
            'projects': {},
            'certifications': {},
            'last_updated': None
        }

    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_progress(progress: Dict[str, Any]) -> None:
    """Save progress data to JSON file"""
    progress['last_updated'] = datetime.now().isoformat()

    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def load_config() -> Dict[str, Any]:
    """Load configuration from JSON file"""
    if not CONFIG_FILE.exists():
        default_config = {
            'default_editor': os.environ.get('EDITOR', 'vim'),
            'show_hints': True,
            'auto_save_progress': True
        }
        save_config(default_config)
        return default_config

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


def get_project_path(project_name: str) -> Optional[Path]:
    """Get the path to a project"""
    # Check in 09-projetos-praticos
    praticos_path = BASE_DIR / '09-projetos-praticos' / f'projeto-{project_name}'
    if praticos_path.exists():
        return praticos_path

    # Check in 10-projetos-entrevista
    entrevista_path = BASE_DIR / '10-projetos-entrevista' / project_name
    if entrevista_path.exists():
        return entrevista_path

    return None


def get_cert_path(cert_name: str) -> Optional[Path]:
    """Get the path to a certification"""
    certs_path = BASE_DIR / '11-certificacoes'

    # Try to find the certification
    for provider_dir in certs_path.iterdir():
        if provider_dir.is_dir():
            cert_path = provider_dir / cert_name
            if cert_path.exists():
                return cert_path

    return None


def print_success(message: str) -> None:
    """Print success message"""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print error message"""
    console.print(f"[red]✗[/red] {message}")


def print_info(message: str) -> None:
    """Print info message"""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_warning(message: str) -> None:
    """Print warning message"""
    console.print(f"[yellow]⚠[/yellow] {message}")


def create_table(title: str, columns: list) -> Table:
    """Create a rich table with standard styling"""
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold cyan")

    for column in columns:
        table.add_column(column['header'], style=column.get('style', 'white'))

    return table


def format_duration(seconds: int) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def calculate_completion_percentage(completed: int, total: int) -> float:
    """Calculate completion percentage"""
    if total == 0:
        return 0.0
    return (completed / total) * 100


def get_difficulty_emoji(stars: int) -> str:
    """Get emoji representation of difficulty"""
    if stars <= 2:
        return "🟢"  # Easy
    elif stars <= 3:
        return "🟡"  # Medium
    else:
        return "🔴"  # Hard
