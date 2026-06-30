# Crypto Pair Trading Engine

An automated, high-frequency pair trading system built in Python. The project uses a multi-agent structure and has a strict interface design.

---

## 🏗️ As 3 Camadas do Projeto

Para garantir que qualquer agente ou desenvolvedor entenda o repositório em 2 minutos:

```text
1. Ambiente de Código
   IDE (VS Code/PyCharm), Python 3.12, dependências (uv), testes (pytest), lint (Ruff), Docker.

2. Ambiente de Gestão
   GitHub Projects, issues, sprints, controle de projetos (project_control/), docs.

3. Ambiente de Operação e Pesquisa
   logs estruturados, dashboards, notebooks, modelos (MLflow), dados, replay e monitoramento.
```

---

## 📂 Estrutura do Repositório

```text
Crypto-Pair-Trading/
├── pyproject.toml      # Configuração de dependências e ferramentas via uv
├── uv.lock             # Trava de dependências determinística do uv
├── Taskfile.yml        # Task runner com comandos padronizados
├── Dockerfile          # Configuração Docker do app principal
├── docker-compose.yml  # Serviços: app, Prometheus, Grafana, MLflow
├── project_control/    # Estado do projeto e controle dos agentes (PROJECT_STATE.md, etc.)
├── tasks/              # Divisão de tarefas por sprints (sprint_01 a sprint_28)
├── docs/               # Documentação técnica (MkDocs Material)
├── src/                # Código-fonte do sistema
├── tests/              # Suite de testes (pytest)
└── notebooks/          # Notebooks de pesquisa e exploração quantitativa
```

---

## ⚡ Comandos Rápidos (Taskfile)

Utilizamos o [Taskfile](https://taskfile.dev) para padronizar comandos.

| Comando | Descrição |
| :--- | :--- |
| `task install` | Instala todas as dependências usando `uv sync` |
| `task test` | Executa a suite de testes automatizados com `pytest` |
| `task lint` | Executa as validações do Ruff (linter e formatador) |
| `task format` | Formata o código e aplica correções automáticas de lint |
| `task type` | Executa a verificação estática de tipos do `pyright` |
| `task check` | Executa lint, type-check e testes sequencialmente |
| `task docs` | Inicia o servidor local de documentação MkDocs |
| `task paper` | Roda a simulação no ambiente de papel (paper engine) |

---

## 👥 Gestão de Sprints e Agentes

Toda a gestão interna do projeto está sob a pasta [project_control/](file:///C:/Users/arthu/Desktop/Aula/Projects/Crypto-Pair-Trading/project_control/).

* **Estado Geral**: [PROJECT_STATE.md](file:///C:/Users/arthu/Desktop/Aula/Projects/Crypto-Pair-Trading/project_control/PROJECT_STATE.md)
* **Sprint Atual**: [CURRENT_SPRINT.md](file:///C:/Users/arthu/Desktop/Aula/Projects/Crypto-Pair-Trading/project_control/CURRENT_SPRINT.md)
* **Quadro de Tarefas**: [TASK_BOARD.md](file:///C:/Users/arthu/Desktop/Aula/Projects/Crypto-Pair-Trading/project_control/TASK_BOARD.md)
* **Membros (Agentes)**: [AGENTS.md](file:///C:/Users/arthu/Desktop/Aula/Projects/Crypto-Pair-Trading/project_control/AGENTS.md)
* **Pontos de Decisão (ADRs)**: [DECISIONS.md](file:///C:/Users/arthu/Desktop/Aula/Projects/Crypto-Pair-Trading/project_control/DECISIONS.md)

---

## 📖 Documentação Técnica

Para ver os diagramas de máquina de estado, protocolos de recuperação e limites de risco de forma legível:

```bash
task install
task docs
```
Acesse `http://127.0.0.1:8000` no seu navegador.
