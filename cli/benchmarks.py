"""
Benchmark commands for projects
"""

import click
import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from cli.utils import (
    get_project_path, print_success, print_error, print_info, print_warning, BASE_DIR
)

console = Console()


@click.group()
def benchmarks_group():
    """⚡ Executar benchmarks de performance"""
    pass


@benchmarks_group.command('run')
@click.argument('project_name')
@click.option('--iterations', '-n', default=1000, help='Número de iterações')
@click.option('--benchmark', '-b', help='Benchmark específico para executar')
def run_benchmark(project_name, iterations, benchmark):
    """Executa benchmarks de performance de um projeto"""

    # Special handling for netflix-clone
    if project_name == 'netflix-clone':
        project_path = BASE_DIR / '09-projetos-praticos' / 'projeto-netflix-clone'
    else:
        project_path = get_project_path(project_name)

    if not project_path:
        print_error(f"Projeto '{project_name}' não encontrado.")
        return

    benchmarks_path = project_path / 'benchmarks'

    if not benchmarks_path.exists():
        print_warning(f"Diretório de benchmarks não encontrado em: {benchmarks_path}")
        console.print("\n💡 Este projeto pode não ter benchmarks implementados ainda.")
        return

    # Find benchmark files
    if benchmark:
        benchmark_files = [benchmarks_path / f'{benchmark}.py']
        if not benchmark_files[0].exists():
            benchmark_files = [benchmarks_path / f'benchmark_{benchmark}.py']
            if not benchmark_files[0].exists():
                print_error(f"Benchmark '{benchmark}' não encontrado.")
                return
    else:
        benchmark_files = list(benchmarks_path.glob('benchmark_*.py'))

    if not benchmark_files:
        print_warning("Nenhum benchmark encontrado.")
        return

    # Show what we're running
    print_info(f"Executando benchmarks em: {project_path}")
    console.print(f"[dim]Iterações: {iterations}[/dim]\n")

    for bench_file in benchmark_files:
        console.print(f"\n[bold cyan]Executando: {bench_file.name}[/bold cyan]")
        console.print("─" * 60)

        try:
            # Run the benchmark
            result = subprocess.run(
                [sys.executable, str(bench_file)],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode == 0:
                console.print(result.stdout)
                if result.stderr:
                    console.print(f"[yellow]{result.stderr}[/yellow]")
            else:
                print_error(f"Erro ao executar {bench_file.name}")
                if result.stderr:
                    console.print(f"[red]{result.stderr}[/red]")

        except subprocess.TimeoutExpired:
            print_error(f"Timeout ao executar {bench_file.name}")
        except Exception as e:
            print_error(f"Erro: {e}")

    print_success("\nBenchmarks concluídos!")


@benchmarks_group.command('list')
@click.argument('project_name')
def list_benchmarks(project_name):
    """Lista todos os benchmarks disponíveis em um projeto"""

    if project_name == 'netflix-clone':
        project_path = BASE_DIR / '09-projetos-praticos' / 'projeto-netflix-clone'
    else:
        project_path = get_project_path(project_name)

    if not project_path:
        print_error(f"Projeto '{project_name}' não encontrado.")
        return

    benchmarks_path = project_path / 'benchmarks'

    if not benchmarks_path.exists():
        print_warning(f"Diretório de benchmarks não encontrado.")
        return

    # Find all benchmark files
    benchmark_files = list(benchmarks_path.glob('benchmark_*.py'))

    if not benchmark_files:
        print_warning("Nenhum benchmark encontrado.")
        return

    console.print(f"\n[bold cyan]Benchmarks disponíveis em {project_name}:[/bold cyan]\n")

    for bench_file in sorted(benchmark_files):
        console.print(f"  ⚡ {bench_file.name}")

        # Try to read description from file
        try:
            with open(bench_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Look for docstring
            in_docstring = False
            docstring = []

            for line in lines[:20]:  # Check first 20 lines
                if '"""' in line or "'''" in line:
                    if not in_docstring:
                        in_docstring = True
                        # Get text on same line if exists
                        text = line.split('"""')[1] if '"""' in line else line.split("'''")[1]
                        if text.strip():
                            docstring.append(text.strip())
                    else:
                        break
                elif in_docstring:
                    docstring.append(line.strip())

            if docstring:
                desc = ' '.join(docstring[:2])  # First 2 lines
                console.print(f"     [dim]{desc}[/dim]")

        except Exception:
            pass

        console.print()


@benchmarks_group.command('compare')
@click.argument('project_name')
@click.argument('benchmark1')
@click.argument('benchmark2')
@click.option('--iterations', '-n', default=1000, help='Número de iterações')
def compare_benchmarks(project_name, benchmark1, benchmark2, iterations):
    """Compara dois benchmarks lado a lado"""

    if project_name == 'netflix-clone':
        project_path = BASE_DIR / '09-projetos-praticos' / 'projeto-netflix-clone'
    else:
        project_path = get_project_path(project_name)

    if not project_path:
        print_error(f"Projeto '{project_name}' não encontrado.")
        return

    benchmarks_path = project_path / 'benchmarks'

    if not benchmarks_path.exists():
        print_warning("Diretório de benchmarks não encontrado.")
        return

    print_info(f"Comparando benchmarks: {benchmark1} vs {benchmark2}")

    # This is a simplified comparison
    # In a real implementation, you'd want to parse the benchmark outputs
    # and create a comparison table

    console.print("\n[yellow]💡 Funcionalidade de comparação em desenvolvimento[/yellow]")
    console.print("Use 'benchmark run' para executar benchmarks individuais")


@benchmarks_group.command('profile')
@click.argument('project_name')
@click.argument('script_path')
@click.option('--memory', is_flag=True, help='Profile memory usage')
def profile_script(project_name, script_path, memory):
    """Perfila um script Python específico"""

    if project_name == 'netflix-clone':
        project_path = BASE_DIR / '09-projetos-praticos' / 'projeto-netflix-clone'
    else:
        project_path = get_project_path(project_name)

    if not project_path:
        print_error(f"Projeto '{project_name}' não encontrado.")
        return

    script = project_path / script_path

    if not script.exists():
        print_error(f"Script não encontrado: {script}")
        return

    print_info(f"Perfilando script: {script_path}")

    try:
        if memory:
            # Memory profiling
            cmd = [sys.executable, '-m', 'memory_profiler', str(script)]
            console.print("\n[bold]Memory Profiling:[/bold]")
            console.print("[dim]Isso pode levar algum tempo...[/dim]\n")
        else:
            # CPU profiling with cProfile
            cmd = [sys.executable, '-m', 'cProfile', '-s', 'cumulative', str(script)]
            console.print("\n[bold]CPU Profiling:[/bold]\n")

        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            console.print(result.stdout)
            if result.stderr:
                console.print(f"[yellow]{result.stderr}[/yellow]")
        else:
            print_error("Erro ao executar profiling")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")

    except subprocess.TimeoutExpired:
        print_error("Timeout ao executar profiling")
    except FileNotFoundError:
        if memory:
            print_error("memory_profiler não está instalado.")
            console.print("\n💡 Instale com: pip install memory-profiler")
        else:
            print_error("cProfile não está disponível.")
    except Exception as e:
        print_error(f"Erro: {e}")


@benchmarks_group.command('create')
@click.argument('project_name')
@click.argument('benchmark_name')
def create_benchmark(project_name, benchmark_name):
    """Cria um novo arquivo de benchmark"""

    if project_name == 'netflix-clone':
        project_path = BASE_DIR / '09-projetos-praticos' / 'projeto-netflix-clone'
    else:
        project_path = get_project_path(project_name)

    if not project_path:
        print_error(f"Projeto '{project_name}' não encontrado.")
        return

    benchmarks_path = project_path / 'benchmarks'
    benchmarks_path.mkdir(exist_ok=True)

    # Create benchmark file
    bench_file = benchmarks_path / f'benchmark_{benchmark_name}.py'

    if bench_file.exists():
        print_warning(f"Benchmark já existe: {bench_file}")
        if not click.confirm("Deseja sobrescrever?"):
            return

    # Template
    template = f'''"""
Benchmark for {benchmark_name}

Performance benchmarks to measure and optimize {benchmark_name} functionality.
"""

import time
import statistics
import numpy as np
from typing import Dict, List


def benchmark_{benchmark_name}(n_iterations: int = 1000) -> Dict[str, float]:
    """
    Benchmark {benchmark_name} performance

    Args:
        n_iterations: Number of iterations to run

    Returns:
        Dictionary with performance metrics
    """
    latencies = []

    print(f"Running {{n_iterations}} iterations...")

    for i in range(n_iterations):
        start = time.perf_counter()

        # TODO: Add your code to benchmark here
        result = None

        latency = time.perf_counter() - start
        latencies.append(latency * 1000)  # Convert to milliseconds

        if i % 100 == 0:
            print(f"Progress: {{i}}/{{n_iterations}}")

    return {{
        'mean': statistics.mean(latencies),
        'median': statistics.median(latencies),
        'p50': np.percentile(latencies, 50),
        'p95': np.percentile(latencies, 95),
        'p99': np.percentile(latencies, 99),
        'min': min(latencies),
        'max': max(latencies),
        'std': statistics.stdev(latencies),
    }}


def print_results(results: Dict[str, float]) -> None:
    """Print benchmark results in a formatted way"""
    print("\\n" + "=" * 60)
    print(f"{{' Benchmark Results ':^60}}")
    print("=" * 60)

    print(f"Mean latency:      {{results['mean']:.2f}} ms")
    print(f"Median latency:    {{results['median']:.2f}} ms")
    print(f"P50 latency:       {{results['p50']:.2f}} ms")
    print(f"P95 latency:       {{results['p95']:.2f}} ms")
    print(f"P99 latency:       {{results['p99']:.2f}} ms")
    print(f"Min latency:       {{results['min']:.2f}} ms")
    print(f"Max latency:       {{results['max']:.2f}} ms")
    print(f"Std deviation:     {{results['std']:.2f}} ms")

    print("=" * 60)

    # Performance targets (adjust as needed)
    target_p99 = 10.0  # 10ms target

    if results['p99'] < target_p99:
        print(f"✅ PASS: P99 latency ({{results['p99']:.2f}}ms) < target ({{target_p99}}ms)")
    else:
        print(f"❌ FAIL: P99 latency ({{results['p99']:.2f}}ms) >= target ({{target_p99}}ms)")


if __name__ == '__main__':
    print("Starting benchmark for {benchmark_name}...")

    results = benchmark_{benchmark_name}(n_iterations=1000)
    print_results(results)
'''

    try:
        with open(bench_file, 'w', encoding='utf-8') as f:
            f.write(template)

        print_success(f"Benchmark criado: {bench_file}")
        console.print("\n💡 Edite o arquivo e adicione seu código na seção TODO")

    except Exception as e:
        print_error(f"Erro ao criar benchmark: {e}")
