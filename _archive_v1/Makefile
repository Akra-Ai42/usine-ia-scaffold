.PHONY: up down api ui test seed logs help

help: ## Liste les commandes disponibles
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

up: ## Lance les services Docker, applique les migrations et charge MITRE ATT&CK
	docker compose up -d --wait db redis qdrant langfuse
	docker compose --profile init run --rm migrate
	python scripts/seed_mitre.py

down: ## Arrête tous les services Docker
	docker compose down

api: ## Lance l'API FastAPI en mode reload (dev)
	uvicorn app.main:app --reload --port 8000

ui: ## Lance l'UI Streamlit
	streamlit run streamlit_app.py

test: ## Exécute tous les tests
	pytest tests/ -v

seed: ## Recharge les techniques MITRE ATT&CK dans Qdrant + BM25
	python scripts/seed_mitre.py

logs: ## Suit les logs de l'API en temps réel
	docker compose logs -f api
