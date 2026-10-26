"""Fail-closed transport security configuration for the public MCP endpoint."""
from __future__ import annotations

import os
from urllib.parse import urlsplit

from mcp.server.transport_security import TransportSecuritySettings


LOCAL_HOSTS = (
    "localhost",
    "localhost:*",
    "127.0.0.1",
    "127.0.0.1:*",
    "[::1]",
    "[::1]:*",
)
LOCAL_ORIGINS = (
    "http://localhost:*",
    "http://127.0.0.1:*",
    "http://[::1]:*",
)


def _csv(name: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, "").split(",") if value.strip()]


def _deployment_hosts() -> list[str]:
    """Read hostnames supplied by supported free-first deployment platforms."""
    hosts = _csv("PALM92_ALLOWED_HOSTS")
    hosts.extend(_csv("RENDER_EXTERNAL_HOSTNAME"))
    hosts.extend(_csv("VERCEL_URL"))
    return hosts


def _validate_host(host: str) -> str:
    if "://" in host or "/" in host or host == "*":
        raise RuntimeError(
            "MCP allowed hosts must be exact hostnames or hostname:* patterns, not URLs or '*'."
        )
    return host


def _validate_origin(origin: str) -> str:
    parsed = urlsplit(origin.removesuffix(":*"))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path:
        raise RuntimeError(
            "MCP allowed origins must be complete http(s) origins without a path."
        )
    return origin


def build_transport_security() -> TransportSecuritySettings:
    """Build an enabled allow-list, with safe local development defaults.

    Public hosts are never inferred from an incoming request. They must come from
    a deployment platform variable or the explicit Palm92 allow-list.
    """
    hosts = [*LOCAL_HOSTS, *(_validate_host(host) for host in _deployment_hosts())]
    origins = [
        *LOCAL_ORIGINS,
        *(_validate_origin(origin) for origin in _csv("PALM92_ALLOWED_ORIGINS")),
    ]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=list(dict.fromkeys(hosts)),
        allowed_origins=list(dict.fromkeys(origins)),
    )
