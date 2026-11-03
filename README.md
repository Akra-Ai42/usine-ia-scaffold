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

## Installation locale

### Prérequis

- Python 3.11
- Docker & Docker Compose
- Clé API OpenRouter (fournies par le formateur)

### Démarrage

```bash
# 1. Cloner le repo
git clone <url-repo> vigie-prod
cd vigie-prod

# 2. Variables d'environnement
cp .env.example .env
# Éditer .env : renseigner OPENROUTER_API_KEY et SESSION_SECRET_KEY

# 3. Lancer les services (DB, Redis, Qdrant, Langfuse)
docker compose up -d db redis qdrant langfuse

# 4. Appliquer le schéma DB
docker compose --profile init up migrate
# ou en local : python -m app.adapters.db.migrate

# 5. Charger les techniques MITRE ATT&CK dans Qdrant
python scripts/seed_mitre.py

# 6. Installer les dépendances Python
pip install uv
uv pip install -e ".[dev]"

# 7. Lancer l'API
uvicorn app.main:app --reload --port 8000

# 8. Lancer l'UI (autre terminal)
streamlit run streamlit_app.py
```

### Tout en Docker

```bash
docker compose up --build
```

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
