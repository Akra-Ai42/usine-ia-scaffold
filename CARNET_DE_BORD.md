# CARNET DE BORD — Vigie v2

## 2026-11-03/04 — Pivot majeur : refonte complète (v1 → v2)

### Contexte du pivot
L'ancienne v1 (LangGraph, Postgres, Qdrant service, Redis, Langfuse, Streamlit, docker-compose) était overengineered pour un support pédagogique MSc2. Pivot validé par l'utilisateur.

---

### Brique 1 — Archive v1  ✅
- Tout l'ancien code archivé dans `_archive_v1/` (app, data, docs, scripts, tests, streamlit_app.py, docker-compose, Makefile...)
- `.env`, `.venv`, `.git`, `CLAUDE.md` conservés

### Brique 2 — Scaffold  ✅
- Structure `app/core/services`, `app/adapters`, `app/static`, `data`, `docs`
- `pyproject.toml` minimal : fastapi, uvicorn, httpx, chromadb, pydantic, python-dotenv
- `.gitignore` mis à jour

### Brique 3 — data/mitre_techniques.json  ✅
- 10 techniques MITRE ATT&CK versionnées : T1110, T1078, T1486, T1059, T1562, T1055, T1190, T1041, T1003, T1021
- Chaque technique inclut : description, detection, mitigations, severity, subtechniques, platforms

### Brique 4 — adapters/llm.py  ✅
- OpenRouter via httpx direct, timeout configurable (`LLM_TIMEOUT_S`)
- Pas de retry (sain — incident 2 sera l'injection retry infini)
- System prompt SOC en français

### Brique 5 — adapters/retrieval.py  ✅
- ChromaDB PersistentClient embedded (fichier local `data/chroma/`)
- Seed automatique au premier appel depuis `mitre_techniques.json`
- Lazy init singleton

### Brique 6 — adapters/db.py  ✅
- sqlite3 avec context manager transactionnel (rollback automatique)
- Tables : `incidents` + `audit_log`
- `review_incident` atomique (UPDATE + INSERT en une transaction)

### Brique 7 — core/services/chat.py  ✅
- Orchestration : retrieval → LLM → persist
- `requires_review = True` si technique high ou critical
- `schemas.py` Pydantic v2 créé en même temps

### Brique 8 — core/services/guardrail.py  ✅
- Validation action (`approved`/`rejected`)
- Idempotence : incident déjà traité → erreur 400
- Délègue la transaction atomique à `db.review_incident`

### Brique 9 — app/main.py  ✅
- 4 routes : POST /api/chat, POST /api/incidents/{id}/review, GET /api/incidents, GET /api/health
- Serve static + lifespan init DB

### Brique 10 — UI Win95 + CRT  ✅ (validée utilisateur)
- Chrome Windows 95 : barre titre bleue dégradée, boutons 3D asymétriques, fonte Tahoma
- Zone chat terminal CRT : fond noir `#000000`, texte vert phosphore `#00ff41`, scan lines subtiles
- Prompts `[ANALYSTE] >` et `[VIGIE] >`, curseur `▊` clignotant
- Guardrail block : `border-left: 2px solid #ffff44`, boutons `[A]pprouver [R]ejeter [D]étails`
- Icônes Tabler webfont (ti-plus, ti-list, ti-shield-check, ti-shield-lock), 0 émojis
- Sidebar incidents intégrée

### Brique 11 — Dockerfile + render.yaml + README  ✅
- Dockerfile 1 service, build simple, pas de docker-compose
- `render.yaml` Web Service Python, 1-clic Render
- README "Démarrage en 30 secondes"
- `docs/incidents-playbook.md` (gitignored) : 3 injections documentées

---

## État au 2026-11-04

| # | Brique | Statut |
|---|--------|--------|
| 1 | Archive v1 | Validée |
| 2 | Scaffold | Validée |
| 3 | MITRE JSON | Validée |
| 4 | LLM adapter | Validée |
| 5 | Retrieval ChromaDB | Validée |
| 6 | DB sqlite | Validée |
| 7 | Service chat | Validée |
| 8 | Guardrail | Validée |
| 9 | main.py routes | Validée |
| 10 | UI Win95 + CRT | Validée |
| 11 | Dockerfile + deploy | Validée |

**Commande de démarrage :** `uvicorn app.main:app --port 8000`  
**Prochaine étape possible :** tester avec une vraie `OPENROUTER_API_KEY` + préparer session d'injection incidents.
