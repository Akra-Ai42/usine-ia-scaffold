FROM python:3.11-slim

WORKDIR /app

# Dépendances système minimales (sentence-transformers a besoin de gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# uv pour install rapide
RUN pip install --no-cache-dir uv

# Dépendances Python — couche cacheable
COPY pyproject.toml .
RUN uv pip install --system .

# Code source
COPY . .

# Par défaut : API FastAPI
# Overrider dans docker-compose pour Streamlit
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
