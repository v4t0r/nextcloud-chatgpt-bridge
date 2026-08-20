from __future__ import annotations

import ipaddress

import pytest

from nextcloud_chatgpt_bridge.egress_proxy import (
    EgressProxyError,
    parse_connect_target,
    require_global_addresses,
)


def test_connect_target_accepts_only_https_authority():
    assert parse_connect_target("cloud.example.com:443") == ("cloud.example.com", 443)
    assert parse_connect_target("[2606:4700:4700::1111]:443") == (
        "2606:4700:4700::1111",
        443,
    )

    for target in (
        "cloud.example.com:80",
        "https://cloud.example.com:443",
        "user@cloud.example.com:443",
        "cloud.example.com:443/path",
    ):
        with pytest.raises(EgressProxyError):
            parse_connect_target(target)


def test_global_address_policy_rejects_private_or_mixed_dns_answers():
    require_global_addresses({ipaddress.ip_address("1.1.1.1")})

    with pytest.raises(EgressProxyError, match="non-global"):
        require_global_addresses({ipaddress.ip_address("127.0.0.1")})

    with pytest.raises(EgressProxyError, match="non-global"):
        require_global_addresses(
            {
                ipaddress.ip_address("1.1.1.1"),
                ipaddress.ip_address("10.0.0.1"),
            }
        )

    with pytest.raises(EgressProxyError, match="did not resolve"):
        require_global_addresses(set())
