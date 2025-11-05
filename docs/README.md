# 📖 GitHub Pages - Engenharia de Dados

Este diretório contém o site estático do projeto, hospedado via GitHub Pages.

## 🌐 Acesso

O site está disponível em: **https://samueldk12.github.io/engenharia-dados/**

## 📁 Estrutura

```
docs/
├── index.html          # Landing page principal
├── web-app.html        # Link para aplicação web local
├── _config.yml         # Configuração do Jekyll
├── assets/
│   ├── css/
│   │   └── style.css   # Estilos do site
│   ├── js/
│   │   └── main.js     # JavaScript interativo
│   └── images/         # Imagens e assets
├── projects/           # Páginas dos projetos
└── certifications/     # Páginas das certificações
```

## 🚀 Funcionalidades

### Landing Page
- Hero section com estatísticas
- Grid de projetos práticos e de entrevista
- Showcasecertificações
- Demo da CLI
- Design responsivo e moderno

### Recursos Visuais
- Gradientes animados
- Animações suaves (fade-in, slide)
- Terminal interativo com animação de digitação
- Cards hover com transformações
- Tema escuro em algumas seções

### Interatividade
- Smooth scroll para navegação
- Intersection Observer para animações
- Contador animado para estatísticas
- Menu responsivo para mobile
- Easter egg: Konami Code 🎮

## 🛠️ Desenvolvimento Local

Para testar o site localmente:

```bash
# Opção 1: Servidor Python simples
cd docs
python -m http.server 8080

# Opção 2: Live Server (VS Code extension)
# Instale "Live Server" e clique com botão direito em index.html

# Opção 3: Usar a aplicação web completa
python study-cli.py web start
```

## 🎨 Design

O site usa:
- **Cores primárias**: Gradientes de roxo/azul (#667eea → #764ba2)
- **Typography**: Inter font family
- **Framework CSS**: Vanilla CSS com variáveis CSS
- **Ícones**: Font Awesome 6
- **Animações**: CSS transitions e keyframes
- **Layout**: CSS Grid e Flexbox

## 📱 Responsividade

O site é totalmente responsivo:
- **Desktop**: Layout completo com grid multi-colunas
- **Tablet**: Grid adaptativo (2 colunas)
- **Mobile**: Layout em coluna única, sidebar colapsada

## 🔧 Customização

### Alterar Cores

Edite as variáveis CSS em `assets/css/style.css`:

```css
:root {
    --primary: #6366f1;
    --secondary: #8b5cf6;
    --success: #10b981;
    /* ... */
}
```

### Adicionar Páginas

1. Crie um novo arquivo `.html` em `docs/`
2. Use o mesmo layout base de `index.html`
3. Adicione link na navegação

### Modificar Conteúdo

O conteúdo está em HTML semântico:
- Seções claramente delimitadas
- Classes BEM-like para CSS
- Comentários explicativos

## 🚀 Deploy

O deploy é automático via GitHub Actions:

1. **Trigger**: Push para `main`/`master` que modifica `docs/`
2. **Build**: GitHub Actions prepara os arquivos
3. **Deploy**: Publica para GitHub Pages
4. **URL**: https://samueldk12.github.io/engenharia-dados/

### Configurar GitHub Pages

No repositório GitHub:
1. Vá em **Settings** → **Pages**
2. Source: **GitHub Actions**
3. O workflow `.github/workflows/gh-pages.yml` cuida do resto

## 📊 Analytics

Para adicionar Google Analytics:

1. Obtenha um ID de tracking (G-XXXXXXXXXX)
2. Edite `_config.yml`:
   ```yaml
   google_analytics: G-XXXXXXXXXX
   ```
3. Adicione o script no `<head>` de index.html

## 🔗 Links Importantes

- **GitHub Repo**: https://github.com/samueldk12/engenharia-dados
- **Web App Local**: Execute `python study-cli.py web start`
- **CLI Docs**: [README-CLI.md](../README-CLI.md)
- **Main README**: [README.md](../README.md)

## 📝 Licença

Este projeto é open source. Sinta-se livre para usar, modificar e distribuir.

---

**Construído com ❤️ para Data Engineers**
