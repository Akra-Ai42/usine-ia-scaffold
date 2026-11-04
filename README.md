# Vigie

Chatbot RAG SOC pédagogique MITRE ATT&CK — MSc2 La Plateforme_ x Devoteam.

---

## Démarrage en 30 secondes

```bash
# 1. Cloner
git clone <url> && cd vigie

# 2. Environnement
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# ou : .venv\Scripts\activate   # PowerShell

# 3. Dépendances
pip install fastapi "uvicorn[standard]" httpx chromadb pydantic python-dotenv

# 4. Variable d'environnement
cp .env.example .env
# Renseigner OPENROUTER_API_KEY dans .env

# 5. Lancer
uvicorn app.main:app --port 8000

# Ouvrir http://localhost:8000
```

---

## Avec Docker

```bash
docker build -t vigie .
docker run -p 8000:8000 -e OPENROUTER_API_KEY=sk-or-... vigie
```

---

## Stack

| Composant | Technologie |
|-----------|-------------|
| API       | FastAPI + uvicorn |
| Vectors   | ChromaDB embedded (fichier local) |
| LLM       | OpenRouter via httpx (pas de LangChain) |
| DB        | sqlite3 stdlib |
| UI        | HTML + CSS + JS vanilla |
| MITRE     | `data/mitre_techniques.json` versionné |

---

## Architecture

```
app/
├── main.py                  Routes FastAPI + serve static
├── core/
│   ├── schemas.py           Pydantic models
│   └── services/
│       ├── chat.py          Orchestration retrieval + LLM + persist
│       └── guardrail.py     Validation humaine AI Act art.14
└── adapters/
    ├── llm.py               OpenRouter via httpx
    ├── retrieval.py         ChromaDB wrapper
    └── db.py                sqlite3 (incidents + audit log)
```

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | — | **Obligatoire** |
| `OPENROUTER_MODEL` | `anthropic/claude-3-haiku` | Modèle OpenRouter |
| `LLM_MAX_TOKENS` | `1024` | Tokens max par réponse |
| `LLM_TIMEOUT_S` | `30` | Timeout LLM en secondes |

---

## API

| Méthode | Route | Description |
|---|---|---|
| GET | `/` | UI chatbot |
| POST | `/api/chat` | Analyser un incident |
| GET | `/api/incidents` | Lister les incidents |
| POST | `/api/incidents/{id}/review` | Approuver / rejeter (guardrail) |
| GET | `/api/health` | Health check |

---

## Déploiement Render

1. Forker le repo sur GitHub
2. Render > New Web Service > connecter le repo
3. Render détecte `render.yaml` automatiquement
4. Ajouter `OPENROUTER_API_KEY` dans les variables d'env Render
5. Deploy

---

## Contexte pédagogique

Ce repo est livré **sans bugs** (code source sain, approche B stricte).  
Les 3 incidents à injecter sont documentés dans `docs/incidents-playbook.md` (gitignored, fourni séparément).
