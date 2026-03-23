from __future__ import annotations

from pathlib import Path

from .config import ServerConfig
from .server import create_application, run_server


def main() -> None:
    base_path = Path(__file__).resolve().parents[1]
    config = ServerConfig.from_base_path(base_path)
    application = create_application(config)
    run_server(application)


if __name__ == "__main__":
    main()
