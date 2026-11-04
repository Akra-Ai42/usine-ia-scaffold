FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir ".[all]" 2>/dev/null || pip install --no-cache-dir \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.30" \
    "httpx>=0.27" \
    "chromadb>=0.5" \
    "pydantic>=2.9" \
    "python-dotenv>=1.0"

COPY app/ app/
COPY data/mitre_techniques.json data/mitre_techniques.json

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
