# Vigie — Agent SOC LangGraph

**Support pédagogique MSc2 Unit 3 — La Plateforme_ x Devoteam Cyber Trust**

Vigie est un agent d'assistance à la réponse à incident pour le SOC fictif d'AtlasMétaux. Il reçoit des alertes SIEM, les triage automatiquement via LLM, les enrichit avec MITRE ATT&CK, et propose des recommandations d'action — que l'analyste doit valider avant tout déploiement.

---

## Contexte du hackathon

Vous recevez ce repo **fonctionnel**. Votre mission sur 2 semaines :

1. **Diagnostiquer** les dysfonctionnements présents dans le système
2. **Corriger** les incidents détectés
3. **Documenter** vos analyses et correctifs

Aucune reconstruction from scratch. Vous travaillez comme des ingénieurs en production.

---

## Architecture

```
Alerte SIEM
    │
    ▼
POST /api/alerts
    │
    ├── Création incident (DB)
    └── Agent LangGraph (background)
            │
            ├── Node triage      → LLM → severity + techniques MITRE
            ├── Node enrichissement → Qdrant + BM25 → contexte ATT&CK
            └── Node recommandation → LLM → actions prioritisées
                        │
                        ▼
            Recommandations (status=pending)
                        │
                        ▼
POST /api/recommendations/{id}/review  ← validation humaine obligatoire
```

**Stack** : Python 3.11 · LangGraph · OpenRouter · Qdrant + BM25 + cross-encoder · FastAPI · Streamlit · PostgreSQL · Redis · Langfuse

---

## Schéma de données

```mermaid
erDiagram
    incidents {
        uuid id PK
        text status
        text severity
        text title
        text[] mitre_techniques
        timestamptz created_at
        timestamptz updated_at
    }
    alerts {
        uuid id PK
        text external_id
        text severity
        text source
        text title
        jsonb raw_payload
        uuid incident_id FK
        timestamptz received_at
    }
    agent_runs {
        uuid id PK
        uuid incident_id FK
        text run_type
        text llm_model
        int latency_ms
        text status
        timestamptz started_at
        timestamptz finished_at
    }
    recommendations {
        uuid id PK
        uuid incident_id FK
        uuid agent_run_id FK
        text content
        float confidence
        text[] mitre_refs
        text status
        timestamptz created_at
        timestamptz reviewed_at
        text reviewed_by
        text review_reason
    }
    audit_log {
        uuid id PK
        text entity_type
        uuid entity_id
        text action
        text actor
        text reason
        timestamptz created_at
    }

    incidents ||--o{ alerts : "regroupe"
    incidents ||--o{ agent_runs : "déclenche"
    incidents ||--o{ recommendations : "produit"
    agent_runs ||--o{ recommendations : "génère"
```

---

## Installation locale

### Prérequis

- Docker & Docker Compose
- Python 3.11 (mode développeur uniquement)
- Clé API OpenRouter (fournie par le formateur)

```bash
# Étape commune : variables d'environnement
cp .env.example .env
# Éditer .env : renseigner OPENROUTER_API_KEY et SESSION_SECRET_KEY
```

---

### Mode A — Tout Docker *(recommandé, zéro installation Python)*

```bash
# Lancer tous les services + API + UI
docker compose up --build

# Première fois — appliquer les migrations et charger MITRE
make up
```

| Service  | URL                        |
|----------|----------------------------|
| API      | http://localhost:8000      |
| Docs API | http://localhost:8000/docs |
| UI       | http://localhost:8501      |
| Langfuse | http://localhost:3000      |

---

### Mode B — Infra Docker, API en local *(développeur Windows/Mac)*

Les services DB, Redis, Qdrant et Langfuse tournent dans Docker et exposent leurs ports sur `localhost`. L'API et l'UI tournent directement sur la machine hôte.

```bash
# 1. Démarrer uniquement l'infrastructure
docker compose up -d db redis qdrant langfuse

# 2. Migrations + seed MITRE (première fois)
docker compose --profile init run --rm migrate
python scripts/seed_mitre.py

# 3. Installer les dépendances Python
pip install uv
uv pip install -e ".[dev]"

# 4. Lancer l'API (avec hot-reload)
uvicorn app.main:app --reload --port 8000

# 5. Lancer l'UI (autre terminal)
streamlit run streamlit_app.py
```

Ports exposés par Docker sur `localhost` :

| Service  | Port  |
|----------|-------|
| PostgreSQL | 5432 |
| Redis      | 6379 |
| Qdrant REST | 6333 |
| Qdrant gRPC | 6334 |
| Langfuse   | 3000 |

| Service  | URL                        |
|----------|----------------------------|
| API      | http://localhost:8000      |
| Docs API | http://localhost:8000/docs |
| UI       | http://localhost:8501      |
| Langfuse | http://localhost:3000      |

---

## Utilisation

### Injecter une alerte (curl)

```bash
curl -X POST http://localhost:8000/api/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "severity": "HIGH",
    "source": "wazuh",
    "title": "Brute-force SSH détecté — 200 tentatives/min",
    "raw_payload": {"src_ip": "10.0.0.42", "dst_port": 22}
  }'
# → {"incident_id": "...", "alert_id": "...", "status": "accepted"}
```

### Consulter les incidents

```bash
curl http://localhost:8000/api/incidents
curl http://localhost:8000/api/incidents/<incident_id>
```

### Valider une recommandation (obligatoire)

```bash
curl -X POST http://localhost:8000/api/recommendations/<reco_id>/review \
  -H "Content-Type: application/json" \
  -d '{
    "status": "approved",
    "reviewed_by": "votre-prenom",
    "reason": "Action validée après analyse"
  }'
```

Toute recommandation doit être validée ou rejetée par un humain avant action. C'est une exigence **non négociable** (AI Act article 14 — supervision humaine).

---

## Endpoints API

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/health` | Statut de l'API et du retriever |
| `POST` | `/api/alerts` | Ingère une alerte SIEM → crée un incident + lance l'agent (202) |
| `GET` | `/api/incidents` | Liste tous les incidents (`?limit=50&offset=0`) |
| `GET` | `/api/incidents/{id}` | Détail d'un incident + ses recommandations |
| `POST` | `/api/recommendations/{id}/review` | Valide ou rejette une recommandation (guardrail AI Act art.14) |

Documentation interactive complète : http://localhost:8000/docs

---

## Tests

```bash
# Tous les tests
pytest tests/ -v

# Unitaires seulement
pytest tests/unit/ -v

# E2E (routes HTTP)
pytest tests/e2e/ -v
```

---

## Fichiers clés

| Fichier | Rôle |
|---------|------|
| `app/agent/graph.py` | Point d'entrée de l'agent LangGraph |
| `app/agent/nodes/triage.py` | Node triage LLM |
| `app/agent/nodes/enrichissement.py` | Node retrieval MITRE |
| `app/agent/nodes/recommandation.py` | Node recommandations LLM |
| `app/adapters/retrieval/hybrid.py` | Pipeline Dense + BM25 + cross-encoder |
| `app/adapters/observability/langfuse_hooks.py` | Observabilité LLM |
| `app/core/routes/recommendations.py` | Guardrail humain AI Act art.14 |
| `app/adapters/db/migrations/001_initial.sql` | Schéma complet |
| `CARNET_DE_BORD.md` | Historique des décisions de construction |

---

## Observabilité

Langfuse trace automatiquement tous les appels LLM de l'agent. Accéder à http://localhost:3000 pour visualiser :
- Les traces par incident
- Les latences par node
- Les tokens consommés
- Les erreurs

---

## Variables d'environnement requises

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | Clé API OpenRouter (accès LLM) |
| `SESSION_SECRET_KEY` | Clé secrète session (`python -c "import secrets; print(secrets.token_urlsafe(32))"`) |
| `POSTGRES_DSN` | DSN PostgreSQL (défaut : `postgresql://vigie:vigie@localhost:5432/vigie`) |
| `LANGFUSE_PUBLIC_KEY` | Clé publique Langfuse self-hosted |
| `LANGFUSE_SECRET_KEY` | Clé secrète Langfuse self-hosted |

---

## En cas de problème

1. Vérifier que les services Docker sont up : `docker compose ps`
2. Consulter les logs : `docker compose logs api -f`
3. Tester le health check : `curl http://localhost:8000/health`
4. Vérifier Langfuse : http://localhost:3000

Si l'agent ne produit pas de recommandations après une alerte, vérifier :
- La clé OpenRouter dans `.env`
- Que le seed MITRE a bien tourné (`python scripts/seed_mitre.py`)
- Les logs structurés JSON dans le terminal de l'API
