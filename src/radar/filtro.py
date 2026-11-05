"""Regras que decidem se uma vaga é de aprendiz e se ela atende ao filtro de região."""

from __future__ import annotations

import re
from enum import Enum

from .modelos import Vaga
from .regioes import FiltroRegiao
from .texto import normalizar

# "aprendiz" como palavra inteira (não pega "aprendizado").
_APRENDIZ_TITULO = re.compile(r"\baprendiz(es)?\b")
_ESTAGIO = re.compile(r"\bestagi(o|ario|aria|arios|arias)\b")
_APRENDIZ_DESCRICAO = re.compile(
    r"\b(jovem aprendiz|menor aprendiz|pessoa aprendiz|programa (de )?aprendiz(agem)?|"
    r"contrato de aprendizagem|lei (no? )?10 ?097|aprendiz legal)\b"
)


def eh_aprendiz(vaga: Vaga) -> bool:
    titulo = normalizar(vaga.titulo)
    if _APRENDIZ_TITULO.search(titulo):
        return True
    # Estágio é outro tipo de contrato, mesmo quando o site classifica junto com aprendiz.
    if _ESTAGIO.search(titulo):
        return False
    if vaga.eh_aprendiz_na_fonte:
        return True
    return bool(_APRENDIZ_DESCRICAO.search(normalizar(vaga.descricao)))


class Encaixe(Enum):
    SIM = "sim"  # local confirmado dentro do filtro
    TALVEZ = "talvez"  # anúncio não diz o bairro/distrito
    NAO = "nao"  # local confirmado fora do filtro


def encaixe(vaga: Vaga, filtro: FiltroRegiao) -> Encaixe:
    if filtro.vazio:
        return Encaixe.SIM
    if filtro.bairros:
        nomes = {b.nome for b in filtro.bairros}
        distritos_dos_bairros = {b.distrito for b in filtro.bairros}
        if vaga.bairro:
            if vaga.bairro in nomes:
                return Encaixe.SIM
            # Bairro fora da lista, mas o filtro também pede o distrito inteiro.
            if vaga.distrito in filtro.distritos:
                return Encaixe.SIM
            return Encaixe.NAO
        if vaga.distrito is not None:
            if vaga.distrito in filtro.distritos:
                return Encaixe.SIM
            return Encaixe.TALVEZ if vaga.distrito in distritos_dos_bairros else Encaixe.NAO
        return Encaixe.TALVEZ
    if vaga.distrito is not None:
        return Encaixe.SIM if vaga.distrito in filtro.distritos else Encaixe.NAO
    return Encaixe.TALVEZ
