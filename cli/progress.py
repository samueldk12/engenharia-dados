"""
Progress tracking commands
"""

import click
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from cli.utils import (
    load_progress, save_progress, print_success, print_error, print_info,
    DATA_DIR, PROGRESS_FILE
)

console = Console()


@click.group()
def progress_group():
    """📊 Gerenciar progresso de estudos"""
    pass


@progress_group.command('show')
@click.option('--export', type=click.Path(), help='Exportar progresso para arquivo JSON')
def show_progress(export):
    """Mostra o progresso geral de estudos"""

    progress = load_progress()

    projects_data = progress.get('projects', {})
    certs_data = progress.get('certifications', {})
    last_updated = progress.get('last_updated')

    # Projects summary
    total_projects = len(projects_data)
    completed_projects = sum(1 for p in projects_data.values() if p.get('status') == 'completed')
    in_progress_projects = sum(1 for p in projects_data.values() if p.get('status') == 'in_progress')

    # Certifications summary
    total_certs = len(certs_data)
    certified = sum(1 for c in certs_data.values() if c.get('status') == 'certified')
    ready_for_exam = sum(1 for c in certs_data.values() if c.get('status') == 'ready_for_exam')
    studying = sum(1 for c in certs_data.values()
                   if c.get('status') in ['in_progress', 'not_started'] and c.get('completed_topics'))

    # Study sessions count
    total_sessions = sum(len(p.get('sessions', [])) for p in projects_data.values())
    total_sessions += sum(len(c.get('study_sessions', [])) for c in certs_data.values())

    # Create summary panel
    summary = f"""[bold cyan]Resumo Geral de Estudos[/bold cyan]

[bold yellow]📁 Projetos:[/bold yellow]
  • Total: {total_projects}
  • [green]Completos:[/green] {completed_projects}
  • [yellow]Em Progresso:[/yellow] {in_progress_projects}
  • [dim]Não Iniciados:[/dim] {total_projects - completed_projects - in_progress_projects}

[bold yellow]🎓 Certificações:[/bold yellow]
  • Total: {total_certs}
  • [green]Certificado:[/green] {certified}
  • [blue]Pronto para Exame:[/blue] {ready_for_exam}
  • [yellow]Estudando:[/yellow] {studying}
  • [dim]Não Iniciados:[/dim] {total_certs - certified - ready_for_exam - studying}

[bold yellow]📚 Sessões de Estudo:[/bold yellow]
  • Total de sessões: {total_sessions}

"""

    if last_updated:
        try:
            updated_date = datetime.fromisoformat(last_updated)
            summary += f"\n[dim]Última atualização: {updated_date.strftime('%Y-%m-%d %H:%M')}[/dim]"
        except:
            pass

    console.print(Panel(summary, border_style="cyan", box=box.ROUNDED))

    # Recent activity
    if projects_data or certs_data:
        console.print("\n[bold]Atividade Recente:[/bold]\n")

        activities = []

        # Get project activities
        for proj_id, proj_data in projects_data.items():
            if 'sessions' in proj_data and proj_data['sessions']:
                last_session = proj_data['sessions'][-1]
                activities.append({
                    'type': 'project',
                    'id': proj_id,
                    'date': last_session.get('started_at', ''),
                    'status': proj_data.get('status', 'unknown')
                })

        # Get cert activities
        for cert_id, cert_data in certs_data.items():
            if 'study_sessions' in cert_data and cert_data['study_sessions']:
                last_session = cert_data['study_sessions'][-1]
                activities.append({
                    'type': 'certification',
                    'id': cert_id,
                    'date': last_session.get('started_at', ''),
                    'topic': last_session.get('topic')
                })

        # Sort by date
        activities.sort(key=lambda x: x['date'], reverse=True)

        # Show last 10
        for activity in activities[:10]:
            try:
                date_obj = datetime.fromisoformat(activity['date'])
                date_str = date_obj.strftime('%Y-%m-%d %H:%M')
            except:
                date_str = 'Unknown date'

            if activity['type'] == 'project':
                icon = "📁"
                status = activity.get('status', '').replace('_', ' ').title()
                console.print(f"  {icon} [cyan]{activity['id']}[/cyan] - {status} - [dim]{date_str}[/dim]")
            else:
                icon = "🎓"
                topic = activity.get('topic', 'General study')
                console.print(f"  {icon} [cyan]{activity['id']}[/cyan] - {topic} - [dim]{date_str}[/dim]")

    # Export if requested
    if export:
        try:
            with open(export, 'w', encoding='utf-8') as f:
                json.dump(progress, f, indent=2, ensure_ascii=False)
            print_success(f"Progresso exportado para: {export}")
        except Exception as e:
            print_error(f"Erro ao exportar progresso: {e}")


@progress_group.command('reset')
@click.option('--confirm', is_flag=True, help='Confirmar reset sem prompt')
def reset_progress(confirm):
    """Reset de todo o progresso (cuidado!)"""

    if not confirm:
        console.print("[bold red]⚠️  ATENÇÃO![/bold red]")
        console.print("Isso irá apagar TODO o seu progresso de estudos.")

        if not click.confirm("\nTem certeza que deseja continuar?"):
            print_info("Operação cancelada.")
            return

    # Backup current progress
    progress = load_progress()
    backup_file = DATA_DIR / f'progress_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
        print_info(f"Backup salvo em: {backup_file}")
    except Exception as e:
        print_error(f"Erro ao criar backup: {e}")
        return

    # Reset progress
    new_progress = {
        'projects': {},
        'certifications': {},
        'last_updated': datetime.now().isoformat()
    }

    save_progress(new_progress)
    print_success("Progresso resetado com sucesso!")


@progress_group.command('stats')
def show_stats():
    """Mostra estatísticas detalhadas"""

    progress = load_progress()
    projects_data = progress.get('projects', {})
    certs_data = progress.get('certifications', {})

    # Calculate stats
    total_study_time = 0

    # Projects stats table
    projects_table = Table(title="📁 Estatísticas de Projetos", box=box.ROUNDED)
    projects_table.add_column("Projeto", style="cyan")
    projects_table.add_column("Sessões", style="yellow")
    projects_table.add_column("Status", style="green")

    for proj_id, proj_data in projects_data.items():
        sessions = len(proj_data.get('sessions', []))
        status = proj_data.get('status', 'not_started').replace('_', ' ').title()

        status_emoji = {
            'Completed': '✓',
            'In Progress': '⚙',
            'Not Started': '○'
        }.get(status, '○')

        projects_table.add_row(
            proj_id,
            str(sessions),
            f"{status_emoji} {status}"
        )

    console.print(projects_table)
    console.print()

    # Certifications stats table
    certs_table = Table(title="🎓 Estatísticas de Certificações", box=box.ROUNDED)
    certs_table.add_column("Certificação", style="cyan")
    certs_table.add_column("Sessões", style="yellow")
    certs_table.add_column("Tópicos", style="blue")
    certs_table.add_column("Status", style="green")

    for cert_id, cert_data in certs_data.items():
        sessions = len(cert_data.get('study_sessions', []))
        topics = len(cert_data.get('completed_topics', []))
        status = cert_data.get('status', 'not_started').replace('_', ' ').title()

        status_emoji = {
            'Certified': '🎓',
            'Ready For Exam': '✓',
            'In Progress': '⚙',
            'Not Started': '○'
        }.get(status, '○')

        certs_table.add_row(
            cert_id,
            str(sessions),
            str(topics),
            f"{status_emoji} {status}"
        )

    console.print(certs_table)


@progress_group.command('import')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--merge', is_flag=True, help='Fazer merge com progresso existente')
def import_progress(file_path, merge):
    """Importa progresso de um arquivo JSON"""

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            imported_progress = json.load(f)

        if merge:
            # Merge with existing progress
            current_progress = load_progress()

            # Merge projects
            if 'projects' in imported_progress:
                if 'projects' not in current_progress:
                    current_progress['projects'] = {}
                current_progress['projects'].update(imported_progress['projects'])

            # Merge certifications
            if 'certifications' in imported_progress:
                if 'certifications' not in current_progress:
                    current_progress['certifications'] = {}
                current_progress['certifications'].update(imported_progress['certifications'])

            save_progress(current_progress)
            print_success("Progresso importado e mesclado com sucesso!")
        else:
            # Replace completely
            save_progress(imported_progress)
            print_success("Progresso importado com sucesso!")

    except json.JSONDecodeError:
        print_error("Arquivo JSON inválido.")
    except Exception as e:
        print_error(f"Erro ao importar progresso: {e}")


@progress_group.command('backup')
@click.argument('output_path', type=click.Path(), required=False)
def backup_progress(output_path):
    """Cria um backup do progresso atual"""

    progress = load_progress()

    if not output_path:
        output_path = DATA_DIR / f'progress_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)

        print_success(f"Backup criado com sucesso!")
        console.print(f"[bold]Localização:[/bold] {output_path}")

    except Exception as e:
        print_error(f"Erro ao criar backup: {e}")
