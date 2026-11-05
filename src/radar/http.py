"""Cliente HTTP educado: limite de concorrência, pausa por site, novas tentativas e robots.txt."""

from __future__ import annotations

import asyncio
import time
import urllib.robotparser
from urllib.parse import urlsplit

import httpx

from . import __version__

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    f"(KHTML, like Gecko) Chrome/128.0 Safari/537.36 RadarAprendiz/{__version__}"
)


class BloqueadoPeloRobots(Exception):
    pass


class Cliente:
    def __init__(self, concorrencia: int = 6, pausa_por_site: float = 1.0, timeout: float = 25.0):
        self._http = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"},
            follow_redirects=True,
            timeout=timeout,
        )
        self._semaforo = asyncio.Semaphore(concorrencia)
        self._pausa = pausa_por_site
        self._travas: dict[str, asyncio.Lock] = {}
        self._ultimo: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    async def __aenter__(self) -> "Cliente":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._http.aclose()

    async def _permitido(self, url: str) -> bool:
        partes = urlsplit(url)
        base = f"{partes.scheme}://{partes.netloc}"
        if base not in self._robots:
            parser: urllib.robotparser.RobotFileParser | None = urllib.robotparser.RobotFileParser()
            try:
                r = await self._http.get(base + "/robots.txt")
                if r.status_code >= 400:
                    parser = None  # sem robots.txt: tudo permitido
                else:
                    parser.parse(r.text.splitlines())
            except httpx.HTTPError:
                parser = None
            self._robots[base] = parser
        parser = self._robots[base]
        return parser is None or parser.can_fetch(USER_AGENT, url)

    async def _esperar_vez(self, host: str) -> None:
        trava = self._travas.setdefault(host, asyncio.Lock())
        async with trava:
            espera = self._ultimo.get(host, 0) + self._pausa - time.monotonic()
            if espera > 0:
                await asyncio.sleep(espera)
            self._ultimo[host] = time.monotonic()

    async def get(self, url: str, tentativas: int = 3, respeitar_robots: bool = True, **kwargs) -> httpx.Response:
        if respeitar_robots and not await self._permitido(url):
            raise BloqueadoPeloRobots(f"robots.txt não permite acessar {url}")
        host = urlsplit(url).netloc
        ultimo_erro: Exception | None = None
        for tentativa in range(tentativas):
            await self._esperar_vez(host)
            try:
                async with self._semaforo:
                    resposta = await self._http.get(url, **kwargs)
                if resposta.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError(
                        f"HTTP {resposta.status_code}", request=resposta.request, response=resposta
                    )
                resposta.raise_for_status()
                return resposta
            except httpx.HTTPStatusError as e:
                ultimo_erro = e
                if e.response.status_code not in (429, 500, 502, 503, 504):
                    break
            except httpx.TransportError as e:
                ultimo_erro = e
            await asyncio.sleep(1.5 * (tentativa + 1))
        assert ultimo_erro is not None
        raise ultimo_erro
