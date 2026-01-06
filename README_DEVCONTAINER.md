# DevContainer Setup for deepagents-quickstarts

Questa guida descrive come configurare un DevContainer production-ready per lo sviluppo locale sicuro, con integrazione 1Password + direnv.

## Setup Iniziale (First Time)

```bash
# Step 1: Autenticare 1Password CLI
op account add

# Step 2: Verificare accesso vault
op vault list

# Step 3: Popolare vault con le API keys
# - Anthropic: https://console.anthropic.com/account/keys
# - OpenAI: https://platform.openai.com/account/api-keys
# - Tavily: https://app.tavily.com/home
# - LangSmith: https://smith.langchain.com/settings

# Step 4: Aprire in VS Code
code .
# Selezionare "Reopen in Container"

# Step 5: Permettere direnv

direnv allow
```

## Workflow Development Quotidiano

```bash
# Avviare LangGraph server
cd deep_research
langgraph dev

# In un altro terminale: Jupyter notebook
jupyter notebook --ip=0.0.0.0

# Testare l'agent
python -c "from deep_research import agent; print(agent)"
```

## Troubleshooting

### direnv non carica le variabili
- Verifica di aver eseguito `direnv allow` nella root del repo.
- Assicurati che `.envrc` esista e sia leggibile.

### 1Password CLI authentication expired
- Esegui di nuovo `op account add` oppure `op signin`.
- Verifica l'accesso con `op vault list`.

### Porta 2024 già in uso
- Chiudi il processo che usa la porta o avvia LangGraph su un'altra porta.
- Verifica con `lsof -i :2024`.

### Module not found errors
- Assicurati di aver eseguito `uv sync`.
- Se necessario, entra in `deep_research` e riesegui `uv sync`.

## Note

- Isolamento completo: tutto gira nel container, zero impatto sul Mac host.
- Performance: Docker layer caching per rebuild veloci.
- Compatibilità: Mac, Linux, Windows, GitHub Codespaces.
- Team-friendly: chiunque può clonare e avviare in pochi minuti.
- Audit trail: 1Password traccia ogni accesso alle secrets.
