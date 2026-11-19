"""Validate public indicator syntax without DNS or network access."""

import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit


def domain(value: str) -> str:
    host = value.rstrip(".").encode("idna").decode("ascii").lower()
    if len(host) > 253 or "." not in host:
        raise ValueError("Invalid public domain")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP literals not supported")
    if host.rsplit(".", 1)[-1].isdigit() or host.endswith(
        (".local", ".localhost", ".internal", ".onion", ".home", ".lan")
    ):
        raise ValueError("Non-public domain")
    if any(
        not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in host.split(".")
    ):
        raise ValueError("Invalid domain label")
    return host


def url(value: str) -> str:
    if (
        len(value) > 2048
        or any(ord(c) <= 32 or ord(c) == 127 for c in value)
        or "\\" in value
    ):
        raise ValueError("Invalid URL characters or length")
    p = urlsplit(value)
    if (
        p.scheme not in ("http", "https")
        or not p.hostname
        or p.username is not None
        or p.password is not None
    ):
        raise ValueError("Invalid URL scheme or authority")
    host = domain(p.hostname)
    if p.port not in (None, 80 if p.scheme == "http" else 443):
        raise ValueError("Non-default port not supported")
    return urlunsplit((p.scheme, host, p.path or "/", p.query, ""))


def phone(value: str) -> str:
    if not re.fullmatch(r"\+[1-9][0-9]{6,14}", value):
        raise ValueError("Expected E.164 format")
    return value
