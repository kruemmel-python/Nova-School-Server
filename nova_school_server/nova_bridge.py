from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class NovaBridge:
    SecurityPlane: type
    ToolSandbox: type
    NovaAIProviderRuntime: type


def load_nova_bridge(nova_shell_path: Path | None) -> NovaBridge:
    if importlib.util.find_spec("nova") is None or importlib.util.find_spec("nova_shell") is None:
        for candidate in _candidate_paths(nova_shell_path):
            if candidate.exists() and str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
                break

    try:
        from nova.agents.sandbox import ToolSandbox
        from nova.runtime.security import SecurityPlane
        from nova_shell import NovaAIProviderRuntime
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Nova-shell classes could not be loaded. Set NOVA_SHELL_PATH to the Nova-shell repository or install nova-shell."
        ) from exc

    return NovaBridge(
        SecurityPlane=SecurityPlane,
        ToolSandbox=ToolSandbox,
        NovaAIProviderRuntime=NovaAIProviderRuntime,
    )


def _candidate_paths(nova_shell_path: Path | None) -> list[Path]:
    candidates: list[Path] = []
    if nova_shell_path is not None:
        candidates.append(nova_shell_path)
    candidates.extend(
        [
            Path(r"H:\Nova-shell-main"),
            Path(__file__).resolve().parents[2] / "Nova-shell-main",
            Path.cwd(),
        ]
    )
    seen: set[str] = set()
    unique: list[Path] = []
    for path in candidates:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique
