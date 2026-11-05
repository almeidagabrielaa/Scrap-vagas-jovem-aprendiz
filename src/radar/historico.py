"""Histórico em SQLite: lembra as vagas já vistas (para marcar as novas) e guarda consultas de CEP."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from .modelos import Vaga

CAMINHO_PADRAO = Path.home() / ".radar-aprendiz" / "radar.db"


class Historico:
    def __init__(self, caminho: Path = CAMINHO_PADRAO):
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self.caminho = caminho
        self._db = sqlite3.connect(caminho)
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS vistas (
                chave TEXT PRIMARY KEY,
                titulo TEXT,
                url TEXT,
                primeira_vez TEXT NOT NULL,
                ultima_vez TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS geocodigos (
                consulta TEXT PRIMARY KEY,
                lat REAL,
                lon REAL,
                consultado_em TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ceps (
                cep TEXT PRIMARY KEY,
                bairro TEXT,
                cidade TEXT,
                uf TEXT,
                consultado_em TEXT NOT NULL
            );
            """
        )

    def fechar(self) -> None:
        self._db.close()

    def __enter__(self) -> "Historico":
        return self

    def __exit__(self, *exc) -> None:
        self.fechar()

    # ------------------------------------------------------------------ vagas

    def marcar_novas(self, vagas: list[Vaga]) -> None:
        """Define `vaga.nova` e registra todas como vistas agora."""
        agora = datetime.now().isoformat(timespec="seconds")
        for vaga in vagas:
            chaves = vaga.todas_chaves
            marcadores = ",".join("?" * len(chaves))
            ja_vista = self._db.execute(
                f"SELECT 1 FROM vistas WHERE chave IN ({marcadores}) LIMIT 1", chaves
            ).fetchone()
            vaga.nova = ja_vista is None
            for chave in chaves:
                self._db.execute(
                    """
                    INSERT INTO vistas (chave, titulo, url, primeira_vez, ultima_vez)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(chave) DO UPDATE SET ultima_vez = excluded.ultima_vez
                    """,
                    (chave, vaga.titulo, vaga.url, agora, agora),
                )
        self._db.commit()

    def limpar_vagas(self) -> int:
        n = self._db.execute("DELETE FROM vistas").rowcount
        self._db.commit()
        return n

    # ------------------------------------------------------------------ CEP

    def cep(self, cep: str) -> tuple[str, str, str] | None:
        linha = self._db.execute("SELECT bairro, cidade, uf FROM ceps WHERE cep = ?", (cep,)).fetchone()
        return tuple(linha) if linha else None  # type: ignore[return-value]

    # ------------------------------------------------------------------ coordenadas

    def tem_geocodigo(self, consulta: str) -> bool:
        return self._db.execute("SELECT 1 FROM geocodigos WHERE consulta = ?", (consulta,)).fetchone() is not None

    def geocodigo(self, consulta: str) -> tuple[float, float] | None:
        linha = self._db.execute("SELECT lat, lon FROM geocodigos WHERE consulta = ?", (consulta,)).fetchone()
        return (linha[0], linha[1]) if linha and linha[0] is not None else None

    def salvar_geocodigo(self, consulta: str, coords: tuple[float, float] | None) -> None:
        lat, lon = coords if coords else (None, None)
        self._db.execute(
            "INSERT OR REPLACE INTO geocodigos (consulta, lat, lon, consultado_em) VALUES (?, ?, ?, ?)",
            (consulta, lat, lon, datetime.now().isoformat(timespec="seconds")),
        )
        self._db.commit()

    def salvar_cep(self, cep: str, bairro: str, cidade: str, uf: str) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO ceps (cep, bairro, cidade, uf, consultado_em) VALUES (?, ?, ?, ?, ?)",
            (cep, bairro, cidade, uf, datetime.now().isoformat(timespec="seconds")),
        )
        self._db.commit()
