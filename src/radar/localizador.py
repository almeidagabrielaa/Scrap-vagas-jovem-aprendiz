"""Descobre bairro e distrito de uma vaga a partir do texto do anúncio ou do CEP."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .modelos import Vaga
from .regioes import Bairro, Cidade
from .texto import normalizar, para_busca

_SEP = r"[,/\-–—|]"
_FIM = r"(?![a-z0-9])"
_INICIO = r"(?<![a-z0-9])"


def _termo(nome: str) -> str:
    return re.escape(para_busca(nome)).replace(r"\ ", r"\s+")


@dataclass
class Local:
    bairro: Bairro | None
    distrito: int | None
    evidencia: str


class Localizador:
    def __init__(self, cidade: Cidade):
        self.cidade = cidade
        cid = _termo(cidade.nome)
        # (padrão, só vale em campo de endereço?, bairro). O grupo "b" marca o nome do bairro.
        self._bairros: list[tuple[re.Pattern, bool, Bairro]] = []
        for bairro in cidade.bairros:
            for nome in bairro.nomes:
                b = f"(?P<b>{_termo(nome)})"
                if not bairro.ambiguo:
                    self._bairros.append((re.compile(f"{_INICIO}{b}{_FIM}"), False, bairro))
                    continue
                # Nome comum ("Centro", "Passagem"): exige contexto que indique bairro.
                contextos = (
                    rf"bairros?\s*(?:d[aoe]s?\s+)?:?\s*{b}{_FIM}",  # "bairro Centro"
                    rf"{_INICIO}{b}\s*{_SEP}\s*{cid}",  # "Centro, Cabo Frio"
                    rf"{_INICIO}{b}\s+de\s+{cid}",  # "Centro de Cabo Frio"
                    rf"{cid}\s*(?:{_SEP}|\()\s*{b}{_FIM}(?!\s+d[aeo]s?\s)",  # "Cabo Frio - Centro", "Cabo Frio (Centro)"
                )
                for p in contextos:
                    self._bairros.append((re.compile(p), False, bairro))
                # Em campo de endereço, "Rua X, 10 - Centro" já basta.
                self._bairros.append((re.compile(rf"{_SEP}\s*{b}{_FIM}"), True, bairro))

        self._distritos: list[tuple[re.Pattern, int]] = []
        for num, d in cidade.distritos.items():
            for apelido in d.apelidos:
                self._distritos.append((re.compile(f"{_INICIO}{_termo(apelido)}{_FIM}"), num))

    # ------------------------------------------------------------------ texto

    def bairro_no_texto(self, texto: str, eh_endereco: bool = False) -> Bairro | None:
        """Bairro citado no texto. Se houver vários, vence o mais longo e depois o primeiro."""
        alvo = para_busca(texto)
        if not alvo:
            return None
        achados: list[tuple[int, int, Bairro]] = []
        for padrao, so_endereco, bairro in self._bairros:
            if so_endereco and not eh_endereco:
                continue
            for m in padrao.finditer(alvo):
                achados.append((m.start("b"), m.end("b"), bairro))
        if not achados:
            return None
        # Descarta trechos contidos em outro maior ("Peró" dentro de "Jardim Peró").
        validos = [
            a
            for a in achados
            if not any(o is not a and o[0] <= a[0] and a[1] <= o[1] and (o[1] - o[0]) > (a[1] - a[0]) for o in achados)
        ]
        validos.sort(key=lambda a: (a[0], -(a[1] - a[0])))
        return validos[0][2]

    def distrito_no_texto(self, texto: str) -> int | None:
        alvo = para_busca(texto)
        melhor: tuple[int, int] | None = None
        for padrao, num in self._distritos:
            m = padrao.search(alvo)
            if m and (melhor is None or m.start() < melhor[0]):
                melhor = (m.start(), num)
        return melhor[1] if melhor else None

    def localizar(self, vaga: Vaga) -> Local | None:
        fontes = [
            ("endereço", vaga.endereco, True),
            ("título", vaga.titulo, False),
            ("descrição", vaga.descricao, False),
        ]
        for nome, texto, eh_endereco in fontes:
            if texto:
                bairro = self.bairro_no_texto(texto, eh_endereco=eh_endereco)
                if bairro:
                    return Local(bairro, bairro.distrito, nome)
        for nome, texto, _ in fontes:
            if texto:
                num = self.distrito_no_texto(texto)
                if num:
                    return Local(None, num, nome)
        return None

    # ------------------------------------------------------------------ CEP

    def de_correios(self, bairro_correios: str) -> Local | None:
        """Interpreta o bairro devolvido pelo ViaCEP, ex.: "Unamar (Tamoios)"."""
        if not bairro_correios:
            return None
        m = re.match(r"^(.*?)\s*(?:\((.*)\))?\s*$", bairro_correios)
        nome, extra = (m.group(1), m.group(2)) if m else (bairro_correios, None)
        bairro = self.cidade.bairro(nome) or self.cidade.bairro(bairro_correios)
        if bairro:
            return Local(bairro, bairro.distrito, "CEP")
        if extra:
            num = self.distrito_no_texto(extra)
            if num:
                return Local(None, num, "CEP")
        return None


def aplicar(vaga: Vaga, local: Local | None) -> None:
    if not local:
        return
    vaga.bairro = local.bairro.nome if local.bairro else None
    vaga.distrito = local.distrito
    vaga.evidencia_local = local.evidencia


def mesma_cidade(nome_a: str, nome_b: str) -> bool:
    return bool(nome_a) and normalizar(nome_a) == normalizar(nome_b)
