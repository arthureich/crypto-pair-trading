# Crypto Pair Trading Engine

Welcome to the Crypto Pair Trading Engine documentation. This repository is structured into **3 Layers** to facilitate onboarding and maintain clean interfaces.

---

## 🏗️ As 3 Camadas do Projeto

### 1. Ambiente de Código
IDE, Python, dependências, testes, lint, Docker.
* **Ferramentas**: `uv`, `Ruff`, `pyright`, `pytest`, `pre-commit`, `Taskfile`

### 2. Ambiente de Gestão
GitHub Projects, issues, sprints, project_control, docs.
* **Ferramentas**: `project_control/` files, `MkDocs Material`

### 3. Ambiente de Operação e Pesquisa
logs, dashboards, notebooks, modelos, dados, replay e monitoramento.
* **Ferramentas**: `docker-compose` (Prometheus, Grafana, MLflow), SQLite

---

## ⚡ Comandos Rápidos

O projeto utiliza o **Taskfile** para padronizar todos os comandos comuns:

* **Instalar dependências**: `task install`
* **Rodar suite de testes**: `task test`
* **Validar Lint e Formatação**: `task lint`
* **Formatar Código**: `task format`
* **Checar Tipagem**: `task type`
* **Rodar todos os checks**: `task check`
* **Servir Documentação Localmente**: `task docs`
* **Rodar engine de Simulação (Paper)**: `task paper`

---

## 📂 Estrutura do Repositório

```text
project-root/
    pyproject.toml      # Configuração do projeto e dependências via uv
    uv.lock             # Trava de dependências determinística do uv
    Taskfile.yml        # Task runner com comandos padronizados
    Dockerfile          # Dockerfile otimizado com uv
    docker-compose.yml  # Docker Compose contendo app, Prometheus, Grafana e MLflow
    project_control/    # Estado do projeto e controle dos agentes
    docs/               # Documentação MkDocs Material
    src/                # Código-fonte
    tests/              # Testes automatizados (pytest)
```
