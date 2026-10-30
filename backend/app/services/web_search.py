import ipaddress
import logging
import socket
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
import trafilatura

from app.core.errors import WebSearchUnavailableError

logger = logging.getLogger(__name__)

UNAVAILABLE_MESSAGE = "A busca na internet não está disponível. Verifique a conexão e: docker compose logs searxng"
MAX_REDIRECTS = 3
ALLOWED_PORTS = {"http": 80, "https": 443}
USER_AGENT = "Mozilla/5.0 (compatible; CelkeIALocal/1.0)"


@dataclass(frozen=True)
class WebResult:
    title: str
    url: str
    text: str


class WebSearch(Protocol):
    def ping(self) -> None: ...

    def search(self, query: str) -> list[WebResult]: ...


class BlockedUrlError(Exception):
    """O endereço não pode ser acessado: não é http(s) público."""


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def resolve_public_ip(host: str) -> str:
    """Só aceita o host se todos os endereços dele forem públicos (nada de containers ou rede local)."""
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise BlockedUrlError(f"Host não resolvido: {host}") from exc
    if not addresses or not all(_is_public(a) for a in addresses):
        raise BlockedUrlError(f"Host não público: {host}")
    return sorted(addresses)[0]


class SearxngSearch:
    """Pesquisa no SearXNG local e lê o texto das páginas encontradas. O texto das páginas é dado não confiável."""

    def __init__(
        self,
        base_url: str,
        timeout: float,
        max_results: int,
        page_max_chars: int,
        page_max_bytes: int = 2 * 1024 * 1024,
        resolve: Callable[[str], str] = resolve_public_ip,
        transport: httpx.BaseTransport | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_results = max_results
        self._page_max_chars = page_max_chars
        self._page_max_bytes = page_max_bytes
        self._resolve = resolve
        self._client = httpx.Client(timeout=timeout, transport=transport, trust_env=False)

    def ping(self) -> None:
        try:
            self._client.get(f"{self._base_url}/healthz", timeout=3).raise_for_status()
        except httpx.HTTPError as exc:
            raise WebSearchUnavailableError(UNAVAILABLE_MESSAGE) from exc

    def search(self, query: str) -> list[WebResult]:
        try:
            response = self._client.get(
                f"{self._base_url}/search", params={"q": query, "format": "json", "language": "pt-BR"}
            )
            response.raise_for_status()
            found = response.json().get("results", [])
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Falha na busca do SearXNG: %s", exc)
            raise WebSearchUnavailableError(UNAVAILABLE_MESSAGE) from exc

        candidates = [r for r in found if urlsplit(str(r.get("url", ""))).scheme in ALLOWED_PORTS]
        candidates = candidates[: self._max_results]
        if not candidates:
            return []
        with ThreadPoolExecutor(max_workers=len(candidates), thread_name_prefix="web-page") as pool:
            results = list(pool.map(self._to_result, candidates))
        return [r for r in results if r.text]

    def _to_result(self, item: dict) -> WebResult:
        url = str(item["url"])
        try:
            text = self._page_text(url)
        except (BlockedUrlError, httpx.HTTPError, ValueError, UnicodeError) as exc:
            logger.info("Página não lida (%s): %s", url, exc)
            text = ""
        # Página bloqueada, fora do ar ou sem texto: fica o resumo que o buscador devolveu.
        text = text or str(item.get("content") or "")
        return WebResult(title=str(item.get("title") or url), url=url, text=text[: self._page_max_chars].strip())

    def _page_text(self, url: str) -> str:
        for _ in range(MAX_REDIRECTS + 1):
            parts = urlsplit(url)
            default_port = ALLOWED_PORTS.get(parts.scheme)
            host = parts.hostname
            if default_port is None or host is None or (parts.port or default_port) != default_port:
                raise BlockedUrlError(f"Endereço não permitido: {url}")
            # Conecta no IP já conferido: o DNS não pode trocar o endereço entre a conferência e a conexão.
            ip = self._resolve(host)
            netloc = f"[{ip}]" if ":" in ip else ip
            pinned = urlunsplit((parts.scheme, netloc, parts.path or "/", parts.query, ""))
            with self._client.stream(
                "GET",
                pinned,
                headers={"Host": host, "User-Agent": USER_AGENT, "Accept": "text/html"},
                extensions={"sni_hostname": host},
            ) as response:
                if response.is_redirect and "location" in response.headers:
                    url = urljoin(url, response.headers["location"])
                    continue
                response.raise_for_status()
                if "html" not in response.headers.get("content-type", "").lower():
                    return ""
                return self._extract(self._read_limited(response), response.encoding or "utf-8")
        raise BlockedUrlError(f"Redirecionamentos demais: {url}")

    def _read_limited(self, response: httpx.Response) -> bytes:
        """Limita tamanho e tempo total: um site lento ou enorme não trava a resposta."""
        deadline = time.monotonic() + self._timeout
        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) >= self._page_max_bytes or time.monotonic() > deadline:
                break
        return bytes(body[: self._page_max_bytes])

    @staticmethod
    def _extract(body: bytes, encoding: str) -> str:
        return trafilatura.extract(body.decode(encoding, errors="replace"), include_comments=False) or ""
