"""Links para abrir manualmente sites que não permitem busca automática.

O robots.txt do LinkedIn proíbe robôs na listagem de vagas, então o radar não lê o LinkedIn: só monta o link
da mesma busca para a pessoa abrir no navegador.
"""

from __future__ import annotations

from urllib.parse import urlencode

from .fontes.base import ESTADOS
from .regioes import Cidade

_BRASIL_LINKEDIN = "106057199"  # geoId do Brasil no LinkedIn


def linkedin(cidade: Cidade, raio_km: int = 40) -> str:
    estado = ESTADOS.get(cidade.uf, cidade.uf)
    milhas = max(5, round(raio_km / 1.609))  # o LinkedIn usa milhas
    consulta = {"keywords": "jovem aprendiz", "location": f"{cidade.nome}, {estado}, Brasil", "distance": milhas}
    return "https://www.linkedin.com/jobs/search/?" + urlencode(consulta)


def linkedin_remotas() -> str:
    consulta = {"keywords": "jovem aprendiz", "geoId": _BRASIL_LINKEDIN, "f_WT": "2"}
    return "https://www.linkedin.com/jobs/search/?" + urlencode(consulta)
