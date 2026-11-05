"""Vagas.com.br. A lista é paginada com `?pagina=N` (o site anuncia a próxima em <link rel="next">)."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..filtro import APRENDIZ, ESTAGIO
from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import espacos
from .base import Fonte, data_br, separar_local

SITE = "https://www.vagas.com.br"
_PROXIMA = re.compile(r"<link[^>]+rel=['\"]next['\"]", re.I)
TERMOS = {APRENDIZ: "aprendiz", ESTAGIO: "estagio"}


def interpretar(pagina: str) -> list[Vaga]:
    sopa = BeautifulSoup(pagina, "html.parser")
    vagas = []
    for item in sopa.select("li.vaga"):
        link = item.select_one("a.link-detalhes-vaga[href]")
        if not link:
            continue
        empresa = item.select_one(".emprVaga")
        local = item.select_one(".vaga-local")
        texto_local = ""
        if local:
            # O tooltip ("A empresa aceita candidaturas de...") fica dentro do mesmo bloco.
            texto_local = next((s.strip() for s in local.find_all(string=True, recursive=False) if s.strip()), "")
        cidade, uf = separar_local(texto_local)
        data = item.select_one(".data-publicacao")
        vagas.append(
            Vaga(
                fonte="vagas.com",
                id_fonte=link.get("data-id-vaga") or link["href"],
                titulo=espacos(link.get("title") or link.get_text(" ")),
                url=urljoin(SITE, link["href"]),
                empresa=espacos(empresa.get_text(" ")) if empresa else "",
                cidade=cidade,
                uf=uf,
                publicada_em=data_br(data.get_text()) if data else None,
            )
        )
    return vagas


class VagasCom(Fonte):
    nome = "vagas.com"
    titulo = "Vagas.com.br"
    site = SITE
    tipos = frozenset(TERMOS)

    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int, tipo: str = APRENDIZ) -> list[Vaga]:
        base = f"{SITE}/vagas-de-{TERMOS[tipo]}-em-{cidade.slug}"
        vagas: list[Vaga] = []
        vistos: set[str] = set()
        for pagina in range(1, max_paginas + 1):
            texto = (await cliente.get(base if pagina == 1 else f"{base}?pagina={pagina}")).text
            novas = [v for v in interpretar(texto) if v.id_fonte not in vistos]
            if not novas:
                break
            vistos.update(v.id_fonte for v in novas)
            vagas.extend(novas)
            if not _PROXIMA.search(texto):
                break
        return vagas
