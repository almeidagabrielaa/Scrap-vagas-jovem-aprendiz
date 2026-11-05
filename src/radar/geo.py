"""Coordenadas e distâncias.

As coordenadas dos bairros ficam no regioes.yaml. Endereços (do anúncio ou o informado em --perto-de)
são convertidos pelo Nominatim (OpenStreetMap), com cache no histórico: no máximo 1 consulta por segundo,
como pede a política de uso do serviço.
"""

from __future__ import annotations

import math
import re

from .historico import Historico
from .http import Cliente
from .regioes import Cidade
from .texto import normalizar

Coordenadas = tuple[float, float]

NOMINATIM = "https://nominatim.openstreetmap.org/search"


def distancia_km(a: Coordenadas, b: Coordenadas) -> float:
    """Distância em linha reta (fórmula de haversine)."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def formatar_km(km: float) -> str:
    if km < 1:
        return f"{round(km * 1000, -2):.0f} m"
    return f"{km:.1f} km".replace(".", ",")


class Geocodificador:
    def __init__(self, cliente: Cliente, historico: Historico, cidade: Cidade):
        self.cliente = cliente
        self.historico = historico
        self.cidade = cidade

    def do_bairro(self, nome: str | None) -> Coordenadas | None:
        bairro = self.cidade.bairro(nome) if nome else None
        return bairro.coordenadas if bairro else None

    async def endereco(self, texto: str) -> Coordenadas | None:
        """Converte um endereço da cidade em coordenadas. Devolve None se não achar ou se cair em outra cidade."""
        texto = re.sub(r"\b\d{5}-?\d{3}\b", " ", texto)  # CEP atrapalha a busca
        consulta = f"{texto}, {self.cidade.nome}, {self.cidade.uf}, Brasil"
        chave = normalizar(consulta)
        if self.historico.tem_geocodigo(chave):
            return self.historico.geocodigo(chave)
        try:
            resposta = await self.cliente.get(
                NOMINATIM,
                params={"q": consulta, "format": "jsonv2", "limit": 1, "countrycodes": "br"},
                tentativas=2,
                respeitar_robots=False,  # API pública com política de uso própria
            )
            dados = resposta.json()
        except Exception:
            return None  # não grava: tenta de novo na próxima execução
        coords = None
        if dados and normalizar(self.cidade.nome) in normalizar(dados[0].get("display_name", "")):
            coords = (float(dados[0]["lat"]), float(dados[0]["lon"]))
        self.historico.salvar_geocodigo(chave, coords)
        return coords

    async def referencia(self, texto: str) -> tuple[str, Coordenadas] | None:
        """Interpreta o --perto-de: nome de bairro cadastrado ou um endereço."""
        bairro = self.cidade.bairro(texto)
        if bairro and bairro.coordenadas:
            return bairro.nome, bairro.coordenadas
        coords = await self.endereco(texto)
        return (texto, coords) if coords else None
