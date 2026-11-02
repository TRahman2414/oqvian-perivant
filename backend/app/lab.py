import asyncio
import secrets

HOST = "127.0.0.1"
PERMITTED_PORTS = range(18080, 18100)


class LocalLab:
    """Only starts listeners owned by this process on the loopback interface."""

    def __init__(self) -> None:
        self.servers: dict[str, asyncio.AbstractServer] = {}
        self.ports: dict[str, int] = {}
        self.tokens: dict[str, str] = {}

    async def _accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, token: str) -> None:
        try:
            data = await asyncio.wait_for(reader.read(1024), timeout=1.5)
            expected = f"GET /health?probe={token} HTTP/1.1".encode()
            if data.startswith(expected):
                body = f"OQVIAN PERIVANT LAB {token}\n".encode()
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: "
                    + str(len(body)).encode()
                    + b"\r\nConnection: close\r\n\r\n"
                    + body
                )
                await writer.drain()
        except (asyncio.TimeoutError, ConnectionError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    async def start(self, name: str, reserved_ports: set[int] | None = None, preferred_port: int | None = None) -> int:
        if name in self.servers:
            return self.ports[name]
        reserved = reserved_ports or set()
        candidates = ([preferred_port] if preferred_port in PERMITTED_PORTS else []) + [p for p in PERMITTED_PORTS if p != preferred_port]
        for port in candidates:
            if port in self.ports.values():
                continue
            if port in reserved and port != preferred_port:
                continue
            try:
                token = secrets.token_urlsafe(18)
                async def accept(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
                    await self._accept(reader, writer, token)
                server = await asyncio.start_server(accept, HOST, port)
            except OSError:
                continue
            self.servers[name] = server
            self.ports[name] = port
            self.tokens[name] = token
            return port
        raise RuntimeError("No available port in the permitted local lab range 18080–18099")

    async def stop(self, name: str) -> None:
        server = self.servers.pop(name, None)
        self.ports.pop(name, None)
        self.tokens.pop(name, None)
        if server:
            server.close()
            await server.wait_closed()

    async def stop_all(self) -> None:
        for name in tuple(self.servers):
            await self.stop(name)
