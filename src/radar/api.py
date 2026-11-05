"""API HTTP usada pela interface web (React).

- GET  /api/opcoes  -> cidades, distritos, bairros, tipos de vaga e fontes disponíveis
- POST /api/buscar  -> roda a busca. Responde em NDJSON (uma linha JSON por evento):
      {"tipo": "aviso", "mensagem": "..."}       progresso
      {"tipo": "resultado", ...}                 resultado final
      {"tipo": "erro", "mensagem": "..."}        filtro inválido ou falha
Também serve a interface já compilada (pasta web_dist), se existir.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import links, perfil
from . import regioes as reg
from .coletor import BuscaInvalida, ReferenciaNaoEncontrada, Resultado, coletar, pos_filtrar
from .filtro import APRENDIZ, TIPOS
from .fontes import TODAS
from .historico import CAMINHO_PADRAO, Historico
from .modelos import Vaga
from .saida import _fontes, descrever_distancia, descrever_local, montar_secoes

PASTA_WEB = Path(__file__).parent / "web_dist"

app = FastAPI(title="FMT - jovem aprendiz")
_uma_busca_por_vez = asyncio.Lock()


class Busca(BaseModel):
    tipos: list[str] = Field(default_factory=lambda: [APRENDIZ])  # chaves de filtro.TIPOS
    cidade: str = "Cabo Frio"
    uf: Optional[str] = None
    distritos: list[str] = Field(default_factory=list)
    bairros: list[str] = Field(default_factory=list)
    perto_de: Optional[str] = None
    raio: Optional[float] = Field(default=None, gt=0)
    novas: bool = False
    somente_com_bairro: bool = False
    fontes: list[str] = Field(default_factory=list)  # vazio = todas
    ler_detalhes: bool = True
    paginas: int = Field(default=3, ge=1, le=20)
    vizinhas: list[str] = Field(default_factory=list)  # nomes das cidades vizinhas a incluir
    incluir_remotas: bool = False
    idade: Optional[int] = Field(default=None, ge=14, le=29)
    escolaridade: Optional[str] = None  # chave de perfil.ESCOLARIDADES
    turno_escola: Optional[str] = None  # chave de perfil.TURNOS: em que turno a pessoa estuda


@app.get("/api/opcoes")
def opcoes() -> dict:
    cidades = []
    for c in reg.carregar().values():
        cidades.append(
            {
                "nome": c.nome,
                "uf": c.uf,
                "vizinhas": [v.nome for v in c.vizinhas],
                "distritos": [
                    {
                        "numero": n,
                        "nome": d.nome,
                        "bairros": [{"nome": b.nome, "temCoordenadas": b.coordenadas is not None} for b in d.bairros],
                    }
                    for n, d in c.distritos.items()
                ],
            }
        )
    return {
        "cidades": cidades,
        "turnos": [{"nome": k, "titulo": t} for k, t in perfil.TURNOS.items()],
        "escolaridades": [{"nome": k, "titulo": t} for k, (t, _) in perfil.ESCOLARIDADES.items()],
        "tipos": [
            {"nome": nome, "titulo": titulo, "fontes": [f.titulo for f in TODAS.values() if nome in f.tipos]}
            for nome, titulo in TIPOS.items()
        ],
        "fontes": [{"nome": f.nome, "titulo": f.titulo, "tipos": sorted(f.tipos)} for f in TODAS.values()],
    }


def _faixa(v: Vaga) -> str | None:
    minima, maxima = perfil.faixa_de_idade(v)
    if minima and maxima:
        return f"{minima} a {maxima} anos"
    if minima:
        return f"a partir de {minima} anos"
    return f"até {maxima} anos" if maxima else None


_NOMES_NIVEIS = {perfil.FUNDAMENTAL: "ensino fundamental", perfil.MEDIO: "ensino médio",
                 perfil.TECNICO: "curso técnico", perfil.SUPERIOR: "faculdade"}
_MODOS = {"cursando": "Cursando {}", "completo": "{} completo", "minimo": "A partir do {}"}


def _escolaridade(v: Vaga) -> str | None:
    exigencia = perfil.exigencia_escolar(v)
    if exigencia is None:
        return v.escolaridade or None
    texto = _MODOS[exigencia.modo].format(_NOMES_NIVEIS[exigencia.nivel])
    return texto[:1].upper() + texto[1:]


def _vaga_json(v: Vaga, cidade: reg.Cidade, com_distrito: bool) -> dict:
    distrito = cidade.distritos.get(v.distrito) if v.distrito else None
    return {
        "id": v.chave,
        "titulo": v.titulo,
        "tipo": v.tipo,
        "empresa": v.empresa,
        "url": v.url,
        "outrosLinks": [{"fonte": f, "url": u} for f, _, u in v.outras_fontes],
        "bairro": v.bairro,
        "distrito": distrito.nome if distrito else None,
        "local": descrever_local(v, cidade, com_distrito),
        "idade": _faixa(v),
        "escolaridade": _escolaridade(v),
        "horario": v.horario or None,
        "salario": v.salario or None,
        "beneficios": v.beneficios or None,
        "turnos": sorted(perfil.turnos_da_vaga(v), key=list(perfil.TURNOS).index),
        "localPeloCep": v.evidencia_local == "CEP",
        "distanciaKm": v.distancia_km,
        "distancia": descrever_distancia(v) if v.distancia_km is not None else None,
        "publicadaEm": v.publicada_em.isoformat() if v.publicada_em else None,
        "fontes": _fontes(v),
        "nova": v.nova,
        "semExperiencia": v.sem_experiencia,
        "remota": v.remota and not v.regiao,
        "cidadeVizinha": v.regiao if v.regiao and v.regiao != cidade.nome else None,
    }


def _resultado_json(r: Resultado) -> dict:
    cidade = r.filtro.cidade
    todas = r.confirmadas + r.sem_local
    extras = r.vizinhas + r.remotas
    return {
        "tipo": "resultado",
        "filtro": r.filtro.descrever(),
        "tipos": r.tipos,
        "pertoDe": r.referencia[0] if r.referencia else None,
        "executadoEm": r.executado_em.isoformat(timespec="seconds"),
        "resumo": {
            "total": len(todas),
            "comLocal": sum(v.distrito is not None for v in todas),
            "novas": sum(v.nova for v in todas + extras),
            "vizinhas": len(r.vizinhas) if r.cidades_vizinhas else None,
            "remotas": len(r.remotas),
            "antigas": r.antigas,
            "perfilAvancado": r.perfil_avancado,
            "foraDoFiltro": r.fora_do_filtro,
            "foraDoRaio": r.fora_do_raio,
            "foraDoPerfil": r.fora_do_perfil,
            "ocultasSemLocal": r.ocultas_sem_local,
        },
        "porFonte": r.por_fonte,
        "linkedin": links.linkedin(cidade, tipos=r.tipos),
        "linkedinRemotas": links.linkedin_remotas(r.tipos),
        "erros": r.erros,
        "secoes": [
            {
                "titulo": s.titulo,
                "comDistancia": s.com_distancia,
                "vagas": [_vaga_json(v, cidade, s.com_distrito) for v in s.vagas],
            }
            for s in montar_secoes(r)
            if s.vagas
        ],
    }


def _linha(dados: dict) -> bytes:
    return (json.dumps(dados, ensure_ascii=False) + "\n").encode("utf-8")


def _sem_marcacao(texto: str) -> str:
    return re.sub(r"\[/?[a-z ]*\]", "", texto)  # tira as cores do terminal ([yellow]...[/])


@app.post("/api/buscar")
async def buscar(busca: Busca) -> StreamingResponse:
    fila: asyncio.Queue[dict | None] = asyncio.Queue()

    async def executar() -> None:
        try:
            cidade = reg.encontrar_cidade(reg.carregar(), busca.cidade, busca.uf)
            filtro = reg.montar_filtro(cidade, busca.distritos, busca.bairros)
            extras = reg.escolher_vizinhas(cidade, busca.vizinhas)
            desconhecidas = [f for f in busca.fontes if f not in TODAS]
            if desconhecidas:
                raise reg.RegiaoDesconhecida(f"Fonte(s) desconhecida(s): {', '.join(desconhecidas)}")
            if busca.turno_escola and busca.turno_escola not in perfil.TURNOS:
                raise reg.RegiaoDesconhecida(f"Turno desconhecido: {busca.turno_escola}")
            if busca.escolaridade and busca.escolaridade not in perfil.ESCOLARIDADES:
                raise reg.RegiaoDesconhecida(f"Escolaridade desconhecida: {busca.escolaridade}")
            tipos_invalidos = [t for t in busca.tipos if t not in TIPOS]
            if tipos_invalidos or not busca.tipos:
                raise reg.RegiaoDesconhecida(
                    f"Escolha pelo menos um tipo de vaga válido ({', '.join(TIPOS)})."
                )
            if busca.raio is not None and not busca.perto_de:
                raise reg.RegiaoDesconhecida("O raio só funciona junto com \"Perto de\".")
            fontes = [TODAS[f] for f in busca.fontes] or list(TODAS.values())

            if _uma_busca_por_vez.locked():
                await fila.put({"tipo": "aviso", "mensagem": "Outra busca está em andamento; aguardando..."})
            async with _uma_busca_por_vez:
                with Historico(CAMINHO_PADRAO) as historico:
                    resultado = await coletar(
                        filtro,
                        fontes,
                        historico,
                        ler_detalhes=busca.ler_detalhes,
                        max_paginas=busca.paginas,
                        perto_de=(busca.perto_de or "").strip() or None,
                        vizinhas=extras,
                        incluir_remotas=busca.incluir_remotas,
                        tipos=busca.tipos,
                        aviso=lambda m: fila.put_nowait({"tipo": "aviso", "mensagem": _sem_marcacao(m)}),
                    )
            pos_filtrar(
                resultado,
                novas=busca.novas,
                somente_com_bairro=busca.somente_com_bairro,
                raio=busca.raio,
                idade=busca.idade,
                escolaridade=busca.escolaridade,
                turno_escola=busca.turno_escola,
            )
            await fila.put(_resultado_json(resultado))
        except (reg.RegiaoDesconhecida, ReferenciaNaoEncontrada, BuscaInvalida) as e:
            await fila.put({"tipo": "erro", "mensagem": str(e)})
        except Exception as e:  # noqa: BLE001 - a tela precisa saber que algo deu errado
            await fila.put({"tipo": "erro", "mensagem": f"Falha inesperada: {e.__class__.__name__}: {e}"})
        finally:
            await fila.put(None)

    async def eventos():
        tarefa = asyncio.create_task(executar())
        try:
            while (evento := await fila.get()) is not None:
                yield _linha(evento)
        finally:
            await tarefa

    return StreamingResponse(eventos(), media_type="application/x-ndjson")


# Interface compilada (npm run build). Em desenvolvimento, o Vite serve a interface e repassa /api para cá.
if PASTA_WEB.exists():
    app.mount("/assets", StaticFiles(directory=PASTA_WEB / "assets"), name="assets")

    @app.get("/{caminho:path}", include_in_schema=False)
    def interface(caminho: str) -> FileResponse:
        arquivo = (PASTA_WEB / caminho).resolve()
        if caminho and arquivo.is_relative_to(PASTA_WEB.resolve()) and arquivo.is_file():
            return FileResponse(arquivo)
        return FileResponse(PASTA_WEB / "index.html")
