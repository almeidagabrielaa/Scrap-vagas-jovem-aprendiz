"""Exibição no terminal e exportação para CSV, JSON e HTML."""

from __future__ import annotations

import csv
import html
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .coletor import Resultado
from .geo import distancia_km, formatar_km
from .modelos import Vaga
from .regioes import Cidade
from .texto import normalizar

NOMES_FONTES = {
    "gupy": "Gupy",
    "infojobs": "InfoJobs",
    "catho": "Catho",
    "trabalhabrasil": "Trabalha Brasil",
    "vagas.com": "Vagas.com.br",
    "bne": "BNE",
}


def descrever_local(vaga: Vaga, cidade: Cidade, com_distrito: bool = True) -> str:
    if not vaga.regiao and vaga.remota:
        sede = f"{vaga.cidade}/{vaga.uf}" if vaga.cidade and vaga.uf else vaga.cidade
        return "Remoto (home office)" + (f" · empresa em {sede}" if sede else "")
    if vaga.regiao and vaga.regiao != cidade.nome:
        return f"{vaga.regiao}/{vaga.uf or cidade.uf}"
    distrito = cidade.distritos.get(vaga.distrito) if vaga.distrito and com_distrito else None
    if vaga.bairro:
        texto = vaga.bairro + (f" · {distrito.nome}" if distrito else "")
    elif distrito:
        texto = f"{distrito.nome} · bairro não informado"
    elif vaga.distrito and not com_distrito:
        return "bairro não informado"
    else:
        return "não informado"
    if vaga.evidencia_local == "CEP":
        texto += " (pelo CEP)"
    return texto


def _fontes(vaga: Vaga) -> str:
    nomes = [NOMES_FONTES.get(vaga.fonte, vaga.fonte)]
    nomes += [NOMES_FONTES.get(f, f) for f, _, _ in vaga.outras_fontes]
    return ", ".join(dict.fromkeys(nomes))


def descrever_distancia(vaga: Vaga) -> str:
    if vaga.distancia_km is None:
        return "-"
    if vaga.distancia_por == "bairro" and vaga.distancia_km < 0.05:
        return "mesmo bairro"
    # "~" quando a conta usa o centro do bairro, e não o endereço da vaga.
    return ("" if vaga.distancia_por == "endereço" else "~") + formatar_km(vaga.distancia_km)


def _tabela(
    vagas: list[Vaga], cidade: Cidade, titulo: str, com_distrito: bool = True, com_distancia: bool = False
) -> Table:
    tabela = Table(title=titulo, title_justify="left", show_lines=True, expand=True)
    tabela.add_column("", width=6)
    if com_distancia:
        tabela.add_column("Distância", no_wrap=True, justify="right")
    tabela.add_column("Vaga", ratio=3)
    tabela.add_column("Local" if com_distrito else "Bairro", ratio=2)
    tabela.add_column("Publicada", no_wrap=True)
    tabela.add_column("Fonte", ratio=1)
    tabela.add_column("Link", ratio=3, overflow="fold")
    for v in vagas:
        vaga = Text(v.titulo, style="bold")
        if v.empresa:
            vaga.append(f"\n{v.empresa}", style="dim")
        selos = Text()
        if v.nova:
            selos.append("NOVA", style="bold green")
        if v.remota and not v.regiao:
            selos.append(("\n" if v.nova else "") + "VAGA REMOTA", style="bold cyan")
        tabela.add_row(
            selos,
            *([Text(descrever_distancia(v), style="bold")] if com_distancia else []),
            vaga,
            descrever_local(v, cidade, com_distrito),
            v.publicada_em.strftime("%d/%m/%Y") if v.publicada_em else "-",
            _fontes(v),
            Text(v.url, style=f"link {v.url} cyan"),
        )
    return tabela


def _por_bairro(vaga: Vaga):
    # Bairro em ordem alfabética (sem bairro por último); dentro do bairro, novas e mais recentes primeiro.
    return (vaga.bairro is None, normalizar(vaga.bairro or ""), not vaga.nova, -(vaga.publicada_em or date.min).toordinal())


def agrupar(vagas: list[Vaga], cidade: Cidade) -> list[tuple[str, list[Vaga], bool]]:
    """Separa as vagas por distrito, ordenadas por bairro. Vagas sem distrito ficam num grupo no fim.

    Devolve (título, vagas, é_um_distrito).
    """
    grupos: list[tuple[str, list[Vaga], bool]] = []
    for num, distrito in cidade.distritos.items():
        do_distrito = sorted((v for v in vagas if v.distrito == num), key=_por_bairro)
        if do_distrito:
            grupos.append((distrito.nome, do_distrito, True))
    sem_distrito = sorted((v for v in vagas if v.distrito not in cidade.distritos), key=_por_bairro)
    if sem_distrito:
        titulo = f"{cidade.nome}, local não informado no anúncio" if cidade.distritos else cidade.nome
        grupos.append((titulo, sem_distrito, False))
    return grupos


@dataclass
class Secao:
    titulo: str
    vagas: list[Vaga]
    com_distrito: bool = True  # a coluna de local mostra o distrito?
    com_distancia: bool = False


def _secao_remotas(resultado: Resultado) -> list[Secao]:
    if not resultado.remotas:
        return []
    return [Secao("Remotas (home office) · qualquer lugar do Brasil", resultado.remotas)]


def _secoes_vizinhas(resultado: Resultado) -> list[Secao]:
    """Uma seção por cidade vizinha, da mais próxima para a mais distante."""
    principal = resultado.filtro.cidade
    secoes = []
    for c in resultado.cidades_vizinhas:
        vagas = [v for v in resultado.vizinhas if v.regiao == c.nome]
        if not vagas:
            continue
        km = distancia_km(principal.coordenadas, c.coordenadas) if principal.coordenadas and c.coordenadas else None
        titulo = c.nome + (f" · {formatar_km(km)} de {principal.nome}" if km is not None else "")
        secoes.append((km if km is not None else 9e9, Secao(titulo, vagas)))
    return [s for _, s in sorted(secoes, key=lambda x: x[0])]


def montar_secoes(resultado: Resultado, incluir_sem_local: bool = True) -> list[Secao]:
    """Organiza as vagas para exibir: por distância (com --perto-de) ou por distrito, bairro e cidade."""
    cidade = resultado.filtro.cidade
    if resultado.referencia:
        todas = resultado.confirmadas + (resultado.sem_local if incluir_sem_local else []) + resultado.vizinhas
        com = sorted((v for v in todas if v.distancia_km is not None), key=lambda v: v.distancia_km)
        sem = sorted((v for v in todas if v.distancia_km is None), key=_por_bairro)
        secoes = [Secao(f"Mais perto de {resultado.referencia[0]}", com, com_distancia=True)]
        if sem:
            secoes.append(Secao("Sem como calcular a distância (o anúncio não diz o bairro)", sem))
        return secoes + _secao_remotas(resultado)
    secoes = [Secao(t, g, com_distrito=not eh) for t, g, eh in agrupar(resultado.confirmadas, cidade)]
    if resultado.sem_local and incluir_sem_local:
        secoes.append(
            Secao(f"Em {cidade.nome}, mas o anúncio não diz o bairro", sorted(resultado.sem_local, key=_por_bairro))
        )
    return secoes + _secoes_vizinhas(resultado) + _secao_remotas(resultado)


def mostrar(resultado: Resultado, console: Console, mostrar_sem_local: bool = True) -> None:
    filtro = resultado.filtro
    console.print()
    console.rule(f"[bold]Vagas de Jovem Aprendiz · {filtro.descrever()}")
    secoes = [s for s in montar_secoes(resultado, mostrar_sem_local) if s.vagas]
    if not secoes:
        console.print("[yellow]Nenhuma vaga encontrada na região pedida.[/]")
    for s in secoes:
        console.print(
            _tabela(s.vagas, filtro.cidade, f"[bold]{s.titulo}[/] ({len(s.vagas)})", s.com_distrito, s.com_distancia)
        )
        console.print()
    if resultado.sem_local and not mostrar_sem_local:
        console.print(f"[dim]{len(resultado.sem_local)} vaga(s) sem bairro informado foram ocultadas.[/]")
    if resultado.referencia:
        console.print(
            "[dim]Distância em linha reta. \"~\" = calculada pelo centro do bairro (ou da cidade, nas vizinhas), "
            "porque o anúncio não traz o endereço.[/]"
        )

    console.print()
    todas = resultado.confirmadas + resultado.sem_local
    novas = sum(v.nova for v in todas)
    com_local = sum(v.distrito is not None for v in todas)
    resumo = (
        f"[bold]{len(todas)}[/] vaga(s) em {filtro.cidade.nome}: "
        f"{com_local} com local identificado, {len(todas) - com_local} sem local no anúncio"
    )
    if resultado.fora_do_filtro:
        resumo += f", {resultado.fora_do_filtro} fora do filtro (ocultas)"
    if resultado.fora_do_raio:
        resumo += f", {resultado.fora_do_raio} além do raio (ocultas)"
    if resultado.cidades_vizinhas:
        resumo += f" · [bold]{len(resultado.vizinhas)}[/] em cidades vizinhas"
    if resultado.remotas:
        resumo += f" · [bold]{len(resultado.remotas)}[/] remota(s)"
    novas += sum(v.nova for v in resultado.vizinhas + resultado.remotas)
    resumo += f" · [green]{novas} nova(s)[/] desde a última execução"
    console.print(resumo)
    if resultado.por_fonte:
        console.print(
            "[dim]Por fonte: " + ", ".join(f"{k} {n}" for k, n in resultado.por_fonte.items()) + "[/]"
        )
    for fonte, erro in resultado.erros.items():
        console.print(f"[yellow]Aviso:[/] {fonte} não foi consultada: {erro}")


# ---------------------------------------------------------------- exportação


def _linhas(resultado: Resultado) -> list[dict]:
    cidade = resultado.filtro.cidade
    linhas = []
    situacoes = {id(v): "confirmada" for v in resultado.confirmadas}
    situacoes.update({id(v): "cidade_vizinha" for v in resultado.vizinhas})
    situacoes.update({id(v): "remota" for v in resultado.remotas})
    for secao in montar_secoes(resultado):
        for v in secao.vagas:
            distrito = cidade.distritos.get(v.distrito) if v.distrito else None
            linhas.append(
                {
                    "situacao": situacoes.get(id(v), "sem_bairro"),
                    "nova": v.nova,
                    "titulo": v.titulo,
                    "empresa": v.empresa,
                    "cidade": v.cidade,
                    "uf": v.uf,
                    "bairro": v.bairro or "",
                    "distrito": distrito.nome if distrito else "",
                    "local_identificado_por": v.evidencia_local,
                    "distancia_km": f"{v.distancia_km:.1f}".replace(".", ",") if v.distancia_km is not None else "",
                    "distancia_calculada_por": v.distancia_por,
                    "endereco": v.endereco,
                    "cep": v.cep or "",
                    "publicada_em": v.publicada_em.isoformat() if v.publicada_em else "",
                    "fonte": _fontes(v),
                    "url": v.url,
                    "outros_links": " ".join(u for _, _, u in v.outras_fontes),
                }
            )
    return linhas


def exportar_csv(resultado: Resultado, caminho: Path) -> None:
    linhas = _linhas(resultado)
    campos = list(linhas[0].keys()) if linhas else ["titulo"]
    # utf-8-sig para o Excel abrir os acentos corretamente
    with caminho.open("w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)


def exportar_json(resultado: Resultado, caminho: Path) -> None:
    dados = {
        "filtro": resultado.filtro.descrever(),
        "perto_de": resultado.referencia[0] if resultado.referencia else None,
        "executado_em": resultado.executado_em.isoformat(timespec="seconds"),
        "erros": resultado.erros,
        "vagas": _linhas(resultado),
    }
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def exportar_html(resultado: Resultado, caminho: Path) -> None:
    cidade = resultado.filtro.cidade
    e = html.escape

    def cartoes(vagas: list[Vaga], com_distrito: bool = True, com_distancia: bool = False) -> str:
        itens = []
        for v in vagas:
            itens.append(
                f"""<li class="vaga">
  <div class="topo">{'<span class="nova">nova</span>' if v.nova else ''}
    <a href="{e(v.url)}" target="_blank" rel="noopener">{e(v.titulo)}</a></div>
  <div class="empresa">{e(v.empresa or 'Empresa não informada')}</div>
  <div class="meta">{f'<strong>{e(descrever_distancia(v))}</strong>' if com_distancia else ''}<span>{e(descrever_local(v, cidade, com_distrito))}</span>
    <span>{v.publicada_em.strftime('%d/%m/%Y') if v.publicada_em else ''}</span>
    <span>{e(_fontes(v))}</span></div>
</li>"""
            )
        return "\n".join(itens) or '<li class="vazio">Nenhuma vaga.</li>'

    erros = "".join(f"<li>{e(f)}: {e(m)}</li>" for f, m in resultado.erros.items())
    secoes = "\n".join(
        f"<section><h2>{e(s.titulo)} ({len(s.vagas)})</h2>"
        f"<ul>{cartoes(s.vagas, s.com_distrito, s.com_distancia)}</ul></section>"
        for s in montar_secoes(resultado)
        if s.vagas
    ) or '<section><p class="vazio">Nenhuma vaga encontrada na região pedida.</p></section>'
    pagina = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vagas de Jovem Aprendiz · {e(resultado.filtro.descrever())}</title>
<style>
:root {{ --bg:#f3f6f6; --card:#fff; --fg:#16302f; --muted:#546b6a; --line:#d3dedd; --accent:#0d7570; --ok:#2f7a3a; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0f1a1a; --card:#152424; --fg:#e3eeed; --muted:#93abaa; --line:#26393a; --accent:#4fc3b9; --ok:#7fcf8a; }} }}
body {{ background:var(--bg); color:var(--fg); font:16px/1.5 "Segoe UI",system-ui,sans-serif; margin:0; padding:2rem 1rem; }}
main {{ max-width:56rem; margin:0 auto; display:grid; gap:1.5rem; }}
h1 {{ margin:0; font-size:1.75rem; }} h2 {{ margin:0; font-size:1.2rem; }}
.sub {{ color:var(--muted); }}
ul {{ list-style:none; margin:0; padding:0; display:grid; gap:.6rem; }}
.vaga {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:.9rem 1rem; display:grid; gap:.25rem; }}
.vaga a {{ color:var(--fg); font-weight:600; text-decoration:none; }} .vaga a:hover {{ color:var(--accent); text-decoration:underline; }}
.empresa {{ color:var(--muted); }}
.meta {{ display:flex; flex-wrap:wrap; gap:.4rem 1.2rem; font-size:.875rem; color:var(--muted); }}
.nova {{ font-size:.7rem; font-weight:700; text-transform:uppercase; color:var(--ok); border:1px solid var(--ok); border-radius:99px; padding:.05rem .45rem; margin-right:.4rem; }}
.vazio {{ color:var(--muted); }}
</style></head><body><main>
<header><h1>Vagas de Jovem Aprendiz</h1>
<p class="sub">{e(resultado.filtro.descrever())} · gerado em {resultado.executado_em.strftime('%d/%m/%Y %H:%M')}</p></header>
{secoes}
{f'<section><h2>Fontes com problema</h2><ul>{erros}</ul></section>' if erros else ''}
</main></body></html>"""
    caminho.write_text(pagina, encoding="utf-8")
