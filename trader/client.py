"""Robinhood session management.

Wraps login/logout for the `robin_stocks` library. `robin_stocks` keeps a
single global session, so this class just owns its lifecycle and gives us a
clean place to handle MFA.
"""
from __future__ import annotations

import logging

import pyotp
import robin_stocks.robinhood as rh

from .config import Config

logger = logging.getLogger(__name__)


class RobinhoodClient:
    """Manages authentication with Robinhood.

    Use as a context manager to guarantee logout::

        with RobinhoodClient(Config.from_env()) as client:
            ...
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logged_in = False

    @property
    def logged_in(self) -> bool:
        return self._logged_in

    def login(self) -> None:
        """Authenticate with Robinhood.

        If a TOTP secret is configured, a fresh 2FA code is generated
        automatically. Otherwise robin_stocks will prompt interactively for
        an SMS/app code on the first login.
        """
        mfa_code = None
        if self._config.mfa_secret:
            mfa_code = pyotp.TOTP(self._config.mfa_secret).now()

        logger.info("Logging in to Robinhood as %s", self._config.username)
        rh.login(
            username=self._config.username,
            password=self._config.password,
            mfa_code=mfa_code,
        )
        self._logged_in = True
        logger.info("Login successful")

    def logout(self) -> None:
        if self._logged_in:
            rh.logout()
            self._logged_in = False
            logger.info("Logged out")

    def __enter__(self) -> "RobinhoodClient":
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.logout()
