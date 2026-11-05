"""Isbet - Instituto Brasileiro Pró-Educação, Trabalho e Desenvolvimento (isbet.org.br).

A página "Quero uma vaga" pede as vagas ao próprio WordPress (`admin-ajax.php?action=buscar_vagas_campos_api`).
O filtro por município do site não funciona, então o radar lê a lista do estado (10 vagas por página) uma vez
por execução e separa por cidade. Cada vaga traz salário, horário, horas por dia, CEP e benefícios.
"""

from __future__ import annotations

import asyncio
import weakref
from urllib.parse import urlencode

from ..filtro import APRENDIZ, ESTAGIO
from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import espacos
from .base import Fonte, moeda

SITE = "https://isbet.org.br"
PROGRAMAS = {APRENDIZ: "J", ESTAGIO: "E"}
MAX_PAGINAS_ESTADO = 10  # o estado inteiro: 10 páginas de 10 vagas cobrem as listas atuais do RJ com folga


def interpretar(dados: dict) -> tuple[list[Vaga], int]:
    """Devolve (vagas, total de páginas)."""
    corpo = dados.get("data") or {}
    vagas = []
    for item in corpo.get("lista_vagas") or []:
        aprendiz = item.get("tipo_programa") == "J"
        area = espacos(item.get("curso_formacao") or (item.get("objeto_area_vaga") or {}).get("nm_area_vaga"))
        nome = "Jovem Aprendiz" if aprendiz else "Estágio"
        municipio = item.get("objeto_municipio") or {}
        inicio, fim = item.get("horario_inicio_trabalho") or "", item.get("horario_fim_trabalho") or ""
        horas = item.get("hh_diaria")
        salario = item.get("salario_descricao") or (moeda(item["salario"]) if item.get("salario") else "")
        vagas.append(
            Vaga(
                fonte="isbet",
                id_fonte=str(item["id_vaga"]),
                titulo=f"{nome} - {area}" if area else nome,
                url=item.get("url_processo_seletivo") or f"{SITE}/quero-uma-vaga/",
                cidade=item.get("localidade") or municipio.get("nm_municipio") or "",
                uf=municipio.get("cd_uf") or "",
                descricao=espacos(item.get("atividades")),
                cep=(item.get("cep_trabalho") or "").replace("-", "") or None,
                eh_aprendiz_na_fonte=aprendiz,
                estagio_na_fonte=not aprendiz,
                salario=f"{salario}/mês" if salario else "",
                horario=(f"{inicio} às {fim}" if inicio and fim else "") + (f" ({horas}h por dia)" if horas else ""),
                escolaridade=espacos(item.get("nivel_ensino") or ""),
                beneficios=espacos(item.get("beneficios")),
            )
        )
    return vagas, int((corpo.get("paginacao") or {}).get("totalPaginas") or 0)


class Isbet(Fonte):
    nome = "isbet"
    titulo = "Isbet"
    site = SITE
    tipos = frozenset(PROGRAMAS)
    abrir_anuncios = False

    def __init__(self) -> None:
        # Uma leitura do estado por execução (cada execução tem seu próprio Cliente), compartilhada entre cidades.
        self._estados: weakref.WeakKeyDictionary[Cliente, dict[tuple[str, str], asyncio.Task]] = (
            weakref.WeakKeyDictionary()
        )

    async def _ler_estado(self, cliente: Cliente, uf: str, programa: str) -> list[Vaga]:
        vagas: list[Vaga] = []
        for pagina in range(1, MAX_PAGINAS_ESTADO + 1):
            consulta = {"action": "buscar_vagas_campos_api", "uf": uf, "programa": programa, "paginaatual": pagina}
            lidas, total = interpretar((await cliente.get(f"{SITE}/wp-admin/admin-ajax.php?{urlencode(consulta)}")).json())
            vagas.extend(lidas)
            if not lidas or pagina >= total:
                break
        return vagas

    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int, tipo: str = APRENDIZ) -> list[Vaga]:
        tarefas = self._estados.setdefault(cliente, {})
        chave = (cidade.uf, PROGRAMAS[tipo])
        if chave not in tarefas:
            tarefas[chave] = asyncio.ensure_future(self._ler_estado(cliente, *chave))
        return [v for v in await tarefas[chave] if cidade.eh(v.cidade)]
