"""Runtime configuration.

Config comes from environment variables, never from code:
  local       -> .env or your shell
  CI          -> GitHub Actions vars
  production  -> app settings / Azure App Configuration

Secrets (e.g. the Takealot API token) do NOT belong here. They live in
Key Vault and are read at runtime via managed identity.
"""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    project_endpoint: str
    model_deployment: str


@lru_cache
def settings() -> Settings:
    """Read and validate config once. Missing values fail loudly at startup."""
    try:
        return Settings(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model_deployment=os.environ["FOUNDRY_MODEL_DEPLOYMENT"],
        )
    except KeyError as missing:
        raise RuntimeError(f"Missing environment variable: {missing}") from None
