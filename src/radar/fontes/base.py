from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import date, datetime

from ..http import Cliente
from ..modelos import Vaga
from ..regioes import Cidade
from ..texto import espacos

ESTADOS = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}


class Fonte(ABC):
    nome: str  # identificador usado na linha de comando
    titulo: str  # nome exibido
    site: str

    @abstractmethod
    async def buscar(self, cliente: Cliente, cidade: Cidade, max_paginas: int) -> list[Vaga]:
        """Devolve as vagas de aprendiz que o site lista para a cidade."""

    #: True se a fonte sabe listar vagas remotas (home office) de todo o Brasil.
    tem_remotas: bool = False

    async def buscar_remotas(self, cliente: Cliente, max_paginas: int) -> list[Vaga]:
        """Vagas de aprendiz 100% remotas, de qualquer lugar. Só retorna as que o site marca como remotas."""
        return []


def separar_local(texto: str) -> tuple[str, str]:
    """ "Cabo Frio / RJ", "Cabo Frio - RJ", "Cabo Frio/RJ" -> ("Cabo Frio", "RJ")."""
    texto = espacos(texto)
    m = re.match(r"^(.*?)\s*[/\-–]\s*([A-Za-z]{2})\b", texto)
    if m:
        return m.group(1).strip(" -"), m.group(2).upper()
    return texto.strip(" -"), ""


def data_br(texto: str, hoje: date | None = None) -> date | None:
    """Lê "05/10/2026" ou "05/10" (assume o ano corrente ou o anterior)."""
    hoje = hoje or date.today()
    m = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", texto or "")
    if not m:
        return None
    dia, mes = int(m.group(1)), int(m.group(2))
    ano = int(m.group(3)) if m.group(3) else hoje.year
    if ano < 100:
        ano += 2000
    try:
        d = date(ano, mes, dia)
    except ValueError:
        return None
    if not m.group(3) and d > hoje:
        d = d.replace(year=ano - 1)
    return d


def data_iso(texto: str | None) -> date | None:
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00").replace("/", "-")).date()
    except ValueError:
        return None
