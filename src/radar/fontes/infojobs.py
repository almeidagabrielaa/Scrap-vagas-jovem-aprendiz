"""InfoJobs (infojobs.com.br).

A primeira página vem no HTML; as seguintes o site carrega por JavaScript (rolagem infinita), pedindo o mesmo
HTML dos cartões a `/mf-publicarea/VacancyList/GetVacancyListFragment?url=<lista>&page=N`. O radar faz o mesmo,
usando o endereço da lista que a própria página informa (campo `hdn_ListURL`).

Meio período usa o filtro de jornada do próprio site (parâmetro `wo`): 2 = parcial manhãs, 5 = parcial tardes,
6 = parcial noites. Por isso essas vagas já vêm marcadas como meio período, mesmo sem dizer isso no título.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from ..filtro import APRENDIZ, ESTAGIO, MEIO_PERIODO, PRIMEIRO_EMPREGO
from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import espacos
from .base import Fonte, data_iso, separar_local

SITE = "https://www.infojobs.com.br"
FRAGMENTO = f"{SITE}/mf-publicarea/VacancyList/GetVacancyListFragment"
_LISTA = re.compile(r'id="hdn_ListURL"\s+value="([^"]*)"')
JORNADA_PARCIAL = "wo=2,5,6"
# Começo do endereço de busca e filtro extra, por tipo de vaga.
BUSCAS = {
    APRENDIZ: ("vagas-de-emprego-aprendiz", ""),
    ESTAGIO: ("vagas-de-emprego-estagio", ""),
    MEIO_PERIODO: ("vagas-de-emprego", f"?{JORNADA_PARCIAL}"),
    # A busca devolve também vagas que só citam o termo; o filtro confirma pelo texto do anúncio.
    PRIMEIRO_EMPREGO: ("vagas-de-emprego-primeiro-emprego", ""),
}


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
    tipos = frozenset(BUSCAS)
    tem_remotas = True

    @staticmethod
    def _ler(pagina: str, tipo: str) -> list[Vaga]:
        vagas = interpretar(pagina)
        for v in vagas:
            v.meio_periodo_na_fonte = tipo == MEIO_PERIODO
        return vagas

    async def _paginas(
        self, cliente: Cliente, url: str, max_paginas: int, tipo: str, continuar: Callable[[list[Vaga]], bool]
    ) -> list[Vaga]:
        primeira = (await cliente.get(url)).text
        vagas = self._ler(primeira, tipo)
        vistos = {v.id_fonte for v in vagas}
        m = _LISTA.search(primeira)
        lista = m.group(1) if m else url
        for pagina in range(2, max_paginas + 1):
            if not vagas or not continuar(vagas[-20:]):
                break
            endereco = f"{lista}{'&' if '?' in lista else '?'}page={pagina}"
            try:
                dados = (await cliente.get(f"{FRAGMENTO}?url={quote(endereco, safe='')}", tentativas=2)).json()
            except Exception:
                break  # as páginas extras são bônus: se falharem, fica o que já foi lido
            novas = [v for v in self._ler(dados.get("listFragmentHTML") or "", tipo) if v.id_fonte not in vistos]
            if not novas:
                break
            vistos.update(v.id_fonte for v in novas)
            vagas.extend(novas)
            if dados.get("eof"):
                break
        return vagas

    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int, tipo: str = APRENDIZ) -> list[Vaga]:
        inicio, extra = BUSCAS[tipo]
        url = f"{SITE}/{inicio}-em-{cidade.slug},-{cidade.uf.lower()}.aspx{extra}"
        # Depois das vagas da cidade o site completa a lista com vagas de "Todo Brasil": aí para.
        return await self._paginas(cliente, url, max_paginas, tipo, lambda lidas: any(cidade.eh(v.cidade) for v in lidas))

    async def buscar_remotas(self, cliente: Cliente, max_paginas: int, tipo: str = APRENDIZ) -> list[Vaga]:
        inicio, extra = BUSCAS[tipo]
        url = f"{SITE}/{inicio}-trabalho-home-office.aspx{extra}"
        return [v for v in await self._paginas(cliente, url, max_paginas, tipo, lambda _: True) if v.remota]
