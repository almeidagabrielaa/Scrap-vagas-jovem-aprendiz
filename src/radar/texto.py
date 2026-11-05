"""Funções de normalização de texto usadas em todo o projeto."""

from __future__ import annotations

import html
import re
import unicodedata

from bs4 import BeautifulSoup


def sem_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos e só letras/números separados por um espaço."""
    texto = sem_acentos(texto or "").lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return texto.strip()


def para_busca(texto: str) -> str:
    """Minúsculas e sem acentos, mas mantendo a pontuação (útil para regex com contexto)."""
    texto = sem_acentos(texto or "").lower()
    return re.sub(r"\s+", " ", texto)


def slug(texto: str) -> str:
    return normalizar(texto).replace(" ", "-")


def limpar_html(texto: str | None) -> str:
    """Converte HTML (ou texto com entidades) em texto corrido."""
    if not texto:
        return ""
    if "<" in texto:
        texto = BeautifulSoup(texto, "html.parser").get_text(" ")
    texto = html.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


def espacos(texto: str | None) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


_CEP = re.compile(r"\b(\d{5})-?(\d{3})\b")


def extrair_cep(texto: str | None) -> str | None:
    if not texto:
        return None
    m = _CEP.search(texto)
    return f"{m.group(1)}{m.group(2)}" if m else None
