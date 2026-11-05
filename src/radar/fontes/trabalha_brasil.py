"""Trabalha Brasil (trabalhabrasil.com.br).

A lista da cidade também mostra vagas de cidades vizinhas; elas são descartadas depois pelo filtro de cidade.
"""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import espacos, normalizar
from .base import Fonte, separar_local

SITE = "https://www.trabalhabrasil.com.br"


def interpretar(pagina: str) -> list[Vaga]:
    sopa = BeautifulSoup(pagina, "html.parser")
    vagas = []
    for card in sopa.select("article.job-card[data-job-id]"):
        link = card.select_one("a.job-link[href]")
        titulo = card.select_one(".job-title")
        if not link or not titulo:
            continue
        empresa = card.select_one(".job-company")
        local = card.select_one(".job-location")
        cidade, uf = separar_local(local.get_text(" ", strip=True)) if local else ("", "")
        vagas.append(
            Vaga(
                fonte="trabalhabrasil",
                id_fonte=card["data-job-id"],
                titulo=espacos(titulo.get_text(" ")),
                url=urljoin(SITE, link["href"]),
                empresa=espacos(empresa.get_text(" ")) if empresa else "",
                cidade=cidade,
                uf=uf,
            )
        )
    return vagas


class TrabalhaBrasil(Fonte):
    nome = "trabalhabrasil"
    titulo = "Trabalha Brasil"
    site = SITE

    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int) -> list[Vaga]:
        base = f"{SITE}/vagas-de-emprego-em-{cidade.slug}-{cidade.uf.lower()}/jovem-aprendiz"
        vagas: list[Vaga] = []
        vistos: set[str] = set()
        for pagina in range(1, max_paginas + 1):
            url = base if pagina == 1 else f"{base}?pagina={pagina}"
            lidas = interpretar((await cliente.get(url)).text)
            novas = [v for v in lidas if v.id_fonte not in vistos]
            if not novas:
                break
            vistos.update(v.id_fonte for v in novas)
            vagas.extend(novas)
            # Quando a lista passa a mostrar só cidades vizinhas, as próximas páginas não interessam.
            if not any(normalizar(v.cidade) == normalizar(cidade.nome) for v in novas):
                break
        return vagas
