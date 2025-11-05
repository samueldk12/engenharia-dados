"""
Projects management commands
"""

import click
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from cli.utils import (
    load_progress, save_progress, get_project_path,
    print_success, print_error, print_info, print_warning,
    create_table, get_difficulty_emoji, BASE_DIR
)

console = Console()


# Project definitions
PROJECTS = {
    'netflix-clone': {
        'name': 'Netflix Clone',
        'path': '09-projetos-praticos/projeto-netflix-clone',
        'difficulty': 5,
        'type': 'practical',
        'topics': ['Video Streaming', 'ML', 'Real-time Analytics'],
        'time': '120 min'
    },
    'log-processing': {
        'name': 'Log Processing System',
        'path': '10-projetos-entrevista/01-log-processing-system',
        'difficulty': 2,
        'type': 'interview',
        'topics': ['Parsing', 'Aggregation', 'Performance'],
        'time': '45 min'
    },
    'rate-limiter': {
        'name': 'Rate Limiter',
        'path': '10-projetos-entrevista/03-rate-limiter',
        'difficulty': 3,
        'type': 'interview',
        'topics': ['Token Bucket', 'Redis', 'Distributed Systems'],
        'time': '60 min'
    },
    'ride-sharing': {
        'name': 'Ride-Sharing System',
        'path': '10-projetos-entrevista/05-ride-sharing-system',
        'difficulty': 5,
        'type': 'interview',
        'topics': ['Geospatial', 'Matching', 'State Machine'],
        'time': '120 min'
    },
    'ecommerce-analytics': {
        'name': 'E-commerce Analytics Pipeline',
        'path': '10-projetos-entrevista/06-ecommerce-analytics-pipeline',
        'difficulty': 5,
        'type': 'interview',
        'topics': ['Lambda Architecture', 'Real-time', 'Data Lake'],
        'time': '120 min'
    }
}


@click.group()
def projects_group():
    """📁 Gerenciar projetos práticos e de entrevista"""
    pass


@projects_group.command('list')
@click.option('--type', type=click.Choice(['all', 'practical', 'interview']), default='all',
              help='Filter by project type')
@click.option('--difficulty', type=click.IntRange(1, 5), help='Filter by difficulty (1-5 stars)')
def list_projects(type, difficulty):
    """Lista todos os projetos disponíveis"""

    # Filter projects
    filtered_projects = PROJECTS.copy()

    if type != 'all':
        filtered_projects = {k: v for k, v in filtered_projects.items() if v['type'] == type}

    if difficulty:
        filtered_projects = {k: v for k, v in filtered_projects.items() if v['difficulty'] == difficulty}

    # Load progress
    progress = load_progress()
    project_progress = progress.get('projects', {})

    # Create table
    table = create_table(
        "📚 Projetos Disponíveis",
        [
            {'header': 'ID', 'style': 'cyan'},
            {'header': 'Nome', 'style': 'white'},
            {'header': 'Tipo', 'style': 'yellow'},
            {'header': 'Dificuldade', 'style': 'magenta'},
            {'header': 'Tempo', 'style': 'blue'},
            {'header': 'Status', 'style': 'green'},
        ]
    )

    for project_id, project in filtered_projects.items():
        # Get status
        proj_data = project_progress.get(project_id, {})
        status = proj_data.get('status', 'Not Started')

        if status == 'completed':
            status_display = "[green]✓ Completo[/green]"
        elif status == 'in_progress':
            status_display = "[yellow]⚙ Em Progresso[/yellow]"
        else:
            status_display = "[dim]○ Não Iniciado[/dim]"

        # Difficulty display
        difficulty_emoji = get_difficulty_emoji(project['difficulty'])
        difficulty_stars = "⭐" * project['difficulty']

        table.add_row(
            project_id,
            project['name'],
            project['type'].title(),
            f"{difficulty_emoji} {difficulty_stars}",
            project['time'],
            status_display
        )

    console.print(table)

    # Summary
    total = len(filtered_projects)
    completed = sum(1 for pid in filtered_projects.keys()
                    if project_progress.get(pid, {}).get('status') == 'completed')
    in_progress = sum(1 for pid in filtered_projects.keys()
                      if project_progress.get(pid, {}).get('status') == 'in_progress')

    console.print()
    console.print(f"[bold]Total:[/bold] {total} | [green]Completos:[/green] {completed} | "
                  f"[yellow]Em Progresso:[/yellow] {in_progress}")


@projects_group.command('start')
@click.argument('project_id')
@click.option('--editor', help='Editor to open project with (default: $EDITOR)')
def start_project(project_id, editor):
    """Inicia um projeto e abre no editor"""

    if project_id not in PROJECTS:
        print_error(f"Projeto '{project_id}' não encontrado.")
        console.print("\n💡 Use 'study-cli.py projects list' para ver projetos disponíveis")
        return

    project = PROJECTS[project_id]
    project_path = BASE_DIR / project['path']

    if not project_path.exists():
        print_error(f"Caminho do projeto não encontrado: {project_path}")
        return

    # Update progress
    progress = load_progress()
    if 'projects' not in progress:
        progress['projects'] = {}

    if project_id not in progress['projects']:
        progress['projects'][project_id] = {
            'status': 'in_progress',
            'started_at': datetime.now().isoformat(),
            'sessions': []
        }
    else:
        progress['projects'][project_id]['status'] = 'in_progress'

    progress['projects'][project_id]['sessions'].append({
        'started_at': datetime.now().isoformat()
    })

    save_progress(progress)

    # Display project info
    panel_content = f"""[bold cyan]{project['name']}[/bold cyan]

[bold]Dificuldade:[/bold] {"⭐" * project['difficulty']}
[bold]Tempo estimado:[/bold] {project['time']}
[bold]Tópicos:[/bold] {', '.join(project['topics'])}
[bold]Caminho:[/bold] {project_path}

[dim]Status atualizado para: Em Progresso[/dim]
"""
    console.print(Panel(panel_content, title="🚀 Iniciando Projeto", border_style="green"))

    # Show README if exists
    readme_path = project_path / 'README.md'
    if readme_path.exists():
        console.print("\n[bold]📖 README:[/bold]\n")
        with open(readme_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
            # Show first 30 lines
            lines = md_content.split('\n')[:30]
            console.print(Markdown('\n'.join(lines)))

        if len(md_content.split('\n')) > 30:
            console.print("\n[dim]... (use 'cat README.md' para ver completo)[/dim]")

    # Open in editor
    if editor or shutil.which('code') or shutil.which('vim'):
        editor_cmd = editor or shutil.which('code') or shutil.which('vim')
        print_info(f"Abrindo projeto no editor: {editor_cmd}")

        try:
            subprocess.run([editor_cmd, str(project_path)])
        except Exception as e:
            print_warning(f"Não foi possível abrir o editor: {e}")

    print_success(f"Projeto '{project['name']}' iniciado com sucesso!")


@projects_group.command('complete')
@click.argument('project_id')
@click.option('--notes', help='Adicionar notas sobre o projeto')
def complete_project(project_id, notes):
    """Marca um projeto como completo"""

    if project_id not in PROJECTS:
        print_error(f"Projeto '{project_id}' não encontrado.")
        return

    project = PROJECTS[project_id]

    # Update progress
    progress = load_progress()
    if 'projects' not in progress:
        progress['projects'] = {}

    if project_id not in progress['projects']:
        progress['projects'][project_id] = {}

    progress['projects'][project_id]['status'] = 'completed'
    progress['projects'][project_id]['completed_at'] = datetime.now().isoformat()

    if notes:
        progress['projects'][project_id]['notes'] = notes

    # Update last session
    if 'sessions' in progress['projects'][project_id]:
        sessions = progress['projects'][project_id]['sessions']
        if sessions and 'completed_at' not in sessions[-1]:
            sessions[-1]['completed_at'] = datetime.now().isoformat()

    save_progress(progress)

    print_success(f"Projeto '{project['name']}' marcado como completo! 🎉")

    if notes:
        console.print(f"\n[bold]Notas:[/bold] {notes}")


@projects_group.command('status')
@click.argument('project_id', required=False)
def project_status(project_id):
    """Mostra o status de um projeto ou de todos"""

    progress = load_progress()
    project_progress = progress.get('projects', {})

    if project_id:
        # Show specific project
        if project_id not in PROJECTS:
            print_error(f"Projeto '{project_id}' não encontrado.")
            return

        project = PROJECTS[project_id]
        proj_data = project_progress.get(project_id, {})

        status = proj_data.get('status', 'not_started')
        started_at = proj_data.get('started_at')
        completed_at = proj_data.get('completed_at')
        sessions = proj_data.get('sessions', [])
        notes = proj_data.get('notes')

        content = f"""[bold cyan]{project['name']}[/bold cyan]

[bold]Status:[/bold] {status.replace('_', ' ').title()}
[bold]Dificuldade:[/bold] {"⭐" * project['difficulty']}
[bold]Tipo:[/bold] {project['type'].title()}
[bold]Tempo estimado:[/bold] {project['time']}

[bold]Sessões de estudo:[/bold] {len(sessions)}
"""

        if started_at:
            content += f"[bold]Iniciado em:[/bold] {started_at}\n"

        if completed_at:
            content += f"[bold]Completo em:[/bold] {completed_at}\n"

        if notes:
            content += f"\n[bold]Notas:[/bold]\n{notes}\n"

        console.print(Panel(content, title="📊 Status do Projeto", border_style="blue"))

    else:
        # Show all projects summary
        list_projects.callback(type='all', difficulty=None)


@projects_group.command('upload')
@click.argument('source_path', type=click.Path(exists=True))
@click.argument('project_name')
@click.option('--type', type=click.Choice(['practical', 'interview']), required=True,
              help='Tipo do projeto')
def upload_project(source_path, project_name, type):
    """Faz upload de um novo projeto"""

    source = Path(source_path)

    # Determine destination
    if type == 'practical':
        dest_dir = BASE_DIR / '09-projetos-praticos'
        dest_path = dest_dir / f'projeto-{project_name}'
    else:
        dest_dir = BASE_DIR / '10-projetos-entrevista'
        dest_path = dest_dir / project_name

    if dest_path.exists():
        print_error(f"Projeto já existe em: {dest_path}")
        if not click.confirm("Deseja sobrescrever?"):
            return

    try:
        # Copy project
        if source.is_file():
            dest_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest_path / source.name)
        else:
            shutil.copytree(source, dest_path, dirs_exist_ok=True)

        print_success(f"Projeto '{project_name}' carregado com sucesso!")
        console.print(f"[bold]Localização:[/bold] {dest_path}")

        # Ask if user wants to start it
        if click.confirm("\nDeseja iniciar o projeto agora?"):
            # This would require registering the new project first
            print_info("Para iniciar, adicione o projeto ao registro e use 'projects start'")

    except Exception as e:
        print_error(f"Erro ao carregar projeto: {e}")
