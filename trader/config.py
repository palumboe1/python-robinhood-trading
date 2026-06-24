"""Configuration loading for the trader.

Credentials are read from environment variables (optionally via a local
.env file). Nothing sensitive is ever hard-coded.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load variables from a .env file if one is present. Real environment
# variables always take precedence over .env values.
load_dotenv()


@dataclass(frozen=True)
class Config:
    """Robinhood credentials and session settings."""

    username: str
    password: str
    mfa_secret: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        username = os.getenv("ROBINHOOD_USERNAME")
        password = os.getenv("ROBINHOOD_PASSWORD")
        mfa_secret = os.getenv("ROBINHOOD_MFA_SECRET") or None

        if not username or not password:
            raise RuntimeError(
                "Missing credentials. Set ROBINHOOD_USERNAME and "
                "ROBINHOOD_PASSWORD in your environment or .env file "
                "(see .env.example)."
            )
        return cls(username=username, password=password, mfa_secret=mfa_secret)
