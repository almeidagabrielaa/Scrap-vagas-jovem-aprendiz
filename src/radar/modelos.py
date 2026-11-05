"""Estruturas de dados compartilhadas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Vaga:
    fonte: str
    id_fonte: str
    titulo: str
    url: str
    empresa: str = ""
    cidade: str = ""
    uf: str = ""
    descricao: str = ""
    endereco: str = ""
    cep: str | None = None
    publicada_em: date | None = None
    eh_aprendiz_na_fonte: bool = False  # a própria fonte classifica como aprendiz
    remota: bool = False  # a fonte marca a vaga como home office / 100% remota

    # Cidade da busca a que a vaga pertence (a principal ou uma vizinha); vazio nas remotas.
    regiao: str = ""

    # Preenchidos pelo localizador
    bairro: str | None = None
    distrito: int | None = None
    evidencia_local: str = ""  # "endereço", "título", "descrição", "CEP" ...

    # Preenchidos só quando há um ponto de referência (--perto-de)
    distancia_km: float | None = None
    distancia_por: str = ""  # "endereço" (mais preciso) ou "bairro" (centro aproximado do bairro)

    # Preenchidos depois da deduplicação / histórico
    outras_fontes: list[tuple[str, str, str]] = field(default_factory=list)  # (fonte, id, url)
    nova: bool = False

    @property
    def chave(self) -> str:
        return f"{self.fonte}:{self.id_fonte}"

    @property
    def todas_chaves(self) -> list[str]:
        return [self.chave] + [f"{f}:{i}" for f, i, _ in self.outras_fontes]
