"""Links para abrir manualmente sites que não permitem busca automática.

O robots.txt do LinkedIn proíbe robôs na listagem de vagas, então o radar não lê o LinkedIn: só monta o link
da mesma busca para a pessoa abrir no navegador.
"""

from __future__ import annotations

from urllib.parse import urlencode

from .filtro import APRENDIZ, ESTAGIO, MEIO_PERIODO, PRIMEIRO_EMPREGO
from .fontes.base import ESTADOS
from .regioes import Cidade

_TERMOS = {APRENDIZ: '"jovem aprendiz"', ESTAGIO: "estágio", MEIO_PERIODO: '"meio período"', PRIMEIRO_EMPREGO: '"primeiro emprego"'}


def _palavras(tipos: list[str] | None) -> str:
    return " OR ".join(_TERMOS[t] for t in (tipos or [APRENDIZ]))

_BRASIL_LINKEDIN = "106057199"  # geoId do Brasil no LinkedIn


def linkedin(cidade: Cidade, raio_km: int = 40, tipos: list[str] | None = None) -> str:
    estado = ESTADOS.get(cidade.uf, cidade.uf)
    milhas = max(5, round(raio_km / 1.609))  # o LinkedIn usa milhas
    consulta = {"keywords": _palavras(tipos), "location": f"{cidade.nome}, {estado}, Brasil", "distance": milhas}
    return "https://www.linkedin.com/jobs/search/?" + urlencode(consulta)


def linkedin_remotas(tipos: list[str] | None = None) -> str:
    consulta = {"keywords": _palavras(tipos), "geoId": _BRASIL_LINKEDIN, "f_WT": "2"}
    return "https://www.linkedin.com/jobs/search/?" + urlencode(consulta)
