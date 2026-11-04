# CLAUDE.md — Vigie v2 (chatbot RAG SOC, version simple niveau senior)

Remplace l'ancien CLAUDE.md. La version précédente était overengineered. On repart propre.

Principe : senior = simple ET robuste, pas compliqué.

---

## Contexte en 3 lignes

- Vigie = chatbot RAG SOC, support pédagogique MSc2 La Plateforme_ x Devoteam.
- Les étudiants reçoivent un repo fonctionnel, diagnostiquent et corrigent 3 incidents injectés.
- Format : app web FastAPI déployable Render en 1 clic, comme Tempo Client V2.

---

## Stack cible — SIMPLE

```
Python 3.11 + uv
FastAPI                     API + serve static HTML
ChromaDB embedded           vecteurs MITRE, fichier local, pas de service
OpenRouter                  LLM via httpx direct, PAS de LangChain
sqlite3 stdlib              historique incidents + audit log
HTML + CSS + JS vanilla     PAS de Streamlit, PAS de React
mitre_techniques.json       source MITRE versionnée, pas de seed
1 Dockerfile simple         PAS de docker-compose
```

### INTERDITS
- Postgres, Redis, Qdrant service séparé, Langfuse self-hosted
- LangChain, LangGraph, Streamlit
- docker-compose multi-services
- migrations SQL complexes
- toute dépendance externe non indispensable

---

## Architecture (pattern hexagonal simplifié)

```
app/
├── main.py                 FastAPI + routes + serve static/
├── core/
│   ├── services/
│   │   ├── chat.py         orchestration retrieval + LLM + persist
│   │   └── guardrail.py    review humain des recommandations
│   └── schemas.py          Pydantic models
├── adapters/
│   ├── llm.py              OpenRouter via httpx
│   ├── retrieval.py        ChromaDB wrapper
│   └── db.py               sqlite3 wrapper
└── static/
    ├── index.html          UI chatbot
    ├── style.css
    └── app.js

data/
├── mitre_techniques.json   source MITRE ATT&CK versionnée
└── vigie.db                sqlite (gitignored)

Dockerfile
pyproject.toml
```

Pas plus. Pas de 15 dossiers.

---

## Esthétique UI — rétro Windows 95 + terminal CRT

L'identité visuelle est verrouillée. Elle n'est pas négociable, c'est la signature du produit.

### Nom
- Nom affiché partout : "Vigie" seul. Pas de sous-titre, pas de slogan, pas de "— AtlasMétaux" ni autre.
- Pas d'émojis nulle part dans l'UI. Les icônes utilisées sont Tabler Icons (webfont) et des caractères ASCII du type `>`, `▊`, `|`, `─`.

### Chrome de la fenêtre (style Windows 95)
- Fond général gris Windows 95 `#c3c3c3` sur le chrome (barre titre, menu, toolbar, status bar).
- Barre de titre bleue avec dégradé `linear-gradient(90deg, #000080 0%, #1084d0 100%)`, texte blanc.
- Boutons de titre (minimiser, maximiser, fermer) en relief 3D classique Win95 avec bordures asymétriques : `border-top: 1px solid #fff; border-left: 1px solid #fff; border-right: 1px solid #808080; border-bottom: 1px solid #808080;`.
- Menu bar avec entrées accentuées type `<u>F</u>ichier`, `<u>I</u>ncidents`, `<u>A</u>gent`, `M<u>I</u>TRE`, `A<u>i</u>de`.
- Toolbar avec boutons 3D Win95 et icônes Tabler à gauche de chaque label (16-18px, pas d'émojis).
- Status bar en bas avec séparateurs `|` et pastille verte pour l'état API en ligne.
- Coins carrés partout, pas de border-radius.
- Fontes du chrome : `'Tahoma', 'MS Sans Serif', sans-serif`.

### Zone centrale du chat (style terminal CRT)
- Fond noir pur `#000000`.
- Texte en vert phosphore `#00ff41` pour l'action, `#00aa2e` pour les prompts et séparateurs, `#c3e8c3` pour le texte explicatif, `#008f22` pour les détails faibles.
- Scan lines CRT subtiles (effet moniteur ancien) via un overlay en `repeating-linear-gradient` à opacité très faible (0.03).
- Fonte monospace pour le contenu : `'Courier New', 'Consolas', monospace`.
- Prompts style terminal : `[ANALYSTE] >` et `[VIGIE] >`.
- Curseur `▊` qui clignote via animation CSS `blink` 1s infinite.
- Message agent dans un bloc avec `border-left: 2px solid #00ff41` et un fond vert très transparent.
- Severity high en jaune `#ffff44`, rouge `#ff6b6b` pour les erreurs, les deux rares et uniquement en marqueur sémantique.
- Entêtes de section préfixées par `▸` ou `─────` ASCII, jamais d'emojis ni d'icônes graphiques.

### Guardrail humain AI Act art.14
- Bloc dédié avec `border-left: 2px solid #ffff44` et fond jaune très transparent.
- Message : "GUARDRAIL AI Act art.14 — Validation humaine requise".
- 3 boutons type terminal avec raccourcis clavier dans le label : `[A]pprouver`, `[R]ejeter`, `[D]étails`.
- Boutons avec fond très sombre (vert, rouge, neutre), bordure 1px dans la couleur sémantique, texte dans la même couleur, pas d'ombres ni d'effets.

### Input utilisateur en bas
- Fond noir, bordure fine verte phosphore.
- Préfixe `>` monospace vert.
- Placeholder : "Décrivez l'incident...".
- Bouton d'envoi en texte terminal : "SEND" (pas "Send", pas "Envoyer").

### Touches modernes autorisées
- Animations douces (curseur qui clignote, fade in sur les nouveaux messages).
- Icônes Tabler modernes dans la toolbar (ti-plus, ti-list, ti-shield-check, ti-shield-lock).
- Hairlines colorées sémantiques (border-left) pour les blocs importants.
- Responsive via CSS flex/grid (ça marche sur mobile mais garde l'esthétique).
- Scrollbar personnalisée verte phosphore (fine, pas de flèches old-school).

### Interdits esthétiques
- Pas d'emojis nulle part dans l'UI.
- Pas de gradients multi-couleurs sauf la barre de titre bleue Win95.
- Pas d'ombres portées (box-shadow) sauf focus accessibility.
- Pas de rounded corners (sauf scrollbar fine).
- Pas de couleurs flashy en dehors des 4 sémantiques : vert phosphore (défaut), jaune (warning), rouge (erreur), bleu Win95 (chrome uniquement).
- Pas de "mode clair" dans un premier temps : l'identité CRT verte est le mode par défaut et unique pour la zone de chat.

Le résultat doit faire ressentir une "ambiance SOC des années 90 modernisée", pas une page web générique. Un étudiant doit reconnaître Vigie à l'esthétique en 1 seconde.

---

## Les 3 incidents à injecter (approche B stricte)

Code source 100% sain pendant le dev. Points d'injection documentés dans `docs/incidents-playbook.md` (gitignored).

| # | Incident | Fichier cible | Pattern |
|---|---|---|---|
| 1 | Dérive sémantique du retrieval | `adapters/retrieval.py` | top_k bidouillé, filtre buggé |
| 2 | Facture OpenRouter qui s'emballe | `adapters/llm.py` | retry mal cadré, pas de rate limit |
| 3 | Bypass guardrail AI Act art.14 | `core/services/guardrail.py` | audit non transactionnel, check contournable |

---

## RÈGLES DE DÉLÉGATION

### Avance SEUL
- Scaffolding, boilerplate, structure
- Tests unitaires, mocks
- Docstrings, README de modules
- Nommage, formatters (ruff, black configs par défaut)
- Dockerfile simple
- HTML/CSS/JS vanilla

### Demande validation
- Changement de contrat API (nouvelle route)
- Ajout d'une dépendance externe
- Design précis des 3 incidents
- Toute modification de l'esthétique UI décrite ci-dessus

### NE FAIS JAMAIS
- Rajouter Postgres, Qdrant, Redis, Langfuse self-hosted, LangChain, Streamlit
- Rajouter docker-compose multi-services
- Push sur `vigie-prod` sans validation
- Ajouter des émojis dans l'UI
- Modifier l'identité "Vigie" seule (pas de sous-titre, pas d'ajout)

---

## Rapport de brique

3 bullets max, pas de blabla.

```markdown
### Brique X — [NOM]  (statut: terminée / bloquée)
1. Fait : [1 phrase]
2. Décidé seul : [points autonomes]
3. Bloquant : [rien ou 1 question]
```

---

## Principe de fond

Le code senior tient en peu de lignes et marche du premier coup.

- Brique > 150 lignes → découper
- Besoin d'une migration DB complexe → repenser le modèle
- Dépendance externe pas indispensable → la supprimer
- Test compliqué à écrire → le code est mal conçu

But final : un étudiant ouvre le repo, lit le README, lance `uvicorn app.main:app`, et ça marche.

---

## Pièges à éviter

- Pas d'overengineering. Vigie est un support pédagogique, pas une plateforme SaaS.
- Pas d'abstractions prématurées.
- Pas de "TODO" dans le code livré. Soit tu fais, soit tu notes dans `BACKLOG.md`.
- Pas de secrets en dur. `os.environ` + `.env.example`.
- Pas de dépendance à un service externe non mocké en test.

---

Dernière mise à jour : 3 novembre 2026
Objectif immédiat : repo fonctionnel en 1 commande, déployable Render, esthétique Vigie rétro CRT verrouillée.
