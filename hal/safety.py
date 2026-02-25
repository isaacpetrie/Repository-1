"""Network safety and SSRF protections."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


BLOCKED_IPS = {ipaddress.ip_address("169.254.169.254")}


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip in BLOCKED_IPS
    )


def _domain_allowed(hostname: str, allowlist: list[str]) -> bool:
    if not allowlist:
        return True
    hostname = hostname.lower()
    return any(hostname == d or hostname.endswith(f".{d}") for d in allowlist)


def validate_url_safety(url: str, allowlist_domains: list[str] | None = None) -> None:
    """Raise ValueError if URL is unsafe according to SSRF policy."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https URLs are allowed")
    if not parsed.hostname:
        raise ValueError("URL must include a hostname")

    allowlist_domains = allowlist_domains or []
    if not _domain_allowed(parsed.hostname, allowlist_domains):
        raise ValueError("Domain is not in HAL_ALLOWLIST_DOMAINS")

    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError(f"Failed to resolve hostname: {exc}") from exc

    for info in infos:
        ip_str = info[4][0]
        ip = ipaddress.ip_address(ip_str)
        if _is_blocked_ip(ip):
            raise ValueError(f"Blocked host/IP by SSRF policy: {ip}")
