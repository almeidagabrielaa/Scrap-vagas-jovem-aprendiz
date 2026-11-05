"""InfoJobs (infojobs.com.br). Lê só a primeira página: as seguintes são carregadas por JavaScript."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import espacos
from .base import Fonte, data_iso, separar_local

SITE = "https://www.infojobs.com.br"


def interpretar(pagina: str) -> list[Vaga]:
    sopa = BeautifulSoup(pagina, "html.parser")
    vagas = []
    for card in sopa.select("div.js_vacancyLoad[data-id]"):
        titulo = card.select_one(".js_vacancyTitle")
        if not titulo:
            continue
        local = card.select_one("div.mb-8")
        # "Cabo Frio - RJ , 0 Km de você." -> "Cabo Frio - RJ"
        texto_local = local.get_text(" ", strip=True).split(",")[0] if local else ""
        cidade, uf = separar_local(texto_local)
        empresa = card.select_one("div.text-body")
        data = card.select_one(".js_date")
        # Modalidade aparece como etiqueta no cartão ("Home office", "Presencial", "Híbrido").
        etiquetas = " ".join(
            e.get_text(" ", strip=True) for e in card.select("div.text-medium div, div.text-medium span")
        )
        vagas.append(
            Vaga(
                fonte="infojobs",
                id_fonte=card["data-id"],
                titulo=espacos(titulo.get_text(" ")),
                url=urljoin(SITE, card.get("data-href", "")),
                empresa=espacos(empresa.get_text(" ")) if empresa else "",
                cidade=cidade,
                uf=uf,
                publicada_em=data_iso(data.get("data-value")) if data else None,
                remota=bool(re.search(r"(?i)\bhome office\b", etiquetas)),
            )
        )
    return vagas


class InfoJobs(Fonte):
    nome = "infojobs"
    titulo = "InfoJobs"
    site = SITE

    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int) -> list[Vaga]:
        url = f"{SITE}/vagas-de-emprego-aprendiz-em-{cidade.slug},-{cidade.uf.lower()}.aspx"
        return interpretar((await cliente.get(url)).text)

    tem_remotas = True

    async def buscar_remotas(self, cliente: Cliente, max_paginas: int) -> list[Vaga]:
        url = f"{SITE}/vagas-de-emprego-aprendiz-trabalho-home-office.aspx"
        return [v for v in interpretar((await cliente.get(url)).text) if v.remota]
