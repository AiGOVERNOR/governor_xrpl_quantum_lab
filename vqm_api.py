#!/usr/bin/env python3
"""
Minimal ASGI API for the XRPL VQM Ecosystem.

Endpoints:
  GET /               -> Health/status
  GET /vqm/heartbeat  -> Run one VQM cycle (live XRPL read + guardian + mesh)
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict

from ecosystem.orchestrator import run_vqm_cycle


async def _json_response(send, status: int, body_obj: Dict[str, Any]) -> None:
    body = json.dumps(body_obj, default=str).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("utf-8")),
    ]
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": headers,
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": body,
        }
    )


async def app(scope, receive, send):
    """
    Barebones ASGI router. No FastAPI/Starlette dependencies.
    """
    if scope["type"] != "http":
        # Only HTTP supported
        await _json_response(
            send,
            500,
            {"error": "Unsupported scope type", "scope_type": scope["type"]},
        )
        return

    method = scope.get("method", "GET").upper()
    path = scope.get("path", "/")

    # --- Root: status endpoint ---
    if path == "/" and method == "GET":
        await _json_response(
            send,
            200,
            {
                "status": "ok",
                "message": "XRPL VQM Pipeline Phase 2 API online",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return

    # --- VQM heartbeat endpoint ---
    if path == "/vqm/heartbeat" and method == "GET":
        try:
            state = run_vqm_cycle()
            await _json_response(send, 200, state)
        except Exception as exc:
            await _json_response(
                send,
                500,
                {
                    "error": "VQM pipeline failure",
                    "detail": str(exc),
                },
            )
        return

    # --- Fallback 404 ---
    await _json_response(
        send,
        404,
        {
            "error": "Not found",
            "path": path,
            "method": method,
        },
    )
