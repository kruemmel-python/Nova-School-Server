from __future__ import annotations

import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from .config import ServerConfig
from .database import SchoolRepository


def normalize_lmstudio_base_url(value: str | None) -> str:
    text = str(value or "").strip() or "http://127.0.0.1:1234/v1"
    if "://" not in text:
        text = f"http://{text}"
    parsed = urlparse(text)
    scheme = parsed.scheme or "http"
    hostname = (parsed.hostname or "").strip()
    if hostname in {"0.0.0.0", "::"}:
        hostname = "127.0.0.1"
    if not hostname:
        hostname = "127.0.0.1"
    netloc = hostname
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    path = parsed.path or "/v1"
    if not path.startswith("/"):
        path = f"/{path}"
    return urlunparse((scheme, netloc, path, "", "", ""))


class LMStudioService:
    def __init__(self, ai_runtime_cls: type, repository: SchoolRepository, config: ServerConfig) -> None:
        self.ai_runtime_cls = ai_runtime_cls
        self.repository = repository
        self.config = config
        self._lock = threading.RLock()

    @property
    def base_url(self) -> str:
        return normalize_lmstudio_base_url(str(self.repository.get_setting("lmstudio_base_url", "http://127.0.0.1:1234/v1")))

    @property
    def model(self) -> str:
        return str(self.repository.get_setting("lmstudio_model", ""))

    def status(self) -> dict[str, Any]:
        runtime = self._runtime()
        try:
            models_result = runtime.list_models("lmstudio")
            models = []
            if isinstance(getattr(models_result, "data", None), dict):
                models = list(models_result.data.get("models", []))
            return {"provider": "lmstudio", "base_url": self.base_url, "model": self.model, "models": models, "configured": True, "error": getattr(models_result, "error", None)}
        except Exception as exc:
            return {"provider": "lmstudio", "base_url": self.base_url, "model": self.model, "models": [], "configured": True, "error": str(exc)}

    def complete(self, prompt: str, *, system_prompt: str = "", model: str | None = None) -> dict[str, Any]:
        resolved_model = (model or self.model).strip()
        if not resolved_model:
            status = self.status()
            if status["models"]:
                resolved_model = str(status["models"][0])
        if not resolved_model:
            raise RuntimeError("Fuer LM Studio ist noch kein Modell gesetzt.")
        with self._lock:
            runtime = self._runtime()
            result = runtime.complete_prompt(prompt, provider="lmstudio", model=resolved_model, system_prompt=system_prompt)
        if getattr(result, "error", None):
            raise RuntimeError(str(result.error))
        payload = getattr(result, "data", {}) or {}
        return {"provider": "lmstudio", "model": resolved_model, "text": str(payload.get("text") or getattr(result, "output", "")), "raw": payload}

    def _runtime(self) -> Any:
        runtime_config = {
            "ai_provider": "lmstudio",
            "ai_model": self.model,
            "lmstudio_model": self.model,
            "lmstudio_base_url": self.base_url,
        }
        return self.ai_runtime_cls(runtime_config=runtime_config, cwd=Path(self.config.base_path))
