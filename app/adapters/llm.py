import os
import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-3-haiku")
MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "1024"))
TIMEOUT = float(os.environ.get("LLM_TIMEOUT_S", "30"))

_SYSTEM_PROMPT = """Tu es Vigie, assistant SOC (Security Operations Center) spécialisé MITRE ATT&CK.
Tu analyses les incidents de sécurité, identifies les techniques MITRE correspondantes et proposes des recommandations de réponse claires et actionnables.
Réponds toujours en français. Sois précis, concis, et structuré. Ne fabrique pas de techniques MITRE : utilise uniquement celles fournies dans le contexte."""


async def call_llm(messages: list[dict], system: str = _SYSTEM_PROMPT) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY non définie")

    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "system", "content": system}] + messages,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://vigie.soc",
        "X-Title": "Vigie SOC",
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
