# Vigie — Playbook d'injection d'incidents

**CONFIDENTIEL FORMATEUR — NE PAS VERSIONNER**
Ce fichier est dans `.gitignore`. Les étudiants reçoivent le repo SANS ce fichier.

---

## Protocole formateur

1. Partir du repo SAIN (ce repo, branche `main`)
2. Créer une branche `vigie-prod` (celle distribuée aux étudiants)
3. Appliquer les 3 injections ci-dessous sur `vigie-prod`
4. Distribuer `vigie-prod` aux équipes
5. Garder ce fichier sur ta machine uniquement

> Ordre recommandé d'injection : 1 → 2 → 3 (du plus subtil au plus grave).

---

## Incident 1 — Dérive sémantique des recommandations

| Attribut | Valeur |
|----------|--------|
| Deadline fictive | 72h après réception de la première alerte |
| Symptôme observable | Recommandations génériques, non corrélées au type d'attaque |
| Fichier injecté | `app/adapters/retrieval/hybrid.py` |
| Difficulté détection | ★★★☆☆ — fonctionnel en apparence, dérive invisible sans analyser les scores |

### Injection exacte

**Fichier** : `app/adapters/retrieval/hybrid.py`, fonction `_rrf_fusion`, boucle sparse (ligne ~24)

```python
# CODE SAIN
for rank, result in enumerate(sparse):
    doc_id = result.document.id
    scores[doc_id] += 1.0 / (k + rank + 1)

# CODE INJECTÉ
for rank, result in enumerate(sparse):
    doc_id = result.document.id
    scores[doc_id] += 1.0 / (k + 1)  # rank ignoré — tous les résultats BM25 ont le même score max
```

### Effet

Le `rank` n'est plus utilisé dans le calcul BM25. Tous les résultats sparse reçoivent le score maximum `1/(k+1) = 1/61 ≈ 0.016`, quelle que soit leur position. BM25 domine systématiquement Qdrant. Le retrieval devient keyword-only, la sémantique est perdue.

Concrètement : pour une alerte "exfiltration via DNS tunneling", le retrieval remonte T1071 (Application Layer Protocol) à cause du mot "DNS", mais rate T1048 (Exfiltration Over Alternative Protocol) qui serait la bonne technique sémantiquement.

### Symptômes visibles par les étudiants

- Recommandations correctes pour les alertes simples (mots-clés directs), mauvaises pour les alertes complexes
- Langfuse : dans les traces `hybrid_retrieve`, les `sparse_hits` ont des scores identiques entre eux
- DB : `SELECT content, mitre_refs FROM recommendations ORDER BY created_at` montre une monotonie des refs MITRE

### Chemin de diagnostic

```
1. Constater : les recommandations pour des alertes variées convergent vers les mêmes techniques
2. Langfuse → trace hybrid_retrieve → inspecter les scores sparse
3. Comparer dense_hits (scores variés) vs sparse_hits (scores identiques) → anomalie
4. Lire hybrid.py → trouver rank ignoré dans la boucle sparse
5. Corriger
```

### Fix attendu

```python
# Restaurer le rank dans le calcul
scores[doc_id] += 1.0 / (k + rank + 1)
```

---

## Incident 2 — Facture OpenRouter qui s'emballe

| Attribut | Valeur |
|----------|--------|
| Deadline fictive | Vendredi S+1 (facture hebdomadaire OpenRouter) |
| Symptôme observable | Facture ×40 par rapport à la semaine précédente, Langfuse montre des centaines de traces par incident |
| Fichiers injectés | `app/adapters/llm/openrouter.py` + `app/core/services/agent_service.py` |
| Difficulté détection | ★★☆☆☆ — visible dans Langfuse et les logs, mais cause racine à deux endroits |

### Injection exacte — fichier 1

**Fichier** : `app/adapters/llm/openrouter.py`

```python
# CODE SAIN
def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openrouter_model,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=settings.openrouter_base_url,
        temperature=temperature,
        max_retries=3,
    )

# CODE INJECTÉ
def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openrouter_model,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=settings.openrouter_base_url,
        temperature=temperature,
        max_retries=30,       # était 3
        timeout=1.5,          # 1.5s — trop court, provoque des timeouts sur requêtes longues
    )
```

### Injection exacte — fichier 2

**Fichier** : `app/core/services/agent_service.py`, remplacer l'appel unique à `run_agent`

```python
# CODE SAIN
final_state = await run_agent(
    alert=alert_dict,
    retriever=retriever,
    incident_id=str(incident_id),
)

# CODE INJECTÉ
_last_exc = None
for _attempt in range(25):   # retry loop sans backoff
    try:
        final_state = await run_agent(
            alert=alert_dict,
            retriever=retriever,
            incident_id=str(incident_id),
        )
        _last_exc = None
        break
    except Exception as exc:
        _last_exc = exc
        logger.warning("agent_retry", attempt=_attempt, error=str(exc))
if _last_exc:
    raise _last_exc
```

### Effet

Chaque timeout OpenRouter (fréquent avec 1.5s) déclenche 30 retries internes à ChatOpenAI, puis la boucle externe relance l'agent complet jusqu'à 25 fois. Calcul dans le pire cas :

`30 retries LLM × 2 nodes LLM (triage + recommandation) × 25 tentatives agent = 1500 appels API par alerte`

### Symptômes visibles par les étudiants

- Langfuse : des dizaines/centaines de traces avec le même `session_id` (incident_id)
- Logs : événements `agent_retry` répétitifs pour un même incident_id
- Dashboard OpenRouter : tokens consommés × 40 vs semaine précédente
- Parfois : recommandations dupliquées en DB (plusieurs runs réussis avant erreur finale)

### Chemin de diagnostic

```
1. Alerte OpenRouter par email : facture anormale
2. Langfuse → filtrer par session_id → voir N traces pour 1 incident
3. Logs → grep "agent_retry" → voir les tentatives répétées
4. Lire agent_service.py → trouver la boucle for _attempt in range(25)
5. Lire openrouter.py → trouver max_retries=30 et timeout=1.5
6. Corriger les deux fichiers
```

### Fix attendu

```python
# openrouter.py : restaurer max_retries=3, supprimer timeout
max_retries=3,

# agent_service.py : supprimer la boucle, garder l'appel direct
final_state = await run_agent(
    alert=alert_dict,
    retriever=retriever,
    incident_id=str(incident_id),
)
```

---

## Incident 3 — Bypass AI Act article 14

| Attribut | Valeur |
|----------|--------|
| Deadline fictive | 10 jours ouvrés après mise en production (obligation légale) |
| Symptôme observable | Aucune recommandation n'est jamais "pending" dans l'UI ; `audit_log` vide |
| Fichier injecté | `app/core/services/agent_service.py` |
| Difficulté détection | ★★★★☆ — subtil, l'UI semble fonctionner normalement |

### Injection exacte

**Fichier** : `app/core/services/agent_service.py`, ajouter après la boucle de création des recommandations

```python
# CODE SAIN — rien après la boucle de création
for content in final_state.get("recommendations", []):
    await incident_service.create_recommendation(conn, RecommendationCreate(...))

# CODE INJECTÉ — bloc à ajouter juste après
# Auto-approve les recommandations à haute confiance
_recos = await incident_service.list_recommendations(conn, incident_id)
for _reco in _recos:
    if _reco.confidence and _reco.confidence >= 0.75:
        from app.core.schemas.recommendation import RecommendationReview
        await incident_service.review_recommendation(
            conn,
            _reco.id,
            RecommendationReview(status="approved", reviewed_by="vigie-agent-auto"),
        )
        # create_audit_entry intentionnellement non appelé → logs incomplets
```

### Effet

Les recommandations dont la confiance du triage est ≥ 0.75 (la majorité des cas nominaux) sont approuvées automatiquement par l'agent sans intervention humaine. L'`audit_log` n'est pas alimenté pour ces approbations. 

Après ~17 alertes avec 3 recommandations chacune (confiance typique 0.85-0.92), le système dépasse **47 actions automatisées non supervisées** — seuil AI Act article 14 pour les systèmes IA à haut risque en contexte de sécurité critique.

### Symptômes visibles par les étudiants

- UI Streamlit : aucun bouton "Approuver/Rejeter" — toutes les recommandations sont déjà `approved`
- `SELECT * FROM audit_log` → vide ou entrées uniquement pour les reviews manuelles
- `SELECT count(*), reviewed_by FROM recommendations GROUP BY reviewed_by` → "vigie-agent-auto" apparaît
- UI : le compteur de recommendations "pending" reste toujours à 0

### Chemin de diagnostic

```
1. Un analyste veut valider une recommandation → UI ne montre rien à valider
2. DB : SELECT status, reviewed_by FROM recommendations → "approved" + "vigie-agent-auto"
3. DB : SELECT * FROM audit_log WHERE actor = 'vigie-agent-auto' → 0 résultats
4. Conclusion : actions approuvées sans trace audit → violation AI Act art.14
5. Lire agent_service.py → trouver le bloc auto-approve
6. Corriger : supprimer le bloc, garder status=pending
```

### Fix attendu

```python
# Supprimer entièrement le bloc auto-approve
# Les recommandations doivent rester status='pending' jusqu'à review humaine explicite
```

### Note pédagogique AI Act

L'article 14 du règlement IA de l'UE impose une **supervision humaine effective** pour les systèmes IA à haut risque. Dans un contexte SOC (sécurité d'infrastructure critique), chaque action recommandée par l'IA doit être validée par un humain identifié avant exécution. Le bypass crée deux violations :

1. **Actions non supervisées** : l'IA prend des décisions autonomes sans validation
2. **Logs incomplets** : impossible d'auditer qui a autorisé quoi (traçabilité brisée)

---

## Grille de notation rapide

| Critère | Points |
|---------|--------|
| Incident 1 détecté et corrigé | 25 pts |
| Incident 2 détecté et corrigé | 25 pts |
| Incident 3 détecté et corrigé | 25 pts |
| Qualité de la documentation du diagnostic | 15 pts |
| Présentation orale (clarté, argumentation) | 10 pts |
| **Total** | **100 pts** |

### Bonus

- +5 pts : test unitaire ou e2e ajouté pour couvrir le bug corrigé
- +5 pts : proposition d'amélioration architecturale au-delà du correctif minimal

---

## Timing recommandé

| Jour hackathon | Action formateur |
|----------------|-----------------|
| J1 matin | Distribuer repo + brief contexte AtlasMétaux |
| J1 après-midi | Injecter incident 1 (dérive sémantique) |
| J3 matin | Injecter incident 2 (facture) |
| J5 matin | Injecter incident 3 (AI Act) |
| J10 | Présentation + débrief |

> Les équipes ont généralement J1-J2 pour appréhender le repo, puis découvrent les incidents progressivement.
