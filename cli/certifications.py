"""
Certifications management commands
"""

import click
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.markdown import Markdown
from cli.utils import (
    load_progress, save_progress, get_cert_path,
    print_success, print_error, print_info, print_warning,
    create_table, calculate_completion_percentage, BASE_DIR
)

console = Console()


# Certification definitions
CERTIFICATIONS = {
    'aws-data-analytics': {
        'name': 'AWS Certified Data Analytics - Specialty',
        'provider': 'AWS',
        'path': '11-certificacoes/01-aws/data-analytics-specialty',
        'cost': 300,
        'duration': '180 min',
        'questions': 65,
        'passing_score': 75,
        'roi': '+$10-20K/year',
        'difficulty': 4,
        'topics': ['Collection', 'Storage', 'Processing', 'Analysis', 'Security']
    },
    'databricks-de-associate': {
        'name': 'Databricks Certified Data Engineer Associate',
        'provider': 'Databricks',
        'path': '11-certificacoes/04-databricks/data-engineer-associate',
        'cost': 200,
        'duration': '90 min',
        'questions': 45,
        'passing_score': 70,
        'roi': '+$15-30K/year',
        'difficulty': 3,
        'topics': ['Lakehouse', 'Spark', 'Delta Lake', 'DLT', 'Unity Catalog']
    },
    'aws-solutions-architect': {
        'name': 'AWS Certified Solutions Architect - Associate',
        'provider': 'AWS',
        'path': '11-certificacoes/01-aws/solutions-architect-associate',
        'cost': 150,
        'duration': '130 min',
        'questions': 65,
        'passing_score': 72,
        'roi': '+$8-15K/year',
        'difficulty': 3,
        'topics': ['Compute', 'Storage', 'Databases', 'Networking', 'Security']
    },
    'gcp-professional-de': {
        'name': 'Google Cloud Professional Data Engineer',
        'provider': 'GCP',
        'path': '11-certificacoes/02-gcp/professional-data-engineer',
        'cost': 200,
        'duration': '120 min',
        'questions': 50,
        'passing_score': 70,
        'roi': '+$12-25K/year',
        'difficulty': 4,
        'topics': ['BigQuery', 'Dataflow', 'Pub/Sub', 'Cloud Storage', 'ML']
    }
}


@click.group()
def certs_group():
    """🎓 Gerenciar certificações"""
    pass


@certs_group.command('list')
@click.option('--provider', type=click.Choice(['all', 'AWS', 'GCP', 'Databricks']), default='all',
              help='Filter by provider')
@click.option('--difficulty', type=click.IntRange(1, 5), help='Filter by difficulty (1-5)')
def list_certs(provider, difficulty):
    """Lista todas as certificações disponíveis"""

    # Filter certifications
    filtered_certs = CERTIFICATIONS.copy()

    if provider != 'all':
        filtered_certs = {k: v for k, v in filtered_certs.items() if v['provider'] == provider}

    if difficulty:
        filtered_certs = {k: v for k, v in filtered_certs.items() if v['difficulty'] == difficulty}

    # Load progress
    progress = load_progress()
    cert_progress = progress.get('certifications', {})

    # Create table
    table = create_table(
        "🎓 Certificações Disponíveis",
        [
            {'header': 'ID', 'style': 'cyan'},
            {'header': 'Nome', 'style': 'white'},
            {'header': 'Provider', 'style': 'yellow'},
            {'header': 'Custo', 'style': 'green'},
            {'header': 'ROI', 'style': 'magenta'},
            {'header': 'Progresso', 'style': 'blue'},
        ]
    )

    for cert_id, cert in filtered_certs.items():
        # Get progress
        cert_data = cert_progress.get(cert_id, {})
        completed_topics = cert_data.get('completed_topics', [])
        total_topics = len(cert['topics'])

        if total_topics > 0:
            percentage = (len(completed_topics) / total_topics) * 100
            progress_bar = f"{percentage:.0f}%"

            if percentage == 100:
                progress_display = f"[green]✓ {progress_bar}[/green]"
            elif percentage > 0:
                progress_display = f"[yellow]⚙ {progress_bar}[/yellow]"
            else:
                progress_display = "[dim]0%[/dim]"
        else:
            progress_display = "[dim]N/A[/dim]"

        table.add_row(
            cert_id,
            cert['name'],
            cert['provider'],
            f"${cert['cost']}",
            cert['roi'],
            progress_display
        )

    console.print(table)

    # Summary
    total = len(filtered_certs)
    in_progress = sum(1 for cid in filtered_certs.keys()
                      if cert_progress.get(cid, {}).get('completed_topics', []))
    completed = sum(1 for cid in filtered_certs.keys()
                    if cert_progress.get(cid, {}).get('status') == 'certified')

    total_cost = sum(cert['cost'] for cert in filtered_certs.values())

    console.print()
    console.print(f"[bold]Total:[/bold] {total} | [green]Certificados:[/green] {completed} | "
                  f"[yellow]Em Progresso:[/yellow] {in_progress}")
    console.print(f"[bold]Investimento Total:[/bold] ${total_cost}")


@certs_group.command('start')
@click.argument('cert_id')
@click.option('--topic', help='Iniciar um tópico específico')
def start_cert(cert_id, topic):
    """Inicia o estudo de uma certificação"""

    if cert_id not in CERTIFICATIONS:
        print_error(f"Certificação '{cert_id}' não encontrada.")
        console.print("\n💡 Use 'study-cli.py certs list' para ver certificações disponíveis")
        return

    cert = CERTIFICATIONS[cert_id]
    cert_path = BASE_DIR / cert['path']

    if not cert_path.exists():
        print_error(f"Caminho da certificação não encontrado: {cert_path}")
        return

    # Update progress
    progress = load_progress()
    if 'certifications' not in progress:
        progress['certifications'] = {}

    if cert_id not in progress['certifications']:
        progress['certifications'][cert_id] = {
            'status': 'in_progress',
            'started_at': datetime.now().isoformat(),
            'completed_topics': [],
            'study_sessions': []
        }

    progress['certifications'][cert_id]['study_sessions'].append({
        'started_at': datetime.now().isoformat(),
        'topic': topic
    })

    save_progress(progress)

    # Display cert info
    panel_content = f"""[bold cyan]{cert['name']}[/bold cyan]

[bold]Provider:[/bold] {cert['provider']}
[bold]Custo:[/bold] ${cert['cost']}
[bold]Duração:[/bold] {cert['duration']}
[bold]Questões:[/bold] {cert['questions']}
[bold]Score mínimo:[/bold] {cert['passing_score']}%
[bold]ROI estimado:[/bold] {cert['roi']}

[bold]Tópicos:[/bold]
{chr(10).join(f"  • {t}" for t in cert['topics'])}

[dim]Caminho: {cert_path}[/dim]
"""
    console.print(Panel(panel_content, title="🚀 Iniciando Certificação", border_style="green"))

    # Show README
    readme_path = cert_path / 'README.md'
    if readme_path.exists():
        console.print("\n[bold]📖 Guia de Estudo:[/bold]\n")
        with open(readme_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
            # Show first 40 lines
            lines = md_content.split('\n')[:40]
            console.print(Markdown('\n'.join(lines)))

        if len(md_content.split('\n')) > 40:
            console.print("\n[dim]... (veja o README completo para mais detalhes)[/dim]")

    print_success(f"Certificação '{cert['name']}' iniciada!")
    print_info("Use 'certs progress' para acompanhar seu progresso")


@certs_group.command('progress')
@click.argument('cert_id', required=False)
@click.option('--detailed', is_flag=True, help='Mostrar progresso detalhado por tópico')
def cert_progress(cert_id, detailed):
    """Mostra o progresso de uma ou todas certificações"""

    progress = load_progress()
    cert_progress_data = progress.get('certifications', {})

    if cert_id:
        # Show specific certification
        if cert_id not in CERTIFICATIONS:
            print_error(f"Certificação '{cert_id}' não encontrada.")
            return

        cert = CERTIFICATIONS[cert_id]
        cert_data = cert_progress_data.get(cert_id, {})

        completed_topics = cert_data.get('completed_topics', [])
        total_topics = len(cert['topics'])
        percentage = calculate_completion_percentage(len(completed_topics), total_topics)

        # Progress bar
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress_bar:
            task = progress_bar.add_task(
                f"[cyan]{cert['name']}",
                total=total_topics,
                completed=len(completed_topics)
            )

        console.print()

        # Detailed progress
        if detailed:
            console.print("[bold]Tópicos:[/bold]")
            for i, topic in enumerate(cert['topics'], 1):
                status = "✓" if topic in completed_topics else "○"
                style = "green" if topic in completed_topics else "dim"
                console.print(f"  [{style}]{status}[/{style}] {i}. {topic}")

        console.print()

        # Stats
        study_sessions = len(cert_data.get('study_sessions', []))
        started_at = cert_data.get('started_at')
        status = cert_data.get('status', 'not_started')

        stats = f"""
[bold]Status:[/bold] {status.replace('_', ' ').title()}
[bold]Sessões de estudo:[/bold] {study_sessions}
[bold]Tópicos completos:[/bold] {len(completed_topics)}/{total_topics}
[bold]Progresso:[/bold] {percentage:.1f}%
"""
        if started_at:
            stats += f"[bold]Iniciado em:[/bold] {started_at}\n"

        console.print(Panel(stats.strip(), title="📊 Estatísticas", border_style="blue"))

    else:
        # Show all certifications summary
        console.print("\n[bold cyan]Resumo de Certificações[/bold cyan]\n")

        for cert_id, cert in CERTIFICATIONS.items():
            cert_data = cert_progress_data.get(cert_id, {})
            completed_topics = cert_data.get('completed_topics', [])
            total_topics = len(cert['topics'])
            percentage = calculate_completion_percentage(len(completed_topics), total_topics)

            console.print(f"[bold]{cert['name']}[/bold]")

            with Progress(
                TextColumn("  "),
                BarColumn(bar_width=30),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            ) as progress_bar:
                task = progress_bar.add_task(
                    "",
                    total=total_topics,
                    completed=len(completed_topics)
                )

            console.print()


@certs_group.command('complete-topic')
@click.argument('cert_id')
@click.argument('topic')
def complete_topic(cert_id, topic):
    """Marca um tópico como completo"""

    if cert_id not in CERTIFICATIONS:
        print_error(f"Certificação '{cert_id}' não encontrada.")
        return

    cert = CERTIFICATIONS[cert_id]

    if topic not in cert['topics']:
        print_error(f"Tópico '{topic}' não encontrado nesta certificação.")
        console.print(f"\n[bold]Tópicos disponíveis:[/bold]")
        for t in cert['topics']:
            console.print(f"  • {t}")
        return

    # Update progress
    progress = load_progress()
    if 'certifications' not in progress:
        progress['certifications'] = {}

    if cert_id not in progress['certifications']:
        progress['certifications'][cert_id] = {
            'completed_topics': [],
            'status': 'in_progress'
        }

    if topic not in progress['certifications'][cert_id].get('completed_topics', []):
        if 'completed_topics' not in progress['certifications'][cert_id]:
            progress['certifications'][cert_id]['completed_topics'] = []

        progress['certifications'][cert_id]['completed_topics'].append(topic)

        # Check if all topics completed
        if len(progress['certifications'][cert_id]['completed_topics']) == len(cert['topics']):
            progress['certifications'][cert_id]['status'] = 'ready_for_exam'
            print_success(f"Todos os tópicos completos! Você está pronto para o exame. 🎉")
        else:
            print_success(f"Tópico '{topic}' marcado como completo!")

        save_progress(progress)
    else:
        print_info(f"Tópico '{topic}' já estava marcado como completo.")


@certs_group.command('certified')
@click.argument('cert_id')
@click.option('--score', type=int, help='Score obtido no exame')
@click.option('--date', help='Data da certificação (YYYY-MM-DD)')
def mark_certified(cert_id, score, date):
    """Marca certificação como obtida"""

    if cert_id not in CERTIFICATIONS:
        print_error(f"Certificação '{cert_id}' não encontrada.")
        return

    cert = CERTIFICATIONS[cert_id]

    # Update progress
    progress = load_progress()
    if 'certifications' not in progress:
        progress['certifications'] = {}

    if cert_id not in progress['certifications']:
        progress['certifications'][cert_id] = {}

    progress['certifications'][cert_id]['status'] = 'certified'
    progress['certifications'][cert_id]['certified_at'] = date or datetime.now().isoformat()

    if score:
        progress['certifications'][cert_id]['score'] = score

    save_progress(progress)

    print_success(f"Parabéns! Certificação '{cert['name']}' obtida! 🎉🎓")

    if score:
        console.print(f"\n[bold]Score:[/bold] {score}% (mínimo: {cert['passing_score']}%)")
