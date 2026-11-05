"""Vagas.com.br. Lê só a primeira página (até cerca de 25 vagas)."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import espacos
from .base import Fonte, data_br, separar_local

SITE = "https://www.vagas.com.br"


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

    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int) -> list[Vaga]:
        url = f"{SITE}/vagas-de-aprendiz-em-{cidade.slug}"
        return interpretar((await cliente.get(url)).text)
