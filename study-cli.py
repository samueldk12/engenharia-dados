#!/usr/bin/env python3
"""
Data Engineering Study CLI
==========================

CLI principal para gerenciar estudos, projetos e certificações de Data Engineering.

Usage:
    study-cli.py projects list
    study-cli.py projects start <name>
    study-cli.py certs list
    study-cli.py progress show
"""

import click
from rich.console import Console
from cli.projects import projects_group
from cli.certifications import certs_group
from cli.progress import progress_group
from cli.tests import tests_group
from cli.benchmarks import benchmarks_group
from cli.web import web_group

console = Console()

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version='1.0.0', prog_name='study-cli')
def cli():
    """
    🎓 Data Engineering Study CLI

    Ferramenta de linha de comando para gerenciar estudos,
    projetos práticos e certificações de Data Engineering.

    Exemplos:
        study-cli.py projects list
        study-cli.py projects start netflix-clone
        study-cli.py certs progress
        study-cli.py test run log-processing
    """
    pass


# Register command groups
cli.add_command(projects_group, name='projects')
cli.add_command(certs_group, name='certs')
cli.add_command(progress_group, name='progress')
cli.add_command(tests_group, name='test')
cli.add_command(benchmarks_group, name='benchmark')
cli.add_command(web_group, name='web')


if __name__ == '__main__':
    cli()
