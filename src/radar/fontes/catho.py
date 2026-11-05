"""Catho (catho.com.br)."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import espacos
from .base import Fonte, data_br

SITE = "https://www.catho.com.br"


def interpretar(pagina: str, uf: str) -> list[Vaga]:
    sopa = BeautifulSoup(pagina, "html.parser")
    vagas = []
    for card in sopa.select("article.offer"):
        link = card.select_one("h2.title_offer a[href]")
        if not link:
            continue
        href = link["href"]
        empresa = card.select_one("p.mb-2 span.text-12")
        cidade = ""
        icone = card.select_one(".i_job_location")
        if icone and icone.parent:
            # "<strong>10 vagas</strong> - Cabo Frio"
            texto = icone.parent.get_text(" ", strip=True)
            cidade = espacos(texto.split("-", 1)[1]) if "-" in texto else ""
        data = card.select_one(".tag")
        vagas.append(
            Vaga(
                fonte="catho",
                id_fonte=href.rstrip("/").rsplit("/", 1)[-1],
                titulo=espacos(link.get("title") or link.get_text(" ")),
                url=urljoin(SITE, href),
                empresa=espacos(empresa.get_text(" ")) if empresa else "",
                cidade=cidade,
                uf=uf,
                publicada_em=data_br(data.get_text()) if data else None,
            )
        )
    return vagas


class Catho(Fonte):
    nome = "catho"
    titulo = "Catho"
    site = SITE

    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int) -> list[Vaga]:
        base = f"{SITE}/vagas/aprendiz/{cidade.slug}-{cidade.uf.lower()}/"
        vagas: list[Vaga] = []
        vistos: set[str] = set()
        for pagina in range(1, max_paginas + 1):
            url = base if pagina == 1 else f"{base}?page={pagina}"
            novas = [v for v in interpretar((await cliente.get(url)).text, cidade.uf) if v.id_fonte not in vistos]
            if not novas:
                break
            vistos.update(v.id_fonte for v in novas)
            vagas.extend(novas)
        return vagas
