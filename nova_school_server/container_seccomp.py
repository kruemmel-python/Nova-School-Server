from __future__ import annotations

import os
from pathlib import Path


def resolve_seccomp_profile_option(profile_path: Path, runtime_name: str) -> str | None:
    if not profile_path.exists():
        return None
    if os.name == "nt" and runtime_name.startswith("docker"):
        return None
    resolved = profile_path.resolve(strict=False)
    return f"seccomp={resolved}"
