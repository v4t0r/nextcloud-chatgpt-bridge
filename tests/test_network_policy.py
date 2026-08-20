from __future__ import annotations

import socket

import pytest

from nextcloud_chatgpt_bridge.network_policy import (
    LocalSelfHostedPolicy,
    PublicHostedPolicy,
    TargetPolicyError,
)


def test_local_policy_allows_private_lan_nextcloud_over_https():
    LocalSelfHostedPolicy().validate_url("https://192.168.10.20/nextcloud")


def test_local_policy_still_requires_https_by_default():
    with pytest.raises(TargetPolicyError, match="HTTPS"):
        LocalSelfHostedPolicy().validate_url("http://192.168.10.20/nextcloud")


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1",
        "https://10.0.0.5",
        "https://192.168.1.2",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]",
    ],
)
def test_public_policy_blocks_non_global_literal_targets(url: str):
    with pytest.raises(TargetPolicyError, match="non-global|Localhost"):
        PublicHostedPolicy().validate_url(url)


def test_public_policy_blocks_non_standard_port():
    with pytest.raises(TargetPolicyError, match="port"):
        PublicHostedPolicy().validate_url("https://cloud.example.com:8443")


def test_public_policy_rejects_domain_if_any_dns_answer_is_private(monkeypatch):
    def fake_getaddrinfo(hostname, port, **kwargs):
        assert hostname == "cloud.example.com"
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.10", port)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(TargetPolicyError, match="non-global"):
        PublicHostedPolicy().validate_url("https://cloud.example.com")


def test_public_policy_accepts_global_dns_answers(monkeypatch):
    def fake_getaddrinfo(hostname, port, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2606:4700:4700::1111", port, 0, 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    PublicHostedPolicy().validate_url("https://cloud.example.com")
