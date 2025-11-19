import json
from typing import Any, Dict, Optional

import requests


class VQMClientError(RuntimeError):
    """Generic error for VQM SDK failures."""


class VQMClient:
    """
    Thin HTTP client for the VQM API.

    This is intentionally read-only:
    - No signing
    - No trading
    - No transaction submission

    It only reads:
    - Network state (fees, load, band)
    - Guardian / policy output
    - Tools registry
    - Fee horizon & scheduler advice (if available)
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # --------- low-level helper ---------
    def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.get(url, timeout=self.timeout)
        except Exception as exc:
            raise VQMClientError(f"Request to {url} failed: {exc!r}") from exc

        if not resp.ok:
            raise VQMClientError(
                f"VQM API {path} returned HTTP {resp.status_code}: {resp.text[:200]!r}"
            )

        try:
            return resp.json()
        except json.JSONDecodeError as exc:
            raise VQMClientError(
                f"Invalid JSON from {url}: {resp.text[:200]!r}"
            ) from exc

    # --------- public high-level methods ---------
    def health(self) -> Dict[str, Any]:
        """
        GET /health

        Returns basic liveness info.
        """
        return self._get("/health")

    def get_state(self) -> Dict[str, Any]:
        """
        GET /v1/state

        Returns the full VQM pipeline snapshot. This is the same
        structure you see when running:

            python -m ecosystem.cli.governor_cli
        """
        return self._get("/v1/state")

    def get_guardian(self) -> Dict[str, Any]:
        """
        GET /v1/guardian

        Returns the Guardian block (policy / forge / mesh / llm).
        """
        return self._get("/v1/guardian")

    def get_tools(self) -> Dict[str, Any]:
        """
        GET /v1/tools

        Returns the tools registry with scores and descriptions.
        """
        return self._get("/v1/tools")

    def get_fee_horizon(self) -> Optional[Dict[str, Any]]:
        """
        GET /v1/fee-horizon

        Returns fee trend projections if the backend exposes it.
        If the endpoint is missing, returns None instead of raising.
        """
        try:
            return self._get("/v1/fee-horizon")
        except VQMClientError as exc:
            # Gracefully downgrade if endpoint not available
            msg = str(exc)
            if "404" in msg or "Not Found" in msg:
                return None
            raise

    def get_scheduler(self) -> Optional[Dict[str, Any]]:
        """
        GET /v1/scheduler

        Returns scheduler advice / bands if available.
        """
        try:
            return self._get("/v1/scheduler")
        except VQMClientError as exc:
            msg = str(exc)
            if "404" in msg or "Not Found" in msg:
                return None
            raise
