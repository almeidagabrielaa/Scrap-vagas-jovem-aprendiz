"""Extrai dados da página de detalhe da vaga a partir do JSON-LD (schema.org/JobPosting).

Todas as fontes usadas publicam esse bloco, que traz descrição completa e endereço com CEP.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass

from .texto import espacos, extrair_cep, limpar_html, normalizar

_LD_JSON = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S | re.I)


@dataclass
class Detalhe:
    descricao: str = ""
    endereco: str = ""
    cidade: str = ""
    cep: str | None = None


def _carregar(bruto: str):
    for texto in (bruto, html.unescape(bruto)):
        try:
            return json.loads(texto, strict=False)
        except json.JSONDecodeError:
            continue
    return None


def _job_postings(dados) -> list[dict]:
    if isinstance(dados, list):
        return [j for d in dados for j in _job_postings(d)]
    if not isinstance(dados, dict):
        return []
    if "@graph" in dados:
        return _job_postings(dados["@graph"])
    tipo = dados.get("@type")
    tipos = tipo if isinstance(tipo, list) else [tipo]
    return [dados] if "JobPosting" in tipos else []


def _sem_rua(rua: str, *partes: str) -> bool:
    """True se o "endereço" só repete cidade/UF/país/CEP, ex.: "RJ, Cabo Frio, 28905000".

    Alguns sites preenchem assim todas as vagas da cidade, com um CEP genérico que não indica o bairro.
    """
    resto = normalizar(_CEP_TEXTO.sub(" ", rua))
    for p in (*partes, "brasil", "br"):
        if p:
            resto = re.sub(rf"\b{re.escape(normalizar(p))}\b", " ", resto)
    return not resto.strip()


_CEP_TEXTO = re.compile(r"\d{5}-?\d{3}")


def extrair(pagina_html: str) -> Detalhe | None:
    for m in _LD_JSON.finditer(pagina_html):
        dados = _carregar(m.group(1).strip())
        for job in _job_postings(dados):
            detalhe = Detalhe(descricao=limpar_html(job.get("description")))
            locais = job.get("jobLocation") or []
            if isinstance(locais, dict):
                locais = [locais]
            for local in locais:
                endereco = (local or {}).get("address") or {}
                if isinstance(endereco, str):
                    detalhe.endereco = espacos(endereco)
                    detalhe.cep = extrair_cep(endereco)
                    break
                rua = espacos(endereco.get("streetAddress"))
                cep = espacos(str(endereco.get("postalCode") or ""))
                detalhe.cidade = espacos(endereco.get("addressLocality"))
                partes = (detalhe.cidade, str(endereco.get("addressRegion") or ""), str(endereco.get("addressCountry") or ""))
                if rua and _sem_rua(rua, *partes):
                    break  # endereço genérico: nem rua nem CEP servem para achar o bairro
                detalhe.endereco = rua
                detalhe.cep = extrair_cep(cep) or extrair_cep(rua)
                break
            return detalhe
    return None
