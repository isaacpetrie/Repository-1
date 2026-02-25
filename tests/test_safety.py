from __future__ import annotations

import socket

import pytest

from hal.safety import validate_url_safety


@pytest.fixture
def fake_dns(monkeypatch: pytest.MonkeyPatch):
    def _set(ip: str):
        def _fake_getaddrinfo(*args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)

    return _set


def test_blocks_private_ip(fake_dns):
    fake_dns("127.0.0.1")
    with pytest.raises(ValueError):
        validate_url_safety("http://localhost")


def test_allowlist_blocks_non_member(fake_dns):
    fake_dns("93.184.216.34")
    with pytest.raises(ValueError):
        validate_url_safety("https://example.net", ["example.com"])


def test_public_ip_passes(fake_dns):
    fake_dns("93.184.216.34")
    validate_url_safety("https://example.com")
