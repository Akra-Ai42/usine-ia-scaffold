# CLAUDE.md — Vigie (via usine-ia-scaffold)

Ce fichier donne à Claude Code les règles pour construire **Vigie** en semi-autonomie. Lis-le en premier. **Avance sans me demander à chaque étape.**

---

## 🎯 Contexte en 3 lignes

- **Vigie** = sujet pédagogique MSc2 Unit 3, La Plateforme_ x Devoteam Cyber Trust.
- Format : hackathon incident response 2 semaines, agent LangGraph pour SOC AtlasMétaux.
- Les étudiants reçoivent un repo `vigie-prod` fonctionnel, diagnostiquent et corrigent **3 incidents injectés**, sans tout reconstruire.

---

## 🔒 Stack verrouillée — NON négociable

```
Python 3.11 + uv
LangGraph                     (orchestration agent)
OpenRouter                    (LLM gateway)
Qdrant + rank_bm25 + cross-encoder  (retrieval hybride)
MITRE ATT&CK                  (framework référence)
FastAPI + Streamlit           (API + UI)
PostgreSQL + Redis            (persistence + cache)
Langfuse self-hosted          (observability LLM)
Docker                        (packaging)
Mailtrap.io                   (emails étudiants fictifs)
```

**Aucune nouvelle dépendance sans validation explicite.** Pas de FastAPI → Flask, pas de Qdrant → Chroma, pas de LangGraph → LlamaIndex. Si tu as un doute, choisis la lib principale de la stack et avance.

---

## 🧨 Les 3 incidents à injecter (approche B stricte)

**Rappel approche B** : code source 100% sain pendant le dev. Points d'injection documentés dans un **playbook privé non versionné** (`.gitignore`). Les étudiants reçoivent le repo SAIN d'abord ; les injections sont appliquées par le formateur juste avant le hackathon.

| # | Incident | Deadline fictive | Pattern |
|---|---|---|---|
| 1 | Dérive sémantique des recommandations | 72h | retrieval qui dévie lentement, SHAP qui ment |
| 2 | Facture OpenRouter qui s'emballe | Vendredi S+1 | boucle de retry mal cadrée, pas de rate limit |
| 3 | Bypass AI Act article 14 (47 actions auto non supervisées) | 10 jours ouvrés | guardrail humain contourné, logs incomplets |

Design détaillé des 3 incidents : voir `docs/incidents-playbook.md` (gitignored).

---

## ✅ RÈGLES DE DÉLÉGATION — ZICO

### 🟢 Avance SEUL sur

- **Scaffolding, boilerplate, structure de dossiers** (suis les patterns de l'usine-ia-scaffold)
- **Tests unitaires, fixtures, mocks**
- **Docstrings, commentaires, README de modules**
- **Refactoring interne** qui ne change pas le contrat API ou le schéma DB
- **Choix de nommage** (variables, fonctions, fichiers) — reste cohérent avec la stack Python/snake_case
- **Formatters et linters** (ruff, black, mypy configs par défaut)
- **Dockerfile et docker-compose** standards pour la stack verrouillée
- **Dependency pinning** dans `pyproject.toml` (versions mineures)
- **Logs structurés** (format JSON, niveau INFO par défaut)
- **Gestion d'erreurs standard** (try/except typés, pas de bare except)

### 🟡 Demande validation sur

- **Changement de contrat API** (nouvelle route, breaking change de payload)
- **Changement de schéma DB** (nouvelle table, migration destructive)
- **Ajout d'une dépendance externe** (nouvelle lib, service tiers)
- **Choix d'un design pattern structurant** (nouveau layer, nouveau concept d'archi)
- **Design des 3 incidents** (comment précisément l'injecter sans que ce soit trop évident OU trop subtil)
- **Fin de chaque brique** (checkpoint obligatoire)

### 🔴 N'AVANCE JAMAIS SANS Zico

- Reformuler la **pédagogie** (ce que les étudiants doivent apprendre)
- Changer l'une des **8 décisions verrouillées 27/10**
- Modifier la **grille jury**
- Toucher aux **comptes réels** (OpenRouter, Mailtrap, GitHub)
- Faire un `git push` sur le repo public `vigie-prod`

---

## 📋 Format de rapport — fin de brique

**Pas de blabla. 3 bullets max.**

```markdown
### Brique X — [NOM]  (statut: ✅ terminée / ⚠️ bloquée)

1. **Fait** : [en 1 phrase]
2. **Décidé seul** : [points d'autonomie à titre d'info]
3. **Bloquant** : [rien, ou 1 question précise]
```

**Exemple** :
```markdown
### Brique 3 — Retrieval hybride Qdrant + BM25  (statut: ✅)

1. **Fait** : wiring Qdrant + rank_bm25 + cross-encoder, tests passants, latence p95 < 400ms sur 1000 docs seed.
2. **Décidé seul** : chunk size 512 tokens avec overlap 50, embedding model `bge-m3` via OpenRouter.
3. **Bloquant** : rien.
```

**Si bloqué** : stoppe, rapporte, attends. Ne devine pas.

---

## ⏱️ Rythme de travail — semaine 2 (4-10 nov)

**Objectif** : Vigie v1 fonctionnelle en fin de semaine, prête pour injection d'incidents en semaine 3.

### Sprint

Avance par **jour entier**, pas tâche par tâche. En fin de journée, 1 rapport consolidé des briques finies.

| Jour | Objectif |
|------|---------|
| Lun 4 | Scaffold Vigie dans l'usine, DB schema, modèles Pydantic |
| Mar 5 | Retrieval Qdrant + BM25 + cross-encoder, seed data MITRE |
| Mer 6 | Agent LangGraph v1 (nodes principaux : triage, enrichissement, recommandation) |
| Jeu 7 | FastAPI endpoints + Streamlit UI minimale |
| Ven 8 | Langfuse hooks, Dockerfile, docker-compose e2e |
| Sam-Dim | Tampon + tests end-to-end + README étudiants |

**Checkpoint Zico** : dimanche 10 nov, 1 rapport global de la semaine (pas plus).

---

## 🚫 Pièges à éviter

- **Pas d'overengineering**. Vigie est un support pédagogique, pas une plateforme SaaS. 10 lignes qui marchent battent 100 lignes "scalables".
- **Pas d'abstractions prématurées**. Si tu écris une interface pour 1 seul implémenteur, tu as écrit du code mort.
- **Pas de "TODO" dans le code livré**. Soit tu fais, soit tu l'ajoutes à `BACKLOG.md`.
- **Pas de secrets en dur**. Toujours via `os.environ` et `.env.example` versionné sans valeurs.
- **Pas de dépendance à un service externe non mocké en test**. OpenRouter, Qdrant, Postgres doivent avoir leur fake pour les tests unitaires.

---

## 🧭 Principe de fond : le brique-par-brique

Tu travailles comme Zico : **une brique = une décision tranchée + un livrable testable + un carnet de bord mis à jour**.

Chaque brique :
1. Décision claire (quoi, pourquoi, alternatives écartées)
2. Implémentation minimale qui passe les tests
3. 1 entrée dans `CARNET_DE_BORD.md` à la racine du repo

Si tu n'arrives pas à décrire une brique en 3 lignes, c'est qu'elle est trop grosse. **Découpe.**

---

## 📞 Si vraiment bloqué

- Erreur de stack ambiguë → essaie la solution la plus idiomatique de la lib, documente le choix.
- Décision architecturale non-triviale → STOP, rapport, attends.
- Comportement bizarre d'une lib → log, continue avec un workaround, note le TODO dans `BACKLOG.md`.

**Ne jamais** demander une validation triviale. Si tu te poses la question "est-ce que Zico voudrait X ou Y ?" et que X et Y sont équivalents fonctionnellement, choisis X et avance.

---

**Dernière mise à jour** : 2 novembre 2026
**Prochain checkpoint** : dimanche 10 novembre 2026
