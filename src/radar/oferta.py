"""O que a vaga oferece (salário e benefícios), lido no texto quando a fonte não informa em campo próprio."""

from __future__ import annotations

import re

from .modelos import Vaga
from .texto import para_busca

# "R$ 1.234,56", "R$1200", "R$ 900,00 por mês". Só valores plausíveis para quem está começando.
_SALARIO = re.compile(r"r\$\s*(\d{1,2}(?:\.\d{3})+|\d{3,5})(?:,(\d{2}))?(?:\s*(?:/|por|ao)\s*(mes|hora|dia))?")
SALARIO_MIN, SALARIO_MAX = 300, 6000  # por mês; fora disso costuma ser outra coisa (comissão, faturamento, multa)

BENEFICIOS = {
    "Vale transporte": r"vale[ -]?transporte|\bvt\b|auxilio[ -]transporte",
    "Vale refeição": r"vale[ -]?refeicao|\bvr\b|refeicao no local|alimentacao no local",
    "Vale alimentação": r"vale[ -]?alimentacao|\bva\b|cesta basica",
    "Plano de saúde": r"plano de saude|assistencia medica|convenio medico",
    "Plano odontológico": r"plano odontologico|assistencia odontologica|convenio odontologico",
    "Seguro de vida": r"seguro de vida",
    "Gympass/Totalpass": r"gympass|wellhub|totalpass",
}


def salario_no_texto(texto: str) -> str:
    for m in _SALARIO.finditer(para_busca(texto)):
        inteiro, centavos, periodo = m.group(1).replace(".", ""), m.group(2) or "00", m.group(3)
        valor = float(f"{inteiro}.{centavos}")
        if periodo in ("hora", "dia"):
            continue  # valor por hora/dia não é comparável sem saber a jornada
        if SALARIO_MIN <= valor <= SALARIO_MAX:
            reais = f"{int(valor):,}".replace(",", ".")
            return f"R$ {reais},{centavos}/mês"
    return ""


def beneficios_no_texto(texto: str) -> str:
    t = para_busca(texto)
    return ", ".join(nome for nome, padrao in BENEFICIOS.items() if re.search(padrao, t))


def completar(vaga: Vaga) -> None:
    """Preenche salário e benefícios a partir da descrição, sem sobrescrever o que a fonte já informou."""
    vaga.salario = vaga.salario or salario_no_texto(vaga.descricao)
    vaga.beneficios = vaga.beneficios or beneficios_no_texto(vaga.descricao)
