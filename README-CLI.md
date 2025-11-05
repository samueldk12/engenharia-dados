# 🎓 Data Engineering Study CLI

CLI completa para gerenciar estudos, projetos práticos e certificações de Data Engineering.

## 📋 Índice

- [Instalação](#instalação)
- [Uso Básico](#uso-básico)
- [Comandos Disponíveis](#comandos-disponíveis)
  - [Projects](#projects)
  - [Certifications](#certifications)
  - [Progress](#progress)
  - [Tests](#tests)
  - [Benchmarks](#benchmarks)
- [Exemplos](#exemplos)
- [Estrutura de Dados](#estrutura-de-dados)

## 🚀 Instalação

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Tornar Executável (Opcional)

```bash
chmod +x study-cli.py

# Criar alias (adicione ao ~/.bashrc ou ~/.zshrc)
alias study="python3 /caminho/para/study-cli.py"
```

### 3. Verificar Instalação

```bash
python study-cli.py --version
python study-cli.py --help
```

## 💡 Uso Básico

```bash
# Listar todos os comandos
python study-cli.py --help

# Listar projetos disponíveis
python study-cli.py projects list

# Iniciar um projeto
python study-cli.py projects start netflix-clone

# Ver progresso geral
python study-cli.py progress show

# Listar certificações
python study-cli.py certs list

# Executar testes
python study-cli.py test run netflix-clone

# Executar benchmarks
python study-cli.py benchmark run netflix-clone
```

## 📚 Comandos Disponíveis

### Projects

Gerenciamento de projetos práticos e de entrevista.

#### `projects list`

Lista todos os projetos disponíveis com filtros.

```bash
# Listar todos os projetos
python study-cli.py projects list

# Filtrar por tipo
python study-cli.py projects list --type practical
python study-cli.py projects list --type interview

# Filtrar por dificuldade (1-5 estrelas)
python study-cli.py projects list --difficulty 5
```

**Saída:**
```
┌────────────────────┬──────────────────────────┬──────────┬─────────────┬─────────┬──────────────────┐
│ ID                 │ Nome                     │ Tipo     │ Dificuldade │ Tempo   │ Status           │
├────────────────────┼──────────────────────────┼──────────┼─────────────┼─────────┼──────────────────┤
│ netflix-clone      │ Netflix Clone            │ Practical│ 🔴 ⭐⭐⭐⭐⭐   │ 120 min │ ✓ Completo       │
│ log-processing     │ Log Processing System    │ Interview│ 🟢 ⭐⭐      │ 45 min  │ ⚙ Em Progresso   │
│ rate-limiter       │ Rate Limiter             │ Interview│ 🟡 ⭐⭐⭐     │ 60 min  │ ○ Não Iniciado   │
└────────────────────┴──────────────────────────┴──────────┴─────────────┴─────────┴──────────────────┘

Total: 5 | Completos: 1 | Em Progresso: 2
```

#### `projects start <project_id>`

Inicia um projeto e abre no editor.

```bash
# Iniciar projeto
python study-cli.py projects start netflix-clone

# Especificar editor
python study-cli.py projects start log-processing --editor code
python study-cli.py projects start rate-limiter --editor vim
```

**Funcionalidades:**
- Atualiza status para "Em Progresso"
- Registra sessão de estudo
- Mostra README do projeto
- Abre projeto no editor (VS Code, Vim, etc)

#### `projects complete <project_id>`

Marca um projeto como completo.

```bash
# Marcar como completo
python study-cli.py projects complete netflix-clone

# Adicionar notas
python study-cli.py projects complete log-processing --notes "Excelente para entender parsing eficiente"
```

#### `projects status [project_id]`

Mostra status detalhado de um projeto ou todos.

```bash
# Status específico
python study-cli.py projects status netflix-clone

# Status de todos
python study-cli.py projects status
```

#### `projects upload <source_path> <project_name>`

Faz upload de um novo projeto.

```bash
# Upload de projeto prático
python study-cli.py projects upload /path/to/project meu-projeto --type practical

# Upload de projeto de entrevista
python study-cli.py projects upload /path/to/project cache-system --type interview
```

---

### Certifications

Gerenciamento de certificações.

#### `certs list`

Lista todas as certificações disponíveis.

```bash
# Listar todas
python study-cli.py certs list

# Filtrar por provider
python study-cli.py certs list --provider AWS
python study-cli.py certs list --provider Databricks

# Filtrar por dificuldade
python study-cli.py certs list --difficulty 4
```

**Saída:**
```
┌─────────────────────────┬────────────────────────────────────────────┬──────────┬────────┬─────────────┬───────────┐
│ ID                      │ Nome                                       │ Provider │ Custo  │ ROI         │ Progresso │
├─────────────────────────┼────────────────────────────────────────────┼──────────┼────────┼─────────────┼───────────┤
│ aws-data-analytics      │ AWS Certified Data Analytics - Specialty   │ AWS      │ $300   │ +$10-20K    │ ✓ 100%    │
│ databricks-de-associate │ Databricks Data Engineer Associate         │ Databricks│ $200   │ +$15-30K    │ ⚙ 60%     │
└─────────────────────────┴────────────────────────────────────────────┴──────────┴────────┴─────────────┴───────────┘

Total: 4 | Certificados: 1 | Em Progresso: 2
Investimento Total: $850
```

#### `certs start <cert_id>`

Inicia o estudo de uma certificação.

```bash
# Iniciar certificação
python study-cli.py certs start aws-data-analytics

# Iniciar tópico específico
python study-cli.py certs start databricks-de-associate --topic "Delta Lake"
```

#### `certs progress [cert_id]`

Mostra progresso de uma ou todas certificações.

```bash
# Progresso específico
python study-cli.py certs progress aws-data-analytics

# Progresso detalhado (por tópico)
python study-cli.py certs progress databricks-de-associate --detailed

# Todas as certificações
python study-cli.py certs progress
```

**Saída detalhada:**
```
AWS Certified Data Analytics - Specialty ████████████░░░░░░░░  60%

Tópicos:
  ✓ 1. Collection (18%)
  ✓ 2. Storage (22%)
  ✓ 3. Processing (24%)
  ○ 4. Analysis (18%)
  ○ 5. Security (18%)

┌─────────────────────────┐
│   📊 Estatísticas       │
├─────────────────────────┤
│ Status: In Progress     │
│ Sessões de estudo: 12   │
│ Tópicos completos: 3/5  │
│ Progresso: 60.0%        │
│ Iniciado em: 2024-01-15 │
└─────────────────────────┘
```

#### `certs complete-topic <cert_id> <topic>`

Marca um tópico como completo.

```bash
python study-cli.py certs complete-topic aws-data-analytics "Collection"
python study-cli.py certs complete-topic databricks-de-associate "Spark SQL"
```

#### `certs certified <cert_id>`

Marca certificação como obtida.

```bash
# Simples
python study-cli.py certs certified aws-data-analytics

# Com score
python study-cli.py certs certified databricks-de-associate --score 85

# Com data específica
python study-cli.py certs certified aws-data-analytics --score 88 --date 2024-01-20
```

---

### Progress

Gerenciamento de progresso geral.

#### `progress show`

Mostra resumo geral de progresso.

```bash
# Ver progresso
python study-cli.py progress show

# Exportar para JSON
python study-cli.py progress show --export meu-progresso.json
```

**Saída:**
```
┌────────────────────────────────────────┐
│      Resumo Geral de Estudos          │
├────────────────────────────────────────┤
│ 📁 Projetos:                           │
│   • Total: 5                           │
│   • Completos: 2                       │
│   • Em Progresso: 2                    │
│   • Não Iniciados: 1                   │
│                                        │
│ 🎓 Certificações:                      │
│   • Total: 4                           │
│   • Certificado: 1                     │
│   • Pronto para Exame: 1               │
│   • Estudando: 1                       │
│   • Não Iniciados: 1                   │
│                                        │
│ 📚 Sessões de Estudo:                  │
│   • Total de sessões: 45               │
│                                        │
│ Última atualização: 2024-01-20 15:30   │
└────────────────────────────────────────┘

Atividade Recente:

  📁 netflix-clone - Completed - 2024-01-20 14:30
  🎓 aws-data-analytics - Processing - 2024-01-20 10:15
  📁 log-processing - In Progress - 2024-01-19 16:45
```

#### `progress stats`

Mostra estatísticas detalhadas.

```bash
python study-cli.py progress stats
```

#### `progress backup [output_path]`

Cria backup do progresso.

```bash
# Backup automático
python study-cli.py progress backup

# Backup em local específico
python study-cli.py progress backup /path/to/backup.json
```

#### `progress import <file_path>`

Importa progresso de arquivo JSON.

```bash
# Substituir completamente
python study-cli.py progress import backup.json

# Fazer merge com existente
python study-cli.py progress import backup.json --merge
```

#### `progress reset`

Reseta todo o progresso (com backup automático).

```bash
# Com confirmação interativa
python study-cli.py progress reset

# Confirmar direto
python study-cli.py progress reset --confirm
```

---

### Tests

Execução e gerenciamento de testes.

#### `test run <project_name>`

Executa testes de um projeto.

```bash
# Executar todos os testes
python study-cli.py test run netflix-clone

# Verbose
python study-cli.py test run log-processing -v

# Com cobertura
python study-cli.py test run netflix-clone --coverage

# Padrão específico
python study-cli.py test run netflix-clone --pattern "test_video*"
```

#### `test list <project_name>`

Lista todos os testes disponíveis.

```bash
python study-cli.py test list netflix-clone
```

**Saída:**
```
Testes disponíveis em netflix-clone:

  📄 test_video_transcoder.py
     └─ test_create_video_profile
     └─ test_generate_ffmpeg_command
     └─ test_transcode_video
     └─ test_generate_hls_playlist

  📄 test_recommendations.py
     └─ test_matrix_factorization
     └─ test_train_model
     └─ test_predict
```

#### `test watch <project_name>`

Watch mode - executa testes automaticamente quando arquivos mudam.

```bash
python study-cli.py test watch netflix-clone
```

#### `test coverage <project_name>`

Gera relatório de cobertura.

```bash
# Terminal
python study-cli.py test coverage netflix-clone

# HTML (abre no navegador)
python study-cli.py test coverage netflix-clone --html
```

#### `test create <project_name> <module_name>`

Cria novo arquivo de teste com template.

```bash
python study-cli.py test create log-processing parser
python study-cli.py test create rate-limiter token_bucket
```

---

### Benchmarks

Execução de benchmarks de performance.

#### `benchmark run <project_name>`

Executa benchmarks de performance.

```bash
# Todos os benchmarks
python study-cli.py benchmark run netflix-clone

# Benchmark específico
python study-cli.py benchmark run netflix-clone -b recommendations

# Especificar iterações
python study-cli.py benchmark run log-processing -n 10000
```

**Saída:**
```
Executando: benchmark_recommendations.py
────────────────────────────────────────────────────────────

Running 10000 iterations...
Progress: 0/10000
Progress: 100/10000
...

============================================================
              Benchmark Results
============================================================
Mean latency:      0.85 ms
Median latency:    0.82 ms
P50 latency:       0.82 ms
P95 latency:       1.23 ms
P99 latency:       1.67 ms
Min latency:       0.45 ms
Max latency:       5.32 ms
Std deviation:     0.34 ms
============================================================
✅ PASS: P99 latency (1.67ms) < target (10.0ms)
```

#### `benchmark list <project_name>`

Lista benchmarks disponíveis.

```bash
python study-cli.py benchmark list netflix-clone
```

#### `benchmark profile <project_name> <script_path>`

Perfila um script específico.

```bash
# CPU profiling
python study-cli.py benchmark profile netflix-clone src/transcoder.py

# Memory profiling
python study-cli.py benchmark profile netflix-clone src/transcoder.py --memory
```

#### `benchmark create <project_name> <benchmark_name>`

Cria novo benchmark com template.

```bash
python study-cli.py benchmark create log-processing parser_speed
python study-cli.py benchmark create rate-limiter throughput
```

---

## 📖 Exemplos de Workflows

### Workflow 1: Começar um Novo Projeto

```bash
# 1. Listar projetos disponíveis
python study-cli.py projects list

# 2. Iniciar projeto
python study-cli.py projects start log-processing --editor code

# 3. Executar testes
python study-cli.py test run log-processing

# 4. Executar benchmarks
python study-cli.py benchmark run log-processing

# 5. Marcar como completo
python study-cli.py projects complete log-processing --notes "Aprendi muito sobre parsing eficiente"

# 6. Ver progresso
python study-cli.py progress show
```

### Workflow 2: Estudar para Certificação

```bash
# 1. Listar certificações
python study-cli.py certs list

# 2. Iniciar certificação
python study-cli.py certs start aws-data-analytics

# 3. Estudar tópicos e marcar como completo
python study-cli.py certs complete-topic aws-data-analytics "Collection"
python study-cli.py certs complete-topic aws-data-analytics "Storage"
python study-cli.py certs complete-topic aws-data-analytics "Processing"

# 4. Ver progresso
python study-cli.py certs progress aws-data-analytics --detailed

# 5. Quando passar no exame
python study-cli.py certs certified aws-data-analytics --score 88
```

### Workflow 3: Desenvolvimento com TDD

```bash
# 1. Criar teste
python study-cli.py test create meu-projeto my_module

# 2. Watch mode (TDD)
python study-cli.py test watch meu-projeto

# (Editar código e ver testes rodarem automaticamente)

# 3. Cobertura
python study-cli.py test coverage meu-projeto --html
```

### Workflow 4: Otimização de Performance

```bash
# 1. Criar benchmark
python study-cli.py benchmark create meu-projeto query_performance

# 2. Executar benchmark inicial
python study-cli.py benchmark run meu-projeto -b query_performance

# 3. Profile para identificar gargalos
python study-cli.py benchmark profile meu-projeto src/query.py

# 4. Otimizar código...

# 5. Executar benchmark novamente
python study-cli.py benchmark run meu-projeto -b query_performance

# 6. Comparar resultados
```

---

## 🗂️ Estrutura de Dados

### Arquivo de Progresso (`.data/progress.json`)

```json
{
  "projects": {
    "netflix-clone": {
      "status": "completed",
      "started_at": "2024-01-15T10:30:00",
      "completed_at": "2024-01-20T15:45:00",
      "sessions": [
        {
          "started_at": "2024-01-15T10:30:00",
          "completed_at": "2024-01-15T12:30:00"
        }
      ],
      "notes": "Excelente projeto para entender video streaming"
    },
    "log-processing": {
      "status": "in_progress",
      "started_at": "2024-01-18T09:00:00",
      "sessions": [
        {
          "started_at": "2024-01-18T09:00:00"
        }
      ]
    }
  },
  "certifications": {
    "aws-data-analytics": {
      "status": "certified",
      "started_at": "2024-01-01T08:00:00",
      "certified_at": "2024-01-20T14:30:00",
      "score": 88,
      "completed_topics": [
        "Collection",
        "Storage",
        "Processing",
        "Analysis",
        "Security"
      ],
      "study_sessions": [
        {
          "started_at": "2024-01-01T08:00:00",
          "topic": "Collection"
        }
      ]
    }
  },
  "last_updated": "2024-01-20T15:45:00"
}
```

### Arquivo de Configuração (`.data/config.json`)

```json
{
  "default_editor": "code",
  "show_hints": true,
  "auto_save_progress": true
}
```

---

## 🎯 Recursos Avançados

### Integração com Git

A CLI mantém seus dados em `.data/`, que pode ser versionado ou ignorado:

```bash
# Adicionar ao .gitignore se quiser progresso local
echo ".data/" >> .gitignore

# Ou versionar para compartilhar entre máquinas
git add .data/progress.json
git commit -m "Update study progress"
```

### Backup Automático

Sempre que você usar `progress reset`, um backup é criado automaticamente:

```
.data/progress_backup_20240120_153000.json
```

### Export/Import para Compartilhar

```bash
# Exportar seu progresso
python study-cli.py progress show --export meu-progresso.json

# Compartilhar com colega
# Colega importa com merge
python study-cli.py progress import meu-progresso.json --merge
```

---

## 🐛 Troubleshooting

### Erro: `pytest not found`

```bash
pip install pytest pytest-cov pytest-watch
```

### Erro: `click module not found`

```bash
pip install -r requirements.txt
```

### Progresso não está salvando

Verifique permissões do diretório `.data/`:

```bash
ls -la .data/
chmod 755 .data/
```

### Editor não abre

Configure o editor manualmente:

```bash
python study-cli.py projects start netflix-clone --editor /usr/bin/code
```

---

## 🚀 Próximos Passos

1. **Explore os projetos**: `python study-cli.py projects list`
2. **Comece um projeto**: `python study-cli.py projects start <project-id>`
3. **Veja seu progresso**: `python study-cli.py progress show`
4. **Estude para certificações**: `python study-cli.py certs list`

---

## 📞 Suporte

- **Documentação dos Projetos**: Veja os READMEs em cada pasta de projeto
- **Guias de Certificação**: Veja `11-certificacoes/`
- **Issues**: Crie uma issue no repositório

---

## 📝 Licença

Este projeto é parte do repositório de estudos de Data Engineering.

---

**Bons estudos! 🚀📚**
