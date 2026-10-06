from __future__ import annotations

import urllib.parse
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

MIME_TYPES: dict[str, str] = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".html": "text/html; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".json": "application/json",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
    ".map": "application/json",
}


def setup_frontend_serving(application: FastAPI, dist_dir: Path) -> None:
    """Mount API 404 fallback and frontend SPA static file catch-all routes."""
    dist_resolved = dist_dir.resolve()

    # 1. API 404 catch-all: unknown /api routes return JSON 404, never index.html
    @application.api_route(
        "/api/{api_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    )
    async def api_not_found(api_path: str) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    # 2. Frontend SPA and static file catch-all
    @application.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def serve_static_or_spa(request: Request, full_path: str) -> Response:
        raw_path = request.url.path

        # Reject NUL bytes or backslashes before and after decoding
        if "\0" in raw_path or "\\" in raw_path:
            return Response(status_code=404)

        unquoted = urllib.parse.unquote(raw_path)
        if "\0" in unquoted or "\\" in unquoted:
            return Response(status_code=404)

        double_unquoted = urllib.parse.unquote(unquoted)
        if "\0" in double_unquoted or "\\" in double_unquoted:
            return Response(status_code=404)

        # Inspect path segments
        rel_str = unquoted.lstrip("/")
        if rel_str in ("docs", "redoc", "openapi.json"):
            return Response(status_code=404)

        segments = [s for s in rel_str.split("/") if s]
        for seg in segments:
            if seg in (".", "..") or (seg.startswith(".") and len(seg) > 1):
                return Response(status_code=404)

        # Resolve path within dist_dir
        try:
            target = (dist_resolved / rel_str).resolve()
        except Exception:
            return Response(status_code=404)

        if not target.is_relative_to(dist_resolved):
            return Response(status_code=404)

        # Do not allow directory listing
        if target.is_dir() and rel_str:
            # A sub-directory was requested; if no extension, let SPA handle or 404
            pass

        # Check if target is a regular file
        if target.is_file():
            if target.name.startswith("."):
                return Response(status_code=404)

            ext = target.suffix.lower()
            media_type = MIME_TYPES.get(ext, "application/octet-stream")

            if target.name == "index.html":
                cache_control = "no-cache"
            elif rel_str.startswith("assets/"):
                cache_control = "public, max-age=31536000, immutable"
            else:
                cache_control = "no-cache"

            headers = {"Cache-Control": cache_control}
            if request.method == "HEAD":
                headers["Content-Length"] = str(target.stat().st_size)
                return Response(status_code=200, media_type=media_type, headers=headers)

            content = target.read_bytes()
            headers["Content-Length"] = str(len(content))
            return Response(
                content=content,
                status_code=200,
                media_type=media_type,
                headers=headers,
            )

        # Target is not a file. If path has an extension, it's a missing asset -> 404
        last_seg = segments[-1] if segments else ""
        if "." in last_seg:
            return Response(status_code=404)

        # Path has no extension -> client-side route fallback to index.html
        index_file = dist_resolved / "index.html"
        if not index_file.is_file():
            return Response(
                status_code=404, content="Index not found", media_type="text/plain"
            )

        index_headers = {"Cache-Control": "no-cache"}
        if request.method == "HEAD":
            index_headers["Content-Length"] = str(index_file.stat().st_size)
            return Response(
                status_code=200,
                media_type="text/html; charset=utf-8",
                headers=index_headers,
            )

        index_content = index_file.read_bytes()
        index_headers["Content-Length"] = str(len(index_content))
        return Response(
            content=index_content,
            status_code=200,
            media_type="text/html; charset=utf-8",
            headers=index_headers,
        )
