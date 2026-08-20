from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit


class TargetPolicyError(ValueError):
    pass


class TargetPolicy(Protocol):
    def validate_url(self, url: str) -> None: ...


@dataclass(slots=True, frozen=True)
class LocalSelfHostedPolicy:
    """Local/self-hosted bridge policy: HTTPS required, private Nextcloud hosts allowed."""

    allow_insecure_http: bool = False

    def validate_url(self, url: str) -> None:
        parsed = urlsplit(url)
        schemes = {"https", "http"} if self.allow_insecure_http else {"https"}
        if parsed.scheme.lower() not in schemes:
            raise TargetPolicyError("Nextcloud URL must use HTTPS")
        if not parsed.hostname:
            raise TargetPolicyError("Nextcloud URL is missing a hostname")
        if parsed.username or parsed.password:
            raise TargetPolicyError("Credentials must not be embedded in the Nextcloud URL")
        if parsed.query or parsed.fragment:
            raise TargetPolicyError("Nextcloud URL must not contain query parameters or fragments")


@dataclass(slots=True, frozen=True)
class PublicHostedPolicy:
    """Preflight target policy for a public multi-tenant bridge.

    This blocks obvious SSRF targets before a request. Production deployment MUST additionally
    enforce the same policy at the network/egress layer so DNS rebinding cannot bypass it between
    validation and socket connection.
    """

    allowed_ports: tuple[int, ...] = (443,)

    def validate_url(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme.lower() != "https":
            raise TargetPolicyError("Hosted Nextcloud connections require HTTPS")
        hostname = parsed.hostname
        if not hostname:
            raise TargetPolicyError("Nextcloud URL is missing a hostname")
        if parsed.username or parsed.password:
            raise TargetPolicyError("Credentials must not be embedded in the Nextcloud URL")
        if parsed.query or parsed.fragment:
            raise TargetPolicyError("Nextcloud URL must not contain query parameters or fragments")

        port = parsed.port or 443
        if port not in self.allowed_ports:
            raise TargetPolicyError("Nextcloud URL uses a port not allowed by hosted policy")

        normalized_host = hostname.rstrip(".").lower()
        if normalized_host in {"localhost", "localhost.localdomain"} or normalized_host.endswith(
            ".localhost"
        ):
            raise TargetPolicyError("Localhost targets are not allowed by hosted policy")

        try:
            literal = ipaddress.ip_address(normalized_host)
        except ValueError:
            addresses = self._resolve(normalized_host, port)
        else:
            addresses = {literal}

        if not addresses:
            raise TargetPolicyError("Nextcloud hostname did not resolve")
        for address in addresses:
            if not address.is_global:
                raise TargetPolicyError(
                    "Private, loopback, link-local, reserved and other non-global targets are blocked"
                )

    @staticmethod
    def _resolve(hostname: str, port: int) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        try:
            records = socket.getaddrinfo(
                hostname,
                port,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise TargetPolicyError("Nextcloud hostname could not be resolved") from exc

        addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
        for _family, _socktype, _proto, _canonname, sockaddr in records:
            addresses.add(ipaddress.ip_address(sockaddr[0]))
        return addresses
