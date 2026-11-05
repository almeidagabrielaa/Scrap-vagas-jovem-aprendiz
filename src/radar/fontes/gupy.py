"""Portal Gupy (portal.gupy.io). A página de busca traz as vagas em JSON no bloco __NEXT_DATA__."""

from __future__ import annotations

import json
import re
from datetime import date
from urllib.parse import quote

from ..filtro import APRENDIZ, ESTAGIO, MEIO_PERIODO
from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import limpar_html
from .base import ESTADOS, Fonte, data_iso

_SIGLAS = {nome: sigla for sigla, nome in ESTADOS.items()}

_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def encerrada(job: dict, hoje: date | None = None) -> bool:
    """A busca da Gupy às vezes devolve vagas antigas de páginas de carreira desativadas."""
    if "inactive" in (job.get("jobUrl") or ""):
        return True
    prazo = data_iso(job.get("applicationDeadline"))
    return prazo is not None and prazo < (hoje or date.today())


def interpretar(pagina: str) -> tuple[list[Vaga], int]:
    """Devolve (vagas abertas, total informado pelo site)."""
    m = _NEXT_DATA.search(pagina)
    if not m:
        raise ValueError("bloco __NEXT_DATA__ não encontrado (o layout da Gupy mudou?)")
    dados = json.loads(m.group(1))
    lista = dados["props"]["pageProps"].get("initialJobList") or {}
    vagas = []
    for j in lista.get("data") or []:
        if encerrada(j):
            continue
        vagas.append(
            Vaga(
                fonte="gupy",
                id_fonte=str(j["id"]),
                titulo=j.get("name", "").strip(),
                url=j.get("jobUrl", ""),
                empresa=(j.get("careerPageName") or "").strip(),
                cidade=j.get("city") or "",
                uf=j.get("state") or "",
                descricao=limpar_html(j.get("description")),
                publicada_em=data_iso(j.get("publishedDate")),
                eh_aprendiz_na_fonte=j.get("type") == "vacancy_type_apprentice",
                estagio_na_fonte=j.get("type") == "vacancy_type_internship",
                remota=j.get("workplaceType") == "remote",
            )
        )
    total = int((lista.get("pagination") or {}).get("total") or len(vagas))
    return vagas, total


# Termo de busca por tipo. Para meio período, só "part time" funciona: a busca da Gupy procura no nome
# da vaga, e "meio período" (com ou sem acento) não devolve nada nem no Rio de Janeiro.
TERMOS = {APRENDIZ: "aprendiz", ESTAGIO: "estágio", MEIO_PERIODO: "part time"}


class Gupy(Fonte):
    nome = "gupy"
    titulo = "Gupy"
    site = "https://portal.gupy.io"
    tipos = frozenset(TERMOS)
    tem_remotas = True

    async def _paginas(self, cliente: Cliente, base: str, max_paginas: int) -> list[Vaga]:
        vagas: list[Vaga] = []
        vistos: set[str] = set()
        for pagina in range(1, max_paginas + 1):
            url = base if pagina == 1 else f"{base}&page={pagina}"
            novas, total = interpretar((await cliente.get(url)).text)
            novas = [v for v in novas if v.id_fonte not in vistos]
            if not novas:
                break
            vistos.update(v.id_fonte for v in novas)
            vagas.extend(novas)
            if len(vagas) >= total:
                break
        # A Gupy devolve o estado por extenso; padroniza para a sigla.
        for v in vagas:
            v.uf = _SIGLAS.get(v.uf, v.uf)
        return vagas

    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int, tipo: str = APRENDIZ) -> list[Vaga]:
        estado = ESTADOS.get(cidade.uf, cidade.uf)
        base = f"{self.site}/job-search/term={quote(TERMOS[tipo])}&city={quote(cidade.nome)}&state={quote(estado)}"
        return await self._paginas(cliente, base, max_paginas)

    async def buscar_remotas(self, cliente: Cliente, max_paginas: int, tipo: str = APRENDIZ) -> list[Vaga]:
        base = f"{self.site}/job-search/term={quote(TERMOS[tipo])}&workplaceTypes[]=remote"
        return [v for v in await self._paginas(cliente, base, max_paginas) if v.remota]
