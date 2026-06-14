"""
TransitFlow LLM Provider
========================
Uses Ollama (local, no API key needed).

Both chat AND embeddings use Ollama.

Students: You do NOT need to change this file.
"""

from __future__ import annotations
import requests
from typing import List

from skeleton.config import (
    OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL, OLLAMA_EMBED_MODEL, OLLAMA_EMBED_DIM, OLLAMA_TIMEOUT,
)


class LLMProvider:
    """
    Unified interface for chat and embeddings via Ollama.
    """

    def __init__(self):
        self.chat_provider = "ollama"
        self._ollama_chat_model = OLLAMA_CHAT_MODEL
        self._embed_provider = "ollama"
        self.embed_dim = OLLAMA_EMBED_DIM

        # Check Ollama is reachable on startup
        self._check_ollama()
        self._print_status()

    def _print_status(self):
        print(f"[LLM] Chat: Ollama ({self._ollama_chat_model}) | Embed: Ollama ({OLLAMA_EMBED_MODEL})")

    # ── Runtime model switching ────────────────────────────────────────────

    def set_chat_provider(self, provider: str) -> str:
        """Kept for compatibility — only 'ollama' is supported."""
        if provider.lower() != "ollama":
            return f"❌ Only 'ollama' is supported."
        try:
            self._check_ollama()
        except ConnectionError as e:
            return f"❌ {e}"
        self.chat_provider = "ollama"
        self._print_status()
        return f"✅ Ollama ({self._ollama_chat_model}) — running locally"

    def get_chat_provider(self) -> str:
        return "ollama"

    def get_chat_model(self) -> str:
        return self._ollama_chat_model

    def set_chat_model(self, model_name: str) -> str:
        self._ollama_chat_model = model_name
        print(f"[LLM] Switched Ollama model to: {model_name}")
        return f"✅ Switched to {model_name}"

    def get_available_ollama_models(self) -> list[str]:
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            r.raise_for_status()
            models = r.json().get("models", [])
            return sorted(m["name"] for m in models)
        except Exception:
            return []

    # ── Public API ─────────────────────────────────────────────────────────

    def chat(self, messages: list[dict], system_prompt: str = "") -> str:
        return self._ollama_chat(messages, system_prompt)

    def embed(self, text: str) -> List[float]:
        return self._ollama_embed(text)

    # ── Ollama internals ───────────────────────────────────────────────────

    def _ollama_chat(self, messages: list[dict], system_prompt: str) -> str:
        # Ollama only accepts {"role": ..., "content": ...} — strip any extra keys
        clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        if system_prompt:
            clean_messages = [{"role": "system", "content": system_prompt}] + clean_messages
        payload = {
            "model": self._ollama_chat_model,
            "messages": clean_messages,
            "stream": False,
        }

        r = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT)
        r.raise_for_status()
        return r.json()["message"]["content"]

    def _ollama_embed(self, text: str) -> List[float]:
        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["embedding"]

    def ollama_tool_call(
        self,
        history: list[dict],
        tools: list[dict],
        user_message: str,
        system_prompt: str = "",
    ) -> list[dict]:
        """
        Use Ollama's native tool-calling API to select tools.
        llama3.2:1b is fine-tuned for this and produces reliable results.
        Returns [{"name": ..., "params": {...}}].
        """
        clean = []
        if system_prompt:
            clean.append({"role": "system", "content": system_prompt})
        clean += [{"role": m["role"], "content": m["content"]} for m in history]
        clean.append({"role": "user", "content": user_message})

        # Convert agent TOOLS list to OpenAI/Ollama function-calling schema
        ollama_tools = []
        for t in tools:
            properties = {}
            for pname, pschema in t.get("parameters", {}).items():
                properties[pname] = {k: v for k, v in pschema.items()}
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": t.get("required", []),
                    },
                },
            })

        payload = {
            "model":   self._ollama_chat_model,
            "messages": clean,
            "tools":   ollama_tools,
            "stream":  False,
        }
        r = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT)
        r.raise_for_status()

        raw_calls = r.json().get("message", {}).get("tool_calls", [])
        return [
            {
                "name":   tc["function"]["name"],
                "params": tc["function"].get("arguments", {}),
            }
            for tc in raw_calls
            if "function" in tc
        ]

    def _check_ollama(self):
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            r.raise_for_status()
        except Exception as e:
            raise ConnectionError(
                f"Cannot reach Ollama at {OLLAMA_BASE_URL}.\n"
                "Make sure Ollama is running: https://ollama.com/download\n"
                f"Then pull a model: ollama pull {OLLAMA_CHAT_MODEL}\n"
                f"Error: {e}"
            )

    def ollama_available(self) -> bool:
        """Quick non-raising check — used by the UI to show toggle state."""
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
            return r.ok
        except Exception:
            return False


# Singleton — import this everywhere
llm = LLMProvider()
