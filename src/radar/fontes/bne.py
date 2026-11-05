"""BNE - Banco Nacional de Empregos (bne.com.br).

A página de busca traz as vagas num JSON (campo oculto "jobInfoLocal"), com cidade, empresa, bairro e a
marcação de home office. A lista da cidade continua com vagas de outras cidades do estado; elas são descartadas.
O BNE mantém anúncios antigos no ar, por isso vagas publicadas há mais de IDADE_MAXIMA_DIAS são ignoradas.
"""

from __future__ import annotations

import html
import json
import re
from datetime import date, timedelta

from bs4 import BeautifulSoup

from ..filtro import APRENDIZ, ESTAGIO
from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import espacos
from .base import Fonte, data_iso

SITE = "https://www.bne.com.br"
FUNCOES = {APRENDIZ: "jovem-aprendiz", ESTAGIO: "estagiario"}
IDADE_MAXIMA_DIAS = 120

_JSON = re.compile(r'id="jobInfoLocal"\s+value="([^"]*)"')


def interpretar(pagina: str, hoje: date | None = None) -> list[Vaga]:
    m = _JSON.search(pagina)
    if not m:
        raise ValueError("lista de vagas (jobInfoLocal) não encontrada (o layout do BNE mudou?)")
    limite = (hoje or date.today()) - timedelta(days=IDADE_MAXIMA_DIAS)
    sopa = BeautifulSoup(pagina, "html.parser")
    vagas = []
    for item in json.loads(html.unescape(m.group(1))):
        publicada = data_iso(item.get("PostDate"))
        if publicada and publicada < limite:
            continue
        funcao = (item.get("Function") or {}).get("Name") or ""
        cartao = sopa.find(id=f"job-miniature-{item['Id']}")
        descricao = ""
        if cartao:
            paragrafo = cartao.find("p")
            descricao = espacos(paragrafo.get_text(" ")) if paragrafo else ""
        cidade = item.get("City") or {}
        vagas.append(
            Vaga(
                fonte="bne",
                id_fonte=str(item["Id"]),
                titulo=espacos(item.get("Titulo") or f"Vaga de {funcao}"),
                url=item.get("Url") or f"{SITE}{item.get('PathUrlJob', '')}",
                empresa="" if item.get("Confidential") else espacos(item.get("CompanyName")),
                cidade=cidade.get("Name") or "",
                uf=item.get("StateAbbreviation") or "",
                descricao=descricao,
                # O BNE às vezes informa o bairro; vai como endereço para o localizador.
                endereco=espacos(item.get("Neighborhood")),
                publicada_em=publicada,
                eh_aprendiz_na_fonte="aprendiz" in funcao.lower(),
                remota=bool(item.get("Home_Office")),
            )
        )
    return vagas


class BNE(Fonte):
    nome = "bne"
    titulo = "BNE"
    site = SITE
    tem_remotas = True
    tipos = frozenset(FUNCOES)

    async def _paginas(self, cliente: Cliente, base: str, max_paginas: int, continuar) -> list[Vaga]:
        vagas: list[Vaga] = []
        vistos: set[str] = set()
        for pagina in range(1, max_paginas + 1):
            url = base if pagina == 1 else f"{base}?page={pagina}"
            lidas = [v for v in interpretar((await cliente.get(url)).text) if v.id_fonte not in vistos]
            if not lidas:
                break
            vistos.update(v.id_fonte for v in lidas)
            vagas.extend(lidas)
            if not continuar(lidas):
                break
        return vagas

    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int, tipo: str = APRENDIZ) -> list[Vaga]:
        base = f"{SITE}/vagas-de-emprego-para-{FUNCOES[tipo]}-em-{cidade.slug}-{cidade.uf.lower()}"
        # As vagas da cidade vêm primeiro; quando a página só tem outras cidades, para.
        return await self._paginas(cliente, base, max_paginas, lambda lidas: any(cidade.eh(v.cidade) for v in lidas))

    async def buscar_remotas(self, cliente: Cliente, max_paginas: int, tipo: str = APRENDIZ) -> list[Vaga]:
        vagas = await self._paginas(cliente, f"{SITE}/vagas-de-emprego-para-{FUNCOES[tipo]}", max_paginas, lambda _: True)
        return [v for v in vagas if v.remota]
