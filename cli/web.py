"""
Web server commands
"""

import click
import subprocess
import sys
import webbrowser
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from cli.utils import print_success, print_error, print_info, BASE_DIR

console = Console()


@click.group()
def web_group():
    """🌐 Gerenciar interface web"""
    pass


@web_group.command('start')
@click.option('--port', default=8000, help='Port to run the server on')
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--no-browser', is_flag=True, help='Don\'t open browser automatically')
@click.option('--reload', is_flag=True, help='Enable auto-reload on code changes')
def start_server(port, host, no_browser, reload):
    """Inicia o servidor web"""

    web_dir = BASE_DIR / 'web'
    app_file = web_dir / 'app.py'

    if not app_file.exists():
        print_error(f"Arquivo da aplicação não encontrado: {app_file}")
        return

    # Display server info
    panel_content = f"""[bold cyan]Web Server Starting[/bold cyan]

[bold]URL:[/bold] http://{host}:{port}
[bold]Aplicação:[/bold] {app_file}
[bold]Auto-reload:[/bold] {'Enabled' if reload else 'Disabled'}

[dim]Pressione Ctrl+C para parar o servidor[/dim]
"""
    console.print(Panel(panel_content, title="🌐 Servidor Web", border_style="green"))

    # Build uvicorn command
    cmd = [
        sys.executable, '-m', 'uvicorn',
        'app:app',
        '--host', host,
        '--port', str(port)
    ]

    if reload:
        cmd.append('--reload')

    print_info(f"Iniciando servidor em http://{host}:{port}")

    # Open browser after a delay
    if not no_browser:
        def open_browser():
            time.sleep(2)  # Wait for server to start
            url = f"http://{host}:{port}"
            print_info(f"Abrindo navegador: {url}")
            webbrowser.open(url)

        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()

    try:
        # Run uvicorn
        subprocess.run(cmd, cwd=web_dir)
    except KeyboardInterrupt:
        print_info("\nServidor interrompido pelo usuário")
    except FileNotFoundError:
        print_error("uvicorn não está instalado.")
        console.print("\n💡 Instale com: pip install 'uvicorn[standard]'")
    except Exception as e:
        print_error(f"Erro ao iniciar servidor: {e}")


@web_group.command('open')
@click.option('--port', default=8000, help='Port the server is running on')
@click.option('--host', default='127.0.0.1', help='Host the server is running on')
def open_browser(port, host):
    """Abre o navegador na interface web"""

    url = f"http://{host}:{port}"

    print_info(f"Abrindo navegador: {url}")

    try:
        webbrowser.open(url)
        print_success("Navegador aberto com sucesso!")
    except Exception as e:
        print_error(f"Erro ao abrir navegador: {e}")
        console.print(f"\n💡 Abra manualmente: {url}")


@web_group.command('docs')
@click.option('--port', default=8000, help='Port the server is running on')
@click.option('--host', default='127.0.0.1', help='Host the server is running on')
def open_docs(port, host):
    """Abre a documentação da API"""

    url = f"http://{host}:{port}/docs"

    print_info(f"Abrindo documentação da API: {url}")

    try:
        webbrowser.open(url)
        print_success("Documentação aberta com sucesso!")
    except Exception as e:
        print_error(f"Erro ao abrir navegador: {e}")
        console.print(f"\n💡 Abra manualmente: {url}")


@web_group.command('status')
@click.option('--port', default=8000, help='Port to check')
@click.option('--host', default='127.0.0.1', help='Host to check')
def check_status(port, host):
    """Verifica se o servidor está rodando"""

    import socket

    url = f"http://{host}:{port}"

    # Check if port is open
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)

    try:
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print_success(f"Servidor está rodando em {url}")

            # Try to ping health endpoint
            try:
                import requests
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    console.print(f"\n[bold]Status:[/bold] {data.get('status')}")
                    console.print(f"[bold]Version:[/bold] {data.get('version')}")
            except:
                pass

        else:
            print_error(f"Servidor não está rodando em {url}")
            console.print("\n💡 Inicie com: study-cli.py web start")

    except Exception as e:
        print_error(f"Erro ao verificar status: {e}")


@web_group.command('info')
def show_info():
    """Mostra informações sobre a interface web"""

    info = """[bold cyan]Interface Web - Study Manager[/bold cyan]

[bold]Descrição:[/bold]
Interface web completa para gerenciar projetos, certificações e progresso
de estudos de Data Engineering.

[bold]Funcionalidades:[/bold]
  • Dashboard com estatísticas gerais
  • Gerenciamento de projetos (iniciar, completar)
  • Gerenciamento de certificações (estudar, marcar tópicos)
  • Visualização de progresso com gráficos
  • Export/Import de dados
  • Interface responsiva e intuitiva

[bold]Tecnologias:[/bold]
  • Backend: FastAPI + Python
  • Frontend: Vue.js 3 + Vanilla CSS
  • API: REST com documentação automática

[bold]Comandos:[/bold]
  study-cli.py web start           - Inicia o servidor
  study-cli.py web start --reload  - Inicia com auto-reload
  study-cli.py web open            - Abre no navegador
  study-cli.py web docs            - Abre documentação da API
  study-cli.py web status          - Verifica se está rodando

[bold]Atalhos de Teclado (na web):[/bold]
  Ctrl/Cmd + R      - Atualizar dados
  Ctrl/Cmd + 1-4    - Navegar entre views

[bold]API Endpoints:[/bold]
  GET  /api/projects               - Listar projetos
  POST /api/projects/:id/start     - Iniciar projeto
  POST /api/projects/:id/complete  - Completar projeto
  GET  /api/certifications         - Listar certificações
  POST /api/certifications/:id/start  - Iniciar certificação
  GET  /api/progress               - Ver progresso
  GET  /docs                       - Documentação interativa

[dim]Para mais informações, visite: http://localhost:8000[/dim]
"""

    console.print(Panel(info, title="ℹ️ Informações da Interface Web", border_style="blue"))
