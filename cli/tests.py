"""
Testing commands for projects
"""

import click
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from cli.utils import (
    get_project_path, print_success, print_error, print_info, print_warning, BASE_DIR
)

console = Console()


@click.group()
def tests_group():
    """🧪 Executar testes nos projetos"""
    pass


@tests_group.command('run')
@click.argument('project_name')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--coverage', is_flag=True, help='Run with coverage')
@click.option('--pattern', default='test_*.py', help='Test file pattern')
def run_tests(project_name, verbose, coverage, pattern):
    """Executa testes de um projeto"""

    # Special handling for netflix-clone
    if project_name == 'netflix-clone':
        project_path = BASE_DIR / '09-projetos-praticos' / 'projeto-netflix-clone'
    else:
        project_path = get_project_path(project_name)

    if not project_path:
        print_error(f"Projeto '{project_name}' não encontrado.")
        return

    tests_path = project_path / 'tests'

    if not tests_path.exists():
        print_warning(f"Diretório de testes não encontrado em: {tests_path}")
        console.print("\n💡 Este projeto pode não ter testes implementados ainda.")
        return

    # Build pytest command
    cmd = ['pytest', str(tests_path)]

    if verbose:
        cmd.append('-v')

    if coverage:
        cmd.extend(['--cov=.', '--cov-report=term-missing'])

    cmd.extend(['-k', pattern.replace('test_', '').replace('.py', '')])

    # Show what we're running
    print_info(f"Executando testes em: {project_path}")
    console.print(f"[dim]Comando: {' '.join(cmd)}[/dim]\n")

    try:
        # Run tests
        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=False,
            text=True
        )

        if result.returncode == 0:
            print_success("Todos os testes passaram! ✓")
        else:
            print_error("Alguns testes falharam.")

    except FileNotFoundError:
        print_error("pytest não está instalado.")
        console.print("\n💡 Instale com: pip install pytest pytest-cov")
    except Exception as e:
        print_error(f"Erro ao executar testes: {e}")


@tests_group.command('list')
@click.argument('project_name')
def list_tests(project_name):
    """Lista todos os testes disponíveis em um projeto"""

    if project_name == 'netflix-clone':
        project_path = BASE_DIR / '09-projetos-praticos' / 'projeto-netflix-clone'
    else:
        project_path = get_project_path(project_name)

    if not project_path:
        print_error(f"Projeto '{project_name}' não encontrado.")
        return

    tests_path = project_path / 'tests'

    if not tests_path.exists():
        print_warning(f"Diretório de testes não encontrado.")
        return

    # Find all test files
    test_files = list(tests_path.glob('test_*.py'))

    if not test_files:
        print_warning("Nenhum arquivo de teste encontrado.")
        return

    console.print(f"\n[bold cyan]Testes disponíveis em {project_name}:[/bold cyan]\n")

    for test_file in sorted(test_files):
        console.print(f"  📄 {test_file.name}")

        # Try to parse test functions
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple regex to find test functions
            import re
            test_functions = re.findall(r'def (test_\w+)', content)

            if test_functions:
                for func in test_functions:
                    console.print(f"     └─ [dim]{func}[/dim]")

        except Exception as e:
            console.print(f"     [dim](erro ao ler arquivo: {e})[/dim]")

        console.print()


@tests_group.command('watch')
@click.argument('project_name')
def watch_tests(project_name):
    """Watch mode - executa testes automaticamente quando arquivos mudam"""

    if project_name == 'netflix-clone':
        project_path = BASE_DIR / '09-projetos-praticos' / 'projeto-netflix-clone'
    else:
        project_path = get_project_path(project_name)

    if not project_path:
        print_error(f"Projeto '{project_name}' não encontrado.")
        return

    try:
        cmd = ['pytest-watch', str(project_path / 'tests')]
        print_info(f"Iniciando watch mode para: {project_name}")
        console.print("[dim]Pressione Ctrl+C para parar[/dim]\n")

        subprocess.run(cmd, cwd=project_path)

    except FileNotFoundError:
        print_error("pytest-watch não está instalado.")
        console.print("\n💡 Instale com: pip install pytest-watch")
    except KeyboardInterrupt:
        print_info("\nWatch mode interrompido.")
    except Exception as e:
        print_error(f"Erro: {e}")


@tests_group.command('coverage')
@click.argument('project_name')
@click.option('--html', is_flag=True, help='Gerar relatório HTML')
def test_coverage(project_name, html):
    """Gera relatório de cobertura de testes"""

    if project_name == 'netflix-clone':
        project_path = BASE_DIR / '09-projetos-praticos' / 'projeto-netflix-clone'
    else:
        project_path = get_project_path(project_name)

    if not project_path:
        print_error(f"Projeto '{project_name}' não encontrado.")
        return

    tests_path = project_path / 'tests'

    if not tests_path.exists():
        print_warning("Diretório de testes não encontrado.")
        return

    # Build command
    cmd = [
        'pytest',
        str(tests_path),
        '--cov=.',
        '--cov-report=term-missing'
    ]

    if html:
        cmd.append('--cov-report=html')

    print_info(f"Gerando relatório de cobertura para: {project_name}")

    try:
        result = subprocess.run(cmd, cwd=project_path)

        if html:
            html_report = project_path / 'htmlcov' / 'index.html'
            if html_report.exists():
                print_success(f"Relatório HTML gerado: {html_report}")
                console.print("\n💡 Abra no navegador para visualizar")

    except FileNotFoundError:
        print_error("pytest ou pytest-cov não está instalado.")
        console.print("\n💡 Instale com: pip install pytest pytest-cov")
    except Exception as e:
        print_error(f"Erro ao gerar relatório: {e}")


@tests_group.command('create')
@click.argument('project_name')
@click.argument('module_name')
def create_test(project_name, module_name):
    """Cria um novo arquivo de teste"""

    if project_name == 'netflix-clone':
        project_path = BASE_DIR / '09-projetos-praticos' / 'projeto-netflix-clone'
    else:
        project_path = get_project_path(project_name)

    if not project_path:
        print_error(f"Projeto '{project_name}' não encontrado.")
        return

    tests_path = project_path / 'tests'
    tests_path.mkdir(exist_ok=True)

    # Create __init__.py if doesn't exist
    init_file = tests_path / '__init__.py'
    if not init_file.exists():
        init_file.touch()

    # Create test file
    test_file = tests_path / f'test_{module_name}.py'

    if test_file.exists():
        print_warning(f"Arquivo de teste já existe: {test_file}")
        if not click.confirm("Deseja sobrescrever?"):
            return

    # Template
    template = f'''"""
Tests for {module_name}
"""

import pytest
from unittest.mock import MagicMock, patch


class Test{module_name.title().replace("_", "")}:
    """Test suite for {module_name}"""

    def test_example(self):
        """Example test - replace with actual tests"""
        assert True

    def test_example_with_fixture(self):
        """Example test with fixture"""
        # TODO: Implement test
        pass

    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 3),
        (3, 4),
    ])
    def test_example_parametrized(self, input, expected):
        """Example parametrized test"""
        assert input + 1 == expected


# Integration tests
class Test{module_name.title().replace("_", "")}Integration:
    """Integration tests for {module_name}"""

    @pytest.mark.integration
    def test_integration_example(self):
        """Example integration test"""
        # TODO: Implement integration test
        pass
'''

    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(template)

        print_success(f"Arquivo de teste criado: {test_file}")

        # Show the created file
        console.print("\n[bold]Conteúdo criado:[/bold]\n")
        syntax = Syntax(template, "python", theme="monokai", line_numbers=True)
        console.print(syntax)

    except Exception as e:
        print_error(f"Erro ao criar arquivo: {e}")
