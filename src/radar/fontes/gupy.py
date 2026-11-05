"""Portal Gupy (portal.gupy.io). A página de busca traz as vagas em JSON no bloco __NEXT_DATA__."""

from __future__ import annotations

import json
import re
from datetime import date
from urllib.parse import quote

from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import limpar_html
from .base import ESTADOS, Fonte, data_iso

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
                remota=j.get("workplaceType") == "remote",
            )
        )
    total = int((lista.get("pagination") or {}).get("total") or len(vagas))
    return vagas, total


class Gupy(Fonte):
    nome = "gupy"
    titulo = "Gupy"
    site = "https://portal.gupy.io"

    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int) -> list[Vaga]:
        estado = ESTADOS.get(cidade.uf, cidade.uf)
        base = (
            f"{self.site}/job-search/term=aprendiz"
            f"&city={quote(cidade.nome)}&state={quote(estado)}"
        )
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
        for v in vagas:
            # A Gupy devolve o estado por extenso; padroniza para a sigla.
            if v.uf == estado:
                v.uf = cidade.uf
        return vagas

    tem_remotas = True

    async def buscar_remotas(self, cliente: Cliente, max_paginas: int) -> list[Vaga]:
        base = f"{self.site}/job-search/term=aprendiz&workplaceTypes[]=remote"
        vagas: list[Vaga] = []
        for pagina in range(1, max_paginas + 1):
            url = base if pagina == 1 else f"{base}&page={pagina}"
            novas, total = interpretar((await cliente.get(url)).text)
            vagas.extend(novas)
            if not novas or len(vagas) >= total:
                break
        siglas = {nome: sigla for sigla, nome in ESTADOS.items()}
        for v in vagas:
            v.uf = siglas.get(v.uf, v.uf)
        return [v for v in vagas if v.remota]
