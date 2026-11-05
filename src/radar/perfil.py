"""Idade e escolaridade: o que o anúncio exige e se a pessoa que procura se encaixa.

O radar lê a faixa de idade ("14 a 24 anos", "maior de 18") e a escolaridade ("cursando o ensino médio",
"ensino médio completo") no texto da vaga. Quando a pessoa informa a idade e/ou a escolaridade, as vagas que
pedem claramente outra coisa são escondidas. Vaga que não diz nada continua aparecendo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .modelos import Vaga
from .texto import normalizar, para_busca

# ----------------------------------------------------------------- idade

_FAIXA = re.compile(r"\b(?:de|entre|dos|idade:?|faixa etaria:?)?\s*(1[4-9]|2[0-9])\s*(?:a|e|ate|-)\s*(1[4-9]|2[0-9])\s*anos\b")
_MINIMA = re.compile(r"\b(?:maior(?:es)? de|acima de|a partir (?:de|dos)|minimo de|idade minima:?|ter no minimo)\s*(1[4-9]|2[0-9])\s*anos\b")
_MAXIMA = re.compile(r"\b(?:ate|no maximo|menor(?:es)? de|idade maxima:?)\s*(1[4-9]|2[0-9])\s*anos\b")


def faixa_de_idade(vaga: Vaga) -> tuple[int | None, int | None]:
    """(mínima, máxima) que o anúncio pede; None onde ele não diz."""
    texto = normalizar(f"{vaga.titulo} {vaga.descricao}")
    if m := _FAIXA.search(texto):
        a, b = sorted((int(m.group(1)), int(m.group(2))))
        return a, b
    minima = int(m.group(1)) if (m := _MINIMA.search(texto)) else None
    maxima = int(m.group(1)) if (m := _MAXIMA.search(texto)) else None
    if m := re.search(r"\bmenor(?:es)? de (1[4-9]|2[0-9]) anos\b", texto):
        maxima = int(m.group(1)) - 1  # "menores de 22 anos" = até 21
    return minima, maxima


# ----------------------------------------------------------- escolaridade

FUNDAMENTAL, MEDIO, TECNICO, SUPERIOR = 1, 2, 3, 4
_NIVEIS = (
    (r"ensino superior|graduacao|faculdade|universitari[oa]", SUPERIOR),
    # "suporte técnico" e "técnico de manutenção" são cargos, não escolaridade: precisa ser curso/ensino técnico.
    (r"(curso|ensino|nivel) tecnico|tecnico em [a-z]+", TECNICO),
    (r"ensino medio|2o grau|segundo grau", MEDIO),
    (r"ensino fundamental|1o grau|primeiro grau", FUNDAMENTAL),
)

#: O que a pessoa informa no formulário: (nível, ainda está cursando?).
ESCOLARIDADES = {
    "fundamental": ("Cursando o ensino fundamental", (FUNDAMENTAL, True)),
    "medio_cursando": ("Cursando o ensino médio", (MEDIO, True)),
    "medio_completo": ("Terminei o ensino médio", (MEDIO, False)),
    "tecnico_cursando": ("Cursando técnico", (TECNICO, True)),
    "superior_cursando": ("Cursando faculdade", (SUPERIOR, True)),
}


@dataclass(frozen=True)
class Exigencia:
    nivel: int
    modo: str  # "cursando" (precisa estar matriculado), "completo" (precisa ter terminado) ou "minimo" (qualquer um)


def _nivel(trecho: str) -> int | None:
    return next((n for padrao, n in _NIVEIS if re.search(rf"\b({padrao})\b", trecho)), None)


def exigencia_escolar(vaga: Vaga) -> Exigencia | None:
    # Mantém a pontuação: cada exigência é lida só dentro da própria frase/item.
    texto = para_busca(f"{vaga.escolaridade}. {vaga.titulo}. {vaga.descricao}")
    # "cursando ou concluído o ensino médio": qualquer um dos dois serve.
    if m := re.search(r"\b(?:cursando|matriculad[oa]s?(?: no| em)?)\s+(?:ou\s+(?:ter\s+)?(?:concluido|completo)\s+)?(?:o\s+)?([a-z0-9 ]{3,40})", texto):
        nivel = _nivel(m.group(1))
        if nivel:
            return Exigencia(nivel, "minimo" if " ou " in m.group(0) else "cursando")
    # "estudantes de técnico em...", "alunos do ensino médio": também pede matrícula.
    if m := re.search(r"\b(?:estudantes?|alunos?|alunas?)\s+(?:de|do|da|dos|das|em|no|na)\s+([a-z0-9 ]{3,40})", texto):
        nivel = _nivel(m.group(1))
        if nivel:
            return Exigencia(nivel, "cursando")
    # "ensino médio completo/cursando", "completo ou em andamento": também aceita quem ainda está cursando.
    if m := re.search(
        r"\b([a-z0-9 ]{3,30}?)\s+(?:completo|concluido)\b(\s*(?:/|ou|e/ou)\s*(?:cursando|em andamento|incompleto))?", texto
    ):
        nivel = _nivel(m.group(1))
        if nivel:
            return Exigencia(nivel, "minimo" if m.group(2) else "completo")
    if vaga.escolaridade:
        nivel = _nivel(normalizar(vaga.escolaridade))
        if nivel:
            # Estágio só existe com matrícula (Lei 11.788); nas outras, a fonte informa o nível mínimo.
            return Exigencia(nivel, "cursando" if vaga.tipo == "estagio" or vaga.estagio_na_fonte else "minimo")
    return None


def escolaridade_combina(exigencia: Exigencia | None, pessoa: tuple[int, bool]) -> bool:
    if exigencia is None:
        return True
    nivel, cursando = pessoa
    concluido = nivel - 1 if cursando else nivel  # último nível que a pessoa já terminou
    if exigencia.modo == "cursando":
        return cursando and nivel == exigencia.nivel
    if exigencia.modo == "completo":
        return concluido >= exigencia.nivel
    return nivel >= exigencia.nivel


def idade_combina(vaga: Vaga, idade: int) -> bool:
    minima, maxima = faixa_de_idade(vaga)
    return (minima is None or idade >= minima) and (maxima is None or idade <= maxima)


# ----------------------------------------------------------------- turno

MANHA, TARDE, NOITE = "manha", "tarde", "noite"
TURNOS = {MANHA: "Manhã", TARDE: "Tarde", NOITE: "Noite"}
_LIMITES = {MANHA: (6 * 60, 12 * 60), TARDE: (12 * 60, 18 * 60), NOITE: (18 * 60, 23 * 60 + 59)}
SOBREPOSICAO_MINIMA = 30  # minutos dentro do turno para contar que a vaga ocupa aquele turno

_HORA = r"(\d{1,2})(?:[:h.](\d{2}))?\s*h?(?:rs?|oras)?"
_INTERVALO = re.compile(rf"\b(?:das?\s+)?{_HORA}\s*(?:as|a|ate|-)\s*{_HORA}\b")
_TURNO_PALAVRA = re.compile(
    r"\b(?:turno|periodo|horario|expediente)\s+(?:da |de |do )?(manha|tarde|noite|matutino|vespertino|noturno)\b"
)
_PALAVRAS = {"manha": MANHA, "matutino": MANHA, "tarde": TARDE, "vespertino": TARDE, "noite": NOITE, "noturno": NOITE}


def _intervalo_em_turnos(inicio: int, fim: int) -> set[str]:
    if fim <= inicio:  # vira a madrugada: não é jornada de estudante, mas conta como noite
        return {NOITE}
    return {t for t, (a, b) in _LIMITES.items() if min(fim, b) - max(inicio, a) >= SOBREPOSICAO_MINIMA}


def turnos_da_vaga(vaga: Vaga) -> set[str]:
    """Turnos que a jornada ocupa, pelo horário informado ou pelo texto. Vazio quando o anúncio não diz."""
    turnos: set[str] = set()
    for texto in (vaga.horario, vaga.descricao, vaga.titulo):
        t = para_busca(texto)  # mantém ":" de "08:00"
        for m in _INTERVALO.finditer(t):
            h1, m1, h2, m2 = (int(x) if x else 0 for x in m.groups())
            if h1 > 23 or h2 > 23 or m1 > 59 or m2 > 59 or (h1 == h2 and m1 == m2):
                continue
            turnos |= _intervalo_em_turnos(h1 * 60 + m1, h2 * 60 + m2)
        turnos |= {_PALAVRAS[p] for p in _TURNO_PALAVRA.findall(t)}
        if turnos:
            return turnos  # o horário estruturado (primeiro da lista) vale mais que o texto livre
    return turnos


def turno_combina(vaga: Vaga, turno_da_escola: str) -> bool:
    return turno_da_escola not in turnos_da_vaga(vaga)


def combina(vaga: Vaga, idade: int | None, escolaridade: str | None, turno_da_escola: str | None = None) -> bool:
    if idade is not None and not idade_combina(vaga, idade):
        return False
    if escolaridade and not escolaridade_combina(exigencia_escolar(vaga), ESCOLARIDADES[escolaridade][1]):
        return False
    if turno_da_escola and not turno_combina(vaga, turno_da_escola):
        return False
    return True
