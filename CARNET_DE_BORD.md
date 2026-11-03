# Carnet de bord — Vigie

## Brique 1 — Scaffold + DB schema + Pydantic schemas  (2026-11-04)

**Décision** : arborescence hexagonale centre + adapters, PostgreSQL 5 tables, Pydantic v2 strict.

**Livrable** :
- Structure `app/` complète (config, logger, core/schemas, adapters/db, adapters/cache, adapters/llm)
- Schéma SQL `001_initial.sql` avec 5 tables : alerts, incidents, agent_runs, recommendations, audit_log
- Schemas Pydantic v2 pour toutes les entités + tests unitaires passants
- `pyproject.toml` avec toutes les dépendances pinées

**Alternatives écartées** :
- SQLAlchemy ORM → écarté (SQL brut suffisant, moins de magie pour les étudiants)
- Alembic → écarté (script de migration custom plus lisible pour le cours)

## Brique 2 — Retrieval hybride Qdrant + BM25 + cross-encoder  (2026-11-05)

**Décision** : pipeline Dense → Sparse → RRF Fusion → Cross-encoder reranking. Embedding : `BAAI/bge-small-en-v1.5` (384 dims, rapide). Cross-encoder : `cross-encoder/ms-marco-MiniLM-L-6-v2`.

**Livrable** :
- `app/adapters/retrieval/` : 6 modules (models, qdrant_store, bm25_store, cross_encoder, hybrid, mitre)
- `scripts/seed_mitre.py` : fetch MITRE CTI → parse 200+ techniques → Qdrant + BM25
- BM25 persisté via pickle dans `data/bm25_index.pkl`
- Tests unitaires avec mocks (pas de Qdrant réel)

**Alternatives écartées** :
- Weighted score fusion → écarté (RRF plus robuste, pas de calibration manuelle)
- Sub-techniques MITRE → écarté du seed initial (trop granulaire, ajouter en Brique 5+)

## Brique 3 — Agent LangGraph v1  (2026-11-03)

**Décision** : graphe linéaire START → triage → enrichissement → recommandation → END. LLM appelé lazily dans chaque node (pas d'eager init). État TypedDict plat pour compatibilité LangGraph.

**Livrable** :
- `app/agent/state.py` : `AgentState` TypedDict
- `app/agent/nodes/triage.py` : node triage avec structured output Pydantic (`TriageLLMOutput`)
- `app/agent/nodes/enrichissement.py` : node retrieval hybride (skip si erreur upstream)
- `app/agent/nodes/recommandation.py` : node recommandations avec structured output (skip si erreur)
- `app/agent/graph.py` : `build_graph(retriever)` + `run_agent()` entry point
- `tests/unit/test_agent.py` : 8 tests unitaires passants (18/18 suite complète)

**Alternatives écartées** :
- Eager init LLM dans la factory → écarté (impossible à mocker sans vrai OpenRouter)
- Mocker au niveau chain `__or__` → écarté (trop fragile), mock au niveau node factory
- Branches conditionnelles dans le graphe → écarté (guard inline dans chaque node, plus lisible)

## Brique 4 — FastAPI endpoints + Streamlit UI minimale  (2026-11-03)

**Décision** : agent lancé en BackgroundTask (202 Accepted) pour ne pas bloquer l'ingestion. Guardrail AI Act art.14 : toutes les recommandations naissent `pending`, chaque review insère dans `audit_log`. Retriever initialisé au lifespan avec fallback gracieux si Qdrant/BM25 absent.

**Livrable** :
- `app/core/services/incident_service.py` : CRUD SQL brut (incidents, alerts, agent_runs, recommendations, audit_log)
- `app/core/services/agent_service.py` : orchestration run_agent → DB
- `app/core/routes/alerts.py` : `POST /api/alerts` → 202 + background agent
- `app/core/routes/incidents.py` : `GET /api/incidents` + `GET /api/incidents/{id}`
- `app/core/routes/recommendations.py` : `POST /api/recommendations/{id}/review`
- `app/main.py` mis à jour : lifespan retriever + include_router
- `streamlit_app.py` : dashboard incidents + détail + approve/reject

**Alternatives écartées** :
- Attendre l'agent de façon synchrone → écarté (latence LLM inacceptable sur POST /alerts)
- ORM SQLAlchemy → écarté (SQL brut plus lisible pour les étudiants, schema simple)

## Brique 5 — Langfuse hooks + Dockerfile + docker-compose e2e  (2026-11-03)

**Décision** : Langfuse câblé comme LangChain CallbackHandler dans `run_agent()`, gracieux si clés absentes. Même image Docker pour API et UI (CMD overridé en compose). Service `migrate` en `profile: init` pour ne pas tourner à chaque `up`.

**Livrable** :
- `app/adapters/observability/langfuse_hooks.py` : singleton client + callback builder + flush
- `app/agent/graph.py` mis à jour : `RunnableConfig(callbacks=[langfuse_cb])` si clés présentes
- `app/main.py` mis à jour : `flush_langfuse()` au shutdown
- `Dockerfile` : python:3.11-slim + uv, couche deps cacheable
- `docker-compose.yml` : db, redis, qdrant, langfuse-db, langfuse, api, ui, migrate (profile init)
- `runtime.txt`, `Procfile` pour Render
- `pyproject.toml` : fix psycopg `>=3.2.10` (3.2.3 n'existe pas)

**Alternatives écartées** :
- Langfuse SDK décorators `@observe` → écarté (callback LangChain plus transparent pour les étudiants)
- Image séparée pour Streamlit → écarté (même image, CMD overridé, moins de maintenance)
- Service migrate auto au startup → écarté (profile init, évite migration accidentelle)

## Brique 6 — Tests e2e + README étudiants  (2026-11-03)

**Décision** : tests e2e via httpx AsyncClient + ASGITransport (pas de vraie DB), mocks au niveau service. README orienté opérateur SOC, pas développeur : commandes directement utilisables, tableau fichiers clés, exigences AI Act expliquées.

**Livrable** :
- `tests/e2e/test_api.py` : 13 tests e2e (health, POST alert, GET incidents, GET detail, review ×4)
- `README.md` réécrit : setup, utilisation curl, fichiers clés, observabilité, troubleshooting
- Suite complète : **31/31 tests passants**

**Alternatives écartées** :
- Tests e2e avec vraie DB (postgres en CI) → écarté pour ce sprint (complexité setup, Docker non dispo en test)
- README développeur → écarté (les étudiants sont des opérateurs SOC, pas des contributeurs du repo)

## Brique 7 — Playbook incidents  (2026-11-03)

**Décision** : approche B stricte — code source 100% sain, injections documentées dans `docs/incidents-playbook.md` (gitignored). 3 incidents conçus pour être découvrables via Langfuse + logs + DB, ni trop évidents ni trop subtils.

**Livrable** : `docs/incidents-playbook.md` (gitignored, formateur uniquement)

| # | Incident | Fichier injecté | Mécanisme |
|---|----------|----------------|-----------|
| 1 | Dérive sémantique | `hybrid.py` | rank ignoré dans RRF fusion sparse → BM25 domine |
| 2 | Facture OpenRouter | `openrouter.py` + `agent_service.py` | timeout=1.5s + retry loop ×25 sans backoff |
| 3 | Bypass AI Act art.14 | `agent_service.py` | auto-approve si confiance ≥ 0.75, audit_log non écrit |
