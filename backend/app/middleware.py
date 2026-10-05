from __future__ import annotations

import json
from typing import Any
import urllib.parse

from starlette.types import ASGIApp, Message, Receive, Scope, Send

ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
]


class SecurityHeadersMiddleware:
    """Outermost plain ASGI middleware to attach security headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = list(message.get("headers", []))
                existing_names = {h[0].lower() for h in headers}
                for name, value in SECURITY_HEADERS:
                    if name not in existing_names:
                        headers.append((name, value))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            if not response_started:
                body = b"Internal Server Error"
                headers = [
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ]
                headers.extend(SECURITY_HEADERS)
                await send(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": headers,
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": body,
                    }
                )
            else:
                raise


class HostOriginMiddleware:
    """Plain ASGI middleware validating Host and Origin headers to prevent DNS rebinding and CSRF."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        host_val: str | None = None
        origin_val: str | None = None

        for raw_name, raw_val in headers:
            name_lower = raw_name.lower()
            if name_lower == b"host":
                try:
                    host_val = raw_val.decode("latin1").strip()
                except Exception:
                    host_val = None
            elif name_lower == b"origin":
                try:
                    origin_val = raw_val.decode("latin1").strip()
                except Exception:
                    origin_val = None

        # 1. Host header validation
        if not host_val:
            await self._send_json(send, 400, {"detail": "Invalid or missing Host header."})
            return

        # Extract hostname, ignoring port (handling optional IPv6 brackets)
        if host_val.startswith("[") and "]" in host_val:
            hostname = host_val[1 : host_val.index("]")]
        else:
            hostname = host_val.split(":")[0].strip()

        if hostname.lower() not in ALLOWED_HOSTS:
            await self._send_json(send, 400, {"detail": "Invalid Host header."})
            return

        # 2. Origin header validation on mutating HTTP methods
        method = scope.get("method", "").upper()
        if method in MUTATING_METHODS and origin_val is not None:
            if origin_val.lower() == "null":
                await self._send_json(send, 403, {"detail": "Cross-site request refused."})
                return

            parsed = urllib.parse.urlsplit(origin_val)
            origin_host = (parsed.hostname or "").lower()
            if origin_host not in ALLOWED_HOSTS:
                await self._send_json(send, 403, {"detail": "Cross-site request refused."})
                return

        await self.app(scope, receive, send)

    @staticmethod
    async def _send_json(send: Send, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
