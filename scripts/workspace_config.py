"""Shared repo/workspace path and secret helpers for local automation."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent.parent if REPO_ROOT.parent.name == "repos" else REPO_ROOT.parent
WORKSPACE_CONFIG_DIR = WORKSPACE_ROOT / "config"
WORKSPACE_SECRETS_PATH = WORKSPACE_CONFIG_DIR / ".secrets"
REPO_SECRETS_PATH = REPO_ROOT / "config" / ".secrets"


def load_dotenv_secrets() -> None:
    for path in (WORKSPACE_SECRETS_PATH, REPO_SECRETS_PATH):
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export ") :]
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_secret(name: str, default: str | None = None) -> str:
    load_dotenv_secrets()
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if default is not None:
        return default
    sys.exit(f"ERROR: {name} not set in environment or local secrets file")
