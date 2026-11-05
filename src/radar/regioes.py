"""Carrega o arquivo de regiões (cidade -> distritos -> bairros) e resolve filtros."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import yaml

from .texto import normalizar, slug


@dataclass
class Bairro:
    nome: str
    distrito: int
    apelidos: list[str] = field(default_factory=list)
    ambiguo: bool = False
    coordenadas: tuple[float, float] | None = None  # (latitude, longitude)

    @property
    def nomes(self) -> list[str]:
        return [self.nome, *self.apelidos]


@dataclass
class Distrito:
    numero: int
    nome: str
    apelidos: list[str] = field(default_factory=list)
    bairros: list[Bairro] = field(default_factory=list)


@dataclass
class Cidade:
    chave: str
    nome: str
    uf: str
    distritos: dict[int, Distrito]
    apelidos: list[str] = field(default_factory=list)
    coordenadas: tuple[float, float] | None = None  # centro da cidade
    vizinhas: list["Cidade"] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return slug(self.nome)

    def eh(self, nome: str) -> bool:
        """O nome (como aparece num anúncio) é esta cidade? Aceita apelidos ("Búzios")."""
        alvo = normalizar(nome)
        return bool(alvo) and alvo in {normalizar(n) for n in (self.nome, *self.apelidos)}

    @property
    def bairros(self) -> list[Bairro]:
        return [b for d in self.distritos.values() for b in d.bairros]

    def bairro(self, nome: str) -> Bairro | None:
        alvo = normalizar(nome)
        for b in self.bairros:
            if any(normalizar(n) == alvo for n in b.nomes):
                return b
        return None

    def distrito(self, valor: str | int) -> Distrito | None:
        """Aceita número (1, "2") ou nome/apelido ("Tamoios", "sede")."""
        texto = str(valor).strip()
        if texto.isdigit():
            return self.distritos.get(int(texto))
        alvo = normalizar(texto)
        for d in self.distritos.values():
            if alvo in {normalizar(d.nome), *(normalizar(a) for a in d.apelidos)}:
                return d
            if alvo and alvo in normalizar(d.nome):
                return d
        return None


class RegiaoDesconhecida(ValueError):
    pass


def caminho_padrao() -> Path:
    return Path(str(resources.files("radar") / "regioes.yaml"))


def carregar(caminho: Path | None = None) -> dict[str, Cidade]:
    caminho = caminho or caminho_padrao()
    dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8")) or {}
    cidades: dict[str, Cidade] = {}
    for chave, c in dados.items():
        distritos: dict[int, Distrito] = {}
        for num, d in (c.get("distritos") or {}).items():
            num = int(num)
            bairros = [
                Bairro(
                    nome=b["nome"],
                    distrito=num,
                    apelidos=list(b.get("apelidos") or []),
                    ambiguo=bool(b.get("ambiguo", False)),
                    coordenadas=tuple(b["coordenadas"]) if b.get("coordenadas") else None,
                )
                for b in (d.get("bairros") or [])
            ]
            distritos[num] = Distrito(
                numero=num,
                nome=d.get("nome", f"{num}º Distrito"),
                apelidos=list(d.get("apelidos") or []),
                bairros=bairros,
            )
        cidades[chave] = Cidade(
            chave=chave,
            nome=c["nome"],
            uf=c["uf"],
            distritos=distritos,
            apelidos=list(c.get("apelidos") or []),
            coordenadas=tuple(c["coordenadas"]) if c.get("coordenadas") else None,
        )
    for chave, c in dados.items():
        for vizinha in c.get("vizinhas") or []:
            if vizinha not in cidades:
                raise RegiaoDesconhecida(f'"{chave}" lista a vizinha "{vizinha}", que não existe no arquivo de regiões.')
            cidades[chave].vizinhas.append(cidades[vizinha])
    return cidades


def encontrar_cidade(cidades: dict[str, Cidade], nome: str, uf: str | None = None) -> Cidade:
    """Procura a cidade no arquivo; se não existir, cria uma sem distritos (filtra só por cidade)."""
    alvo = normalizar(nome)
    for c in cidades.values():
        if (c.eh(nome) or alvo == normalizar(c.chave)) and (not uf or uf.upper() == c.uf):
            return c
    if not uf:
        raise RegiaoDesconhecida(
            f'A cidade "{nome}" não está no arquivo de regiões. '
            "Informe a UF com --uf para buscar só pela cidade, ou adicione a cidade ao regioes.yaml."
        )
    return Cidade(chave=slug(nome), nome=nome.strip().title(), uf=uf.upper(), distritos={})


@dataclass
class FiltroRegiao:
    cidade: Cidade
    distritos: set[int] = field(default_factory=set)
    bairros: list[Bairro] = field(default_factory=list)

    @property
    def vazio(self) -> bool:
        return not self.distritos and not self.bairros

    def descrever(self) -> str:
        partes = [f"{self.cidade.nome}/{self.cidade.uf}"]
        if self.distritos:
            partes.append(", ".join(self.cidade.distritos[n].nome for n in sorted(self.distritos)))
        if self.bairros:
            partes.append("bairros: " + ", ".join(b.nome for b in self.bairros))
        return " · ".join(partes)


def montar_filtro(cidade: Cidade, distritos: list[str], bairros: list[str]) -> FiltroRegiao:
    filtro = FiltroRegiao(cidade=cidade)
    for d in distritos:
        encontrado = cidade.distrito(d)
        if not encontrado:
            opcoes = ", ".join(f"{n} ({x.nome})" for n, x in cidade.distritos.items()) or "nenhum"
            raise RegiaoDesconhecida(f'Distrito "{d}" não existe em {cidade.nome}. Opções: {opcoes}.')
        filtro.distritos.add(encontrado.numero)
    for nome in bairros:
        b = cidade.bairro(nome)
        if not b:
            raise RegiaoDesconhecida(
                f'Bairro "{nome}" não está cadastrado em {cidade.nome}. '
                "Veja a lista com `radar regioes` ou adicione-o ao regioes.yaml."
            )
        filtro.bairros.append(b)
    return filtro


def escolher_vizinhas(cidade: Cidade, nomes: list[str], todas: bool = False) -> list[Cidade]:
    """Resolve as cidades vizinhas pedidas pelo nome ("Búzios", "arraial do cabo"), na ordem do arquivo."""
    if todas:
        return list(cidade.vizinhas)
    escolhidas = []
    for nome in nomes:
        achada = next((v for v in cidade.vizinhas if v.eh(nome) or normalizar(nome) == normalizar(v.chave)), None)
        if not achada:
            opcoes = ", ".join(v.nome for v in cidade.vizinhas) or "nenhuma cadastrada"
            raise RegiaoDesconhecida(f'"{nome}" não é uma cidade vizinha de {cidade.nome}. Opções: {opcoes}.')
        escolhidas.append(achada)
    return [v for v in cidade.vizinhas if any(v is e for e in escolhidas)]
