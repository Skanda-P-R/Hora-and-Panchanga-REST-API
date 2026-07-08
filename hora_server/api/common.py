"""Shared API route helpers."""

from __future__ import annotations

from flask import current_app, request

from hora_server.service import PanchangaService, RequestContext


def service() -> PanchangaService:
    return current_app.extensions["panchanga_service"]


def context() -> RequestContext:
    return service().request_context(request.args)

