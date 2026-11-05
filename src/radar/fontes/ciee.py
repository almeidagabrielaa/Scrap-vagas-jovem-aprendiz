"""CIEE - Centro de Integração Empresa-Escola (portal.ciee.org.br).

A página "Quero uma vaga" lê as vagas de uma API pública em JSON (a mesma usada pelo site), filtrando por
município e tipo de programa. Cada vaga já traz bairro, salário ou bolsa, horário e escolaridade exigida.
O código do município vem de outra chamada da mesma API (`/core/city/search`).
"""

from __future__ import annotations

from urllib.parse import quote, urlencode

from ..filtro import APRENDIZ, ESTAGIO
from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import espacos, normalizar
from .base import Fonte, moeda

SITE = "https://portal.ciee.org.br"
API = "https://api.ciee.org.br"
PROGRAMAS = {APRENDIZ: "APRENDIZ", ESTAGIO: "ESTAGIO"}
POR_PAGINA = 50

ESCOLARIDADES = {
    "EF": "Ensino fundamental",
    "EM": "Ensino médio",
    "EP": "Ensino técnico",
    "TE": "Ensino técnico",
    "ES": "Ensino superior",
    "SU": "Ensino superior",
}


def interpretar(dados: dict) -> list[Vaga]:
    vagas = []
    for item in dados.get("content") or []:
        programa = item.get("tipoVaga") or ""
        area = espacos(item.get("areaAtuacao") or item.get("areaProfissional") or "")
        nome = "Jovem Aprendiz" if programa == "APRENDIZ" else "Estágio"
        local = item.get("local") or {}
        atividades = "; ".join(espacos(a) for a in item.get("atividades") or [] if a)
        valor = item.get("salario") or item.get("bolsaAuxilio")
        entrada, saida = (item.get("horarioEntrada") or "")[:5], (item.get("horarioSaida") or "")[:5]
        beneficios = [espacos(b.get("beneficio")) for b in item.get("beneficios") or [] if b.get("beneficio")]
        codigo = str(item["codigoVaga"])
        vagas.append(
            Vaga(
                fonte="ciee",
                id_fonte=codigo,
                titulo=f"{nome} - {area}" if area else nome,
                url=f"{SITE}/quero-uma-vaga/?codigoVaga={codigo}",
                empresa=espacos(item.get("nomeEmpresa")),
                cidade=local.get("cidade") or "",
                uf=local.get("uf") or "",
                descricao=espacos(f"{atividades}. Ramo da empresa: {item.get('descricao') or ''}"),
                # O CIEE informa o bairro em campo próprio; vai como endereço para o localizador.
                endereco=", ".join(p for p in (local.get("endereco"), local.get("bairro")) if p),
                cep=(local.get("cep") or "").replace("-", "") or None,
                eh_aprendiz_na_fonte=programa == "APRENDIZ",
                estagio_na_fonte=programa == "ESTAGIO",
                salario=f"{moeda(valor)}/mês" if valor else "",
                horario=f"{entrada} às {saida}" if entrada and saida else "",
                escolaridade=ESCOLARIDADES.get(item.get("nivelEscolar") or "", ""),
                beneficios=", ".join(beneficios),
            )
        )
    return vagas


class CIEE(Fonte):
    nome = "ciee"
    titulo = "CIEE"
    site = SITE
    tipos = frozenset(PROGRAMAS)
    abrir_anuncios = False

    def __init__(self) -> None:
        self._municipios: dict[tuple[str, str], int | None] = {}

    async def _municipio(self, cliente: Cliente, cidade: Cidade) -> int | None:
        chave = (normalizar(cidade.nome), cidade.uf)
        if chave not in self._municipios:
            dados = (await cliente.get(f"{API}/core/city/search?filter={quote(cidade.nome)}")).json()
            self._municipios[chave] = next(
                (
                    c["id"]
                    for c in dados.get("content") or []
                    if cidade.eh(c.get("cityName") or "") and (c.get("state") or {}).get("initials", "").upper() == cidade.uf
                ),
                None,
            )
        return self._municipios[chave]

    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int, tipo: str = APRENDIZ) -> list[Vaga]:
        municipio = await self._municipio(cliente, cidade)
        if municipio is None:
            return []
        vagas: list[Vaga] = []
        for pagina in range(max_paginas):
            consulta = {
                "page": pagina, "size": POR_PAGINA, "sort": "codigoVaga,desc",
                "codigoMunicipio": municipio, "tipoVaga": PROGRAMAS[tipo],
            }
            dados = (await cliente.get(f"{API}/vagas/vitrine-vaga/publicadas?{urlencode(consulta)}")).json()
            vagas.extend(interpretar(dados))
            if pagina + 1 >= int(dados.get("totalPages") or 0):
                break
        return vagas
