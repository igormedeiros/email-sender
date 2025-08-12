import socket
from typing import Any

import pytest


class NetworkAccessError(RuntimeError):
    """Raised when any code attempts to use the network during tests."""


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Block all outbound network access for every test.

    - Patches common socket entrypoints (connect, connect_ex, create_connection, getaddrinfo)
    - Patches requests' Session.request if requests is installed
    - Patches urllib3 HTTPConnectionPool.urlopen if urllib3 is installed
    """

    def raise_network(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover - trivial guard
        raise NetworkAccessError(
            "Acesso à rede está desabilitado nos testes. Use mocks/stubs."
        )

    # Patch low-level socket functions
    monkeypatch.setattr("socket.socket.connect", raise_network, raising=True)
    monkeypatch.setattr("socket.socket.connect_ex", raise_network, raising=True)
    monkeypatch.setattr("socket.create_connection", raise_network, raising=True)
    monkeypatch.setattr("socket.getaddrinfo", raise_network, raising=True)

    # Optionally patch high-level HTTP stacks if available
    try:  # requests
        import requests  # type: ignore

        monkeypatch.setattr(
            "requests.sessions.Session.request", raise_network, raising=True
        )
    except Exception:
        pass

    try:  # urllib3
        monkeypatch.setattr(
            "urllib3.connectionpool.HTTPConnectionPool.urlopen",
            raise_network,
            raising=True,
        )
    except Exception:
        pass
