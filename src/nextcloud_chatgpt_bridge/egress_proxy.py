from __future__ import annotations

import argparse
import asyncio
import ipaddress
import socket
from contextlib import suppress
from dataclasses import dataclass
from urllib.parse import urlsplit

from nextcloud_chatgpt_bridge import __version__


class EgressProxyError(ValueError):
    pass


@dataclass(slots=True, frozen=True)
class EgressProxyConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    max_connections: int = 256
    header_timeout_seconds: float = 10.0
    connect_timeout_seconds: float = 15.0
    idle_timeout_seconds: float = 60.0
    max_header_bytes: int = 16 * 1024


def parse_connect_target(target: str) -> tuple[str, int]:
    if not target or len(target) > 512 or any(ord(character) < 33 for character in target):
        raise EgressProxyError("Invalid CONNECT target")
    parsed = urlsplit(f"//{target}")
    if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise EgressProxyError("CONNECT target must contain only a host and port")
    hostname = parsed.hostname
    try:
        port = parsed.port
    except ValueError as exc:
        raise EgressProxyError("Invalid CONNECT port") from exc
    if not hostname or port != 443:
        raise EgressProxyError("Only HTTPS destinations on port 443 are allowed")
    try:
        normalized = hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise EgressProxyError("Invalid CONNECT hostname") from exc
    if not normalized or len(normalized) > 253:
        raise EgressProxyError("Invalid CONNECT hostname")
    return normalized, port


def require_global_addresses(addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address]) -> None:
    if not addresses:
        raise EgressProxyError("Destination did not resolve")
    if any(not address.is_global for address in addresses):
        raise EgressProxyError("Destination resolved to a non-global address")


async def resolve_public_addresses(
    hostname: str,
    port: int,
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    loop = asyncio.get_running_loop()
    try:
        records = await loop.getaddrinfo(
            hostname,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise EgressProxyError("Destination could not be resolved") from exc
    addresses = {ipaddress.ip_address(record[4][0]) for record in records}
    require_global_addresses(addresses)
    return sorted(addresses, key=lambda address: (address.version, int(address)))


async def _write_status(writer: asyncio.StreamWriter, status: int, reason: str) -> None:
    writer.write(
        f"HTTP/1.1 {status} {reason}\r\nConnection: close\r\nContent-Length: 0\r\n\r\n".encode(
            "ascii"
        )
    )
    with suppress(ConnectionError):
        await writer.drain()


async def _relay(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    *,
    idle_timeout_seconds: float,
) -> None:
    while True:
        data = await asyncio.wait_for(reader.read(64 * 1024), timeout=idle_timeout_seconds)
        if not data:
            return
        writer.write(data)
        await writer.drain()


class PublicHttpsEgressProxy:
    """CONNECT-only proxy that resolves, validates and pins every public destination."""

    def __init__(self, config: EgressProxyConfig) -> None:
        self.config = config
        self.connections = asyncio.Semaphore(config.max_connections)

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        acquired = False
        upstream_writer: asyncio.StreamWriter | None = None
        try:
            await asyncio.wait_for(self.connections.acquire(), timeout=1.0)
            acquired = True
            header = await asyncio.wait_for(
                reader.readuntil(b"\r\n\r\n"),
                timeout=self.config.header_timeout_seconds,
            )
            if len(header) > self.config.max_header_bytes:
                raise EgressProxyError("Proxy request headers are too large")
            request_line = header.split(b"\r\n", 1)[0].decode("ascii", "strict")
            parts = request_line.split(" ")
            if len(parts) != 3 or parts[0] != "CONNECT" or parts[2] not in {"HTTP/1.0", "HTTP/1.1"}:
                await _write_status(writer, 405, "Method Not Allowed")
                return
            hostname, port = parse_connect_target(parts[1])
            addresses = await resolve_public_addresses(hostname, port)

            upstream_reader: asyncio.StreamReader | None = None
            for address in addresses:
                try:
                    upstream_reader, upstream_writer = await asyncio.wait_for(
                        asyncio.open_connection(str(address), port),
                        timeout=self.config.connect_timeout_seconds,
                    )
                    break
                except (OSError, TimeoutError):
                    continue
            if upstream_reader is None or upstream_writer is None:
                await _write_status(writer, 502, "Bad Gateway")
                return

            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
            client_to_upstream = asyncio.create_task(
                _relay(
                    reader,
                    upstream_writer,
                    idle_timeout_seconds=self.config.idle_timeout_seconds,
                )
            )
            upstream_to_client = asyncio.create_task(
                _relay(
                    upstream_reader,
                    writer,
                    idle_timeout_seconds=self.config.idle_timeout_seconds,
                )
            )
            done, pending = await asyncio.wait(
                {client_to_upstream, upstream_to_client},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*done, *pending, return_exceptions=True)
        except (EgressProxyError, UnicodeError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            await _write_status(writer, 403, "Forbidden")
        except TimeoutError:
            await _write_status(writer, 408, "Request Timeout")
        finally:
            if upstream_writer is not None:
                upstream_writer.close()
                with suppress(ConnectionError):
                    await upstream_writer.wait_closed()
            writer.close()
            with suppress(ConnectionError):
                await writer.wait_closed()
            if acquired:
                self.connections.release()

    async def serve(self) -> None:
        server = await asyncio.start_server(
            self.handle,
            host=self.config.host,
            port=self.config.port,
            limit=self.config.max_header_bytes,
        )
        async with server:
            await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the internal public-address-only HTTPS egress proxy."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--max-connections", type=int, default=256)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or not 1 <= args.max_connections <= 10_000:
        parser.error("Port or connection limit is outside the allowed range")
    asyncio.run(
        PublicHttpsEgressProxy(
            EgressProxyConfig(
                host=args.host,
                port=args.port,
                max_connections=args.max_connections,
            )
        ).serve()
    )


if __name__ == "__main__":
    main()
