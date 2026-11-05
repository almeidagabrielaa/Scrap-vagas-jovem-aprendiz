"""Orquestra uma execução: busca nas fontes, completa detalhes, localiza, deduplica e filtra."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable

import httpx

from . import detalhes as det
from . import oferta, perfil
from .filtro import (
    APRENDIZ,
    TIPOS,
    Encaixe,
    aceita_sem_experiencia,
    classificar,
    descrever_tipos,
    encaixe,
    perfil_avancado,
)
from .fontes import Fonte
from .geo import Coordenadas, Geocodificador, distancia_km
from .historico import Historico
from .http import BloqueadoPeloRobots, Cliente
from .localizador import Localizador, aplicar, mesma_cidade
from .modelos import Vaga
from .regioes import Cidade, FiltroRegiao
from .texto import normalizar

Aviso = Callable[[str], None]


class ReferenciaNaoEncontrada(ValueError):
    pass


class BuscaInvalida(ValueError):
    """Tipo de vaga desconhecido ou nenhuma fonte escolhida sabe buscar os tipos pedidos."""


# Distância máxima aceita entre o endereço geocodificado e o centro do bairro da vaga.
LIMITE_ENDERECO_KM = 4.0

# Anúncios mais antigos que isso quase sempre já foram preenchidos (alguns sites não tiram do ar).
IDADE_MAXIMA_DIAS = 180


@dataclass
class Resultado:
    filtro: FiltroRegiao
    tipos: list[str] = field(default_factory=lambda: [APRENDIZ])  # tipos de vaga procurados
    confirmadas: list[Vaga] = field(default_factory=list)  # local dentro do filtro
    sem_local: list[Vaga] = field(default_factory=list)  # anúncio não diz bairro/distrito
    vizinhas: list[Vaga] = field(default_factory=list)  # vagas das cidades vizinhas (se pedido)
    remotas: list[Vaga] = field(default_factory=list)  # home office, todo o Brasil (se pedido)
    cidades_vizinhas: list[Cidade] = field(default_factory=list)  # vizinhas consultadas
    fora_do_filtro: int = 0
    antigas: int = 0  # anúncios publicados há mais de IDADE_MAXIMA_DIAS
    perfil_avancado: int = 0  # não aprendiz que pedem faculdade, liderança ou experiência (ocultas)
    fora_do_raio: int = 0
    fora_do_perfil: int = 0  # pedem outra idade/escolaridade ou batem com o turno da escola
    ocultas_sem_local: int = 0
    por_fonte: dict[str, int] = field(default_factory=dict)
    erros: dict[str, str] = field(default_factory=dict)
    referencia: tuple[str, Coordenadas] | None = None  # (nome, coordenadas) do --perto-de
    executado_em: datetime = field(default_factory=datetime.now)


def _descrever_erro(erro: Exception) -> str:
    if isinstance(erro, httpx.HTTPStatusError):
        codigo = erro.response.status_code
        if codigo in (401, 403):
            return f"o site recusou o acesso (HTTP {codigo}); provavelmente bloqueia robôs"
        return f"o site respondeu com erro HTTP {codigo}"
    if isinstance(erro, httpx.TimeoutException):
        return "o site demorou demais para responder"
    if isinstance(erro, httpx.TransportError):
        return f"falha de conexão ({erro.__class__.__name__})"
    if isinstance(erro, BloqueadoPeloRobots):
        return str(erro)
    return f"{erro.__class__.__name__}: {erro}"


async def _buscar_fontes(
    cliente: Cliente,
    fontes: list[Fonte],
    cidades: list[Cidade],
    tipos: list[str],
    remotas: bool,
    max_paginas: int,
    resultado: Resultado,
    aviso: Aviso,
) -> list[Vaga]:
    """Cada fonte percorre tipos e cidades em sequência (respeitando a pausa por site); as fontes rodam em paralelo."""

    async def uma(fonte: Fonte) -> list[Vaga]:
        achadas: list[Vaga] = []
        falhas: list[str] = []
        meus_tipos = [t for t in tipos if t in fonte.tipos]
        rotulo = (lambda t: f"{TIPOS[t].lower()}, ") if len(meus_tipos) > 1 else (lambda t: "")
        for tipo in meus_tipos:
            for cidade in cidades:
                try:
                    vagas = await fonte.buscar(cliente, cidade, max_paginas, tipo)
                except Exception as e:  # uma fonte quebrada não derruba as outras
                    falhas.append(f"{rotulo(tipo)}{cidade.nome}: {_descrever_erro(e)}")
                    continue
                for v in vagas:
                    if cidade.eh(v.cidade) and v.uf.upper() in ("", cidade.uf):
                        v.regiao = cidade.nome
                        achadas.append(v)
            if remotas and fonte.tem_remotas:
                try:
                    for v in await fonte.buscar_remotas(cliente, max_paginas, tipo):
                        v.regiao = ""
                        achadas.append(v)
                except Exception as e:
                    falhas.append(f"{rotulo(tipo)}remotas: {_descrever_erro(e)}")
        if falhas:
            resultado.erros[fonte.titulo] = "; ".join(falhas)
            aviso(f"[yellow]{fonte.titulo}[/]: {resultado.erros[fonte.titulo]}")
        resultado.por_fonte[fonte.titulo] = len(achadas)
        detalhe = f"{len(achadas)} vaga(s)"
        if len(cidades) > 1 or remotas:
            na_principal = sum(v.regiao == cidades[0].nome for v in achadas)
            detalhe += f" ({na_principal} em {cidades[0].nome})"
        else:
            detalhe += f" em {cidades[0].nome}"
        aviso(f"{fonte.titulo}: {detalhe}")
        return achadas

    listas = await asyncio.gather(*(uma(f) for f in fontes))
    # A mesma vaga pode vir em duas buscas do mesmo site (ex.: lista da cidade e lista de remotas,
    # ou a busca de aprendiz e a de meio período). Fica a primeira, somando o que cada busca sabia.
    unicas: dict[str, Vaga] = {}
    for v in (v for lista in listas for v in lista):
        primeira = unicas.setdefault(v.chave, v)
        if primeira is not v:
            primeira.meio_periodo_na_fonte |= v.meio_periodo_na_fonte
            primeira.eh_aprendiz_na_fonte |= v.eh_aprendiz_na_fonte
            primeira.regiao = primeira.regiao or v.regiao
    return list(unicas.values())


async def _completar_detalhes(cliente: Cliente, vagas: list[Vaga], aviso: Aviso) -> None:
    async def um(vaga: Vaga) -> None:
        try:
            resposta = await cliente.get(vaga.url, tentativas=2)
        except Exception:
            return  # segue com os dados da listagem
        d = det.extrair(resposta.text)
        if not d:
            return
        if len(d.descricao) > len(vaga.descricao):
            vaga.descricao = d.descricao
        vaga.endereco = d.endereco or vaga.endereco
        vaga.cep = d.cep or vaga.cep

    aviso(f"Abrindo {len(vagas)} anúncio(s) para ler descrição e endereço...")
    await asyncio.gather(*(um(v) for v in vagas))


async def _consultar_cep(cliente: Cliente, historico: Historico, cep: str) -> tuple[str, str, str] | None:
    salvo = historico.cep(cep)
    if salvo:
        return salvo if salvo[0] else None
    try:
        resposta = await cliente.get(f"https://viacep.com.br/ws/{cep}/json/", tentativas=2, respeitar_robots=False)
        dados = resposta.json()
    except Exception:
        return None  # não grava: tenta de novo na próxima execução
    if dados.get("erro"):
        historico.salvar_cep(cep, "", "", "")
        return None
    linha = (dados.get("bairro") or "", dados.get("localidade") or "", dados.get("uf") or "")
    historico.salvar_cep(cep, *linha)
    return linha if linha[0] else None


async def _localizar(cliente, historico, localizador: Localizador, vagas: list[Vaga]) -> None:
    async def um(vaga: Vaga) -> None:
        local = localizador.localizar(vaga)
        if (local is None or local.bairro is None) and vaga.cep:
            dados = await _consultar_cep(cliente, historico, vaga.cep)
            if dados and mesma_cidade(dados[1], localizador.cidade.nome):
                pelo_cep = localizador.de_correios(dados[0])
                # O texto do anúncio vence o CEP; o CEP só completa quando não contradiz o texto.
                if pelo_cep and (local is None or pelo_cep.distrito == local.distrito):
                    local = pelo_cep
        aplicar(vaga, local)

    await asyncio.gather(*(um(v) for v in vagas))


def _distancias_vizinhas(ref: Coordenadas, vagas: list[Vaga], cidades: list[Cidade]) -> None:
    """Vagas de cidades vizinhas: distância até o centro da cidade da vaga."""
    centros = {c.nome: c.coordenadas for c in cidades if c.coordenadas}
    for v in vagas:
        if v.regiao in centros:
            v.distancia_km, v.distancia_por = distancia_km(ref, centros[v.regiao]), "cidade"


async def _calcular_distancias(geo: Geocodificador, ref: Coordenadas, vagas: list[Vaga]) -> None:
    async def um(vaga: Vaga) -> None:
        do_bairro = geo.do_bairro(vaga.bairro)
        coords, por = None, ""
        if vaga.endereco:
            coords, por = await geo.endereco(vaga.endereco), "endereço"
            # Ruas com nome repetido na cidade ("Avenida Central") podem cair no lugar errado:
            # se o ponto ficar longe do bairro já identificado, vale o bairro.
            if coords and do_bairro and distancia_km(coords, do_bairro) > LIMITE_ENDERECO_KM:
                coords = None
        if coords is None:
            coords, por = do_bairro, "bairro"
        if coords:
            vaga.distancia_km, vaga.distancia_por = distancia_km(ref, coords), por

    await asyncio.gather(*(um(v) for v in vagas))


def _chave_dedupe(vaga: Vaga) -> str:
    empresa = normalizar(vaga.empresa)
    if not empresa or "confidencial" in empresa:
        return vaga.chave
    return f"{normalizar(vaga.titulo)}|{empresa}"


def deduplicar(vagas: list[Vaga]) -> list[Vaga]:
    unicas: dict[str, Vaga] = {}
    for vaga in vagas:
        chave = _chave_dedupe(vaga)
        principal = unicas.get(chave)
        if principal is None:
            unicas[chave] = vaga
            continue
        principal.outras_fontes.append((vaga.fonte, vaga.id_fonte, vaga.url))
        if principal.bairro is None and vaga.bairro is not None:
            principal.bairro, principal.distrito = vaga.bairro, vaga.distrito
            principal.evidencia_local = vaga.evidencia_local
        elif principal.distrito is None and vaga.distrito is not None:
            principal.distrito, principal.evidencia_local = vaga.distrito, vaga.evidencia_local
        principal.publicada_em = principal.publicada_em or vaga.publicada_em
        principal.sem_experiencia |= vaga.sem_experiencia
        if vaga.tipo == APRENDIZ:  # um site disse aprendiz, outro só meio período: vale aprendiz
            principal.tipo = APRENDIZ
    return list(unicas.values())


def _ordem(vaga: Vaga):
    return (not vaga.nova, -(vaga.publicada_em or date.min).toordinal(), vaga.titulo.lower())


async def coletar(
    filtro: FiltroRegiao,
    fontes: list[Fonte],
    historico: Historico,
    *,
    ler_detalhes: bool = True,
    max_paginas: int = 3,
    aviso: Aviso = lambda _: None,
    perto_de: str | None = None,
    vizinhas: list[Cidade] | None = None,
    incluir_remotas: bool = False,
    tipos: list[str] | None = None,
) -> Resultado:
    """`vizinhas`: cidades buscadas junto com a principal (veja `escolher_vizinhas`).
    `tipos`: tipos de vaga procurados (chaves de `filtro.TIPOS`); o padrão é só aprendiz."""
    tipos = list(dict.fromkeys(tipos or [APRENDIZ]))
    desconhecidos = [t for t in tipos if t not in TIPOS]
    if desconhecidos:
        raise BuscaInvalida(f"Tipo(s) de vaga desconhecido(s): {', '.join(desconhecidos)}")
    # Fonte que não tem nenhum dos tipos pedidos não entra (nem aparece com "0 vagas").
    fontes = [f for f in fontes if f.tipos.intersection(tipos)]
    if not fontes:
        raise BuscaInvalida(
            f"Nenhum dos sites escolhidos tem vagas de {descrever_tipos(tipos).lower()}. Marque outros sites."
        )
    resultado = Resultado(filtro=filtro, tipos=tipos)
    principal = filtro.cidade
    if vizinhas:
        resultado.cidades_vizinhas = list(vizinhas)
        aviso("Também em: " + ", ".join(c.nome for c in vizinhas))
    async with Cliente() as cliente:
        geo = Geocodificador(cliente, historico, filtro.cidade)
        if perto_de:
            resultado.referencia = await geo.referencia(perto_de)
            if not resultado.referencia:
                raise ReferenciaNaoEncontrada(
                    f'Não encontrei "{perto_de}" em {filtro.cidade.nome}. '
                    "Informe um bairro cadastrado ou um endereço com rua (ex.: \"Rua Tal, 100, Unamar\")."
                )
            aviso(f"Ponto de referência: {resultado.referencia[0]}")

        cidades = [principal, *resultado.cidades_vizinhas]
        vagas = await _buscar_fontes(cliente, fontes, cidades, tipos, incluir_remotas, max_paginas, resultado, aviso)

        limite = date.today().toordinal() - IDADE_MAXIMA_DIAS
        recentes = [v for v in vagas if not v.publicada_em or v.publicada_em.toordinal() >= limite]
        resultado.antigas = len(vagas) - len(recentes)
        vagas = recentes

        # Só as vagas da cidade principal precisam de bairro; as outras ficam no nível da cidade.
        sem_anuncio = {f.nome for f in fontes if not f.abrir_anuncios}
        da_principal = [v for v in vagas if v.regiao == principal.nome and v.fonte not in sem_anuncio]
        if ler_detalhes and da_principal:
            await _completar_detalhes(cliente, da_principal, aviso)
        for v in vagas:
            v.tipo = classificar(v, tipos) or ""
            v.sem_experiencia = aceita_sem_experiencia(v)
            oferta.completar(v)
        vagas = [v for v in vagas if v.tipo]
        # Fora do contrato de aprendiz, sobra muita vaga para quem já tem formação ou experiência.
        de_entrada = [v for v in vagas if v.tipo == APRENDIZ or not perfil_avancado(v)]
        resultado.perfil_avancado = len(vagas) - len(de_entrada)
        vagas = de_entrada
        await _localizar(cliente, historico, Localizador(principal), [v for v in vagas if v.regiao == principal.nome])

        vagas = deduplicar(vagas)
        exibidas = []
        for vaga in vagas:
            if vaga.regiao != principal.nome:
                (resultado.vizinhas if vaga.regiao else resultado.remotas).append(vaga)
                exibidas.append(vaga)
                continue
            e = encaixe(vaga, filtro)
            if e is Encaixe.SIM:
                resultado.confirmadas.append(vaga)
            elif e is Encaixe.TALVEZ:
                resultado.sem_local.append(vaga)
            else:
                resultado.fora_do_filtro += 1
                continue
            exibidas.append(vaga)

        if resultado.referencia:
            aviso("Calculando distâncias...")
            ref = resultado.referencia[1]
            await _calcular_distancias(geo, ref, resultado.confirmadas + resultado.sem_local)
            _distancias_vizinhas(ref, resultado.vizinhas, resultado.cidades_vizinhas)

    historico.marcar_novas(exibidas)
    for lista in (resultado.confirmadas, resultado.sem_local, resultado.vizinhas, resultado.remotas):
        lista.sort(key=_ordem)
    return resultado


def pos_filtrar(
    resultado: Resultado,
    *,
    novas: bool = False,
    somente_com_bairro: bool = False,
    raio: float | None = None,
    idade: int | None = None,
    escolaridade: str | None = None,
    turno_escola: str | None = None,
) -> None:
    """Filtros aplicados depois da busca (os mesmos na linha de comando e na interface web)."""
    if idade is not None or escolaridade or turno_escola:
        listas = ("confirmadas", "sem_local", "vizinhas", "remotas")
        antes = sum(len(getattr(resultado, n)) for n in listas)
        for n in listas:
            setattr(resultado, n, [v for v in getattr(resultado, n) if perfil.combina(v, idade, escolaridade, turno_escola)])
        resultado.fora_do_perfil = antes - sum(len(getattr(resultado, n)) for n in listas)
    if somente_com_bairro:
        # Sem filtro de região, as vagas sem local ficam em "confirmadas"; por isso olha as duas listas.
        com_local = [v for v in resultado.confirmadas if v.distrito is not None]
        resultado.ocultas_sem_local = len(resultado.sem_local) + len(resultado.confirmadas) - len(com_local)
        resultado.confirmadas, resultado.sem_local = com_local, []
    if novas:
        for nome in ("confirmadas", "sem_local", "vizinhas", "remotas"):
            setattr(resultado, nome, [v for v in getattr(resultado, nome) if v.nova])
    if raio is not None:
        # Vagas sem distância conhecida continuam aparecendo, em seção própria. Remotas não têm distância.
        def dentro(v: Vaga) -> bool:
            return v.distancia_km is None or v.distancia_km <= raio

        listas = ("confirmadas", "sem_local", "vizinhas")
        antes = sum(len(getattr(resultado, n)) for n in listas)
        for n in listas:
            setattr(resultado, n, [v for v in getattr(resultado, n) if dentro(v)])
        resultado.fora_do_raio = antes - sum(len(getattr(resultado, n)) for n in listas)
