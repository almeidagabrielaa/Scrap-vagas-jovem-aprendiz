"""Linha de comando: `radar buscar`, `radar regioes`, `radar fontes`, `radar limpar-historico`."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.tree import Tree

from . import regioes as reg
from . import saida
from . import links
from .coletor import IDADE_MAXIMA_DIAS, ReferenciaNaoEncontrada, coletar, pos_filtrar
from .fontes import TODAS
from .historico import CAMINHO_PADRAO, Historico

app = typer.Typer(
    help="Busca vagas de Jovem Aprendiz na internet e filtra por cidade, distrito e bairro.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

OpcaoRegioes = typer.Option(None, "--regioes", help="Arquivo YAML de regiões (padrão: o que vem no pacote).")


def _cidade(arquivo: Optional[Path], cidade: str, uf: Optional[str]) -> reg.Cidade:
    try:
        return reg.encontrar_cidade(reg.carregar(arquivo), cidade, uf)
    except reg.RegiaoDesconhecida as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(2)


@app.command()
def buscar(
    cidade: str = typer.Option("Cabo Frio", "--cidade", "-c", help="Cidade onde procurar."),
    uf: Optional[str] = typer.Option(None, "--uf", help="UF (só é necessária para cidades fora do regioes.yaml)."),
    distrito: list[str] = typer.Option(
        [], "--distrito", "-d", help='Número ou nome do distrito ("2", "Tamoios"). Pode repetir.'
    ),
    bairro: list[str] = typer.Option([], "--bairro", "-b", help="Bairro. Pode repetir."),
    perto_de: Optional[str] = typer.Option(
        None, "--perto-de", "-p", help='Seu bairro ou endereço. Ordena as vagas pela distância ("Unamar", "Rua X, 100, Peró").'
    ),
    raio: Optional[float] = typer.Option(
        None, "--raio", min=0.1, help="Com --perto-de: esconde vagas a mais de N km."
    ),
    vizinha: list[str] = typer.Option(
        [], "--vizinha", "-v", help='Também busca nesta cidade vizinha ("Arraial do Cabo", "Búzios"). Pode repetir.'
    ),
    vizinhas: bool = typer.Option(False, "--vizinhas", help="Também busca em todas as cidades vizinhas cadastradas."),
    remotas: bool = typer.Option(False, "--remotas", help="Inclui vagas 100% remotas (home office) de todo o Brasil."),
    novas: bool = typer.Option(False, "--novas", help="Mostra só vagas que não apareceram em execuções anteriores."),
    somente_com_bairro: bool = typer.Option(
        False, "--somente-com-bairro", help="Esconde vagas cujo anúncio não informa bairro/distrito."
    ),
    fontes: Optional[str] = typer.Option(
        None, "--fontes", help=f"Lista separada por vírgula. Opções: {', '.join(TODAS)}."
    ),
    sem_detalhes: bool = typer.Option(
        False, "--sem-detalhes", help="Não abre cada anúncio (mais rápido, mas acha menos bairros)."
    ),
    paginas: int = typer.Option(3, "--paginas", min=1, max=20, help="Máximo de páginas por fonte."),
    csv: Optional[Path] = typer.Option(None, "--csv", help="Salva o resultado em CSV."),
    json: Optional[Path] = typer.Option(None, "--json", help="Salva o resultado em JSON."),
    html: Optional[Path] = typer.Option(None, "--html", help="Salva um relatório HTML."),
    arquivo_regioes: Optional[Path] = OpcaoRegioes,
    banco: Path = typer.Option(CAMINHO_PADRAO, "--banco", help="Arquivo SQLite do histórico."),
) -> None:
    """Procura vagas agora, na internet, para a região informada."""
    c = _cidade(arquivo_regioes, cidade, uf)
    if raio is not None and not perto_de:
        console.print("[red]--raio só funciona junto com --perto-de.[/]")
        raise typer.Exit(2)
    try:
        filtro = reg.montar_filtro(c, distrito, bairro)
        extras = reg.escolher_vizinhas(c, vizinha, todas=vizinhas)
    except reg.RegiaoDesconhecida as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(2)

    if fontes:
        nomes = [n.strip().lower() for n in fontes.split(",") if n.strip()]
        invalidas = [n for n in nomes if n not in TODAS]
        if invalidas:
            console.print(f"[red]Fonte(s) desconhecida(s): {', '.join(invalidas)}. Opções: {', '.join(TODAS)}.[/]")
            raise typer.Exit(2)
        escolhidas = [TODAS[n] for n in nomes]
    else:
        escolhidas = list(TODAS.values())

    console.print(f"Buscando vagas de aprendiz em [bold]{filtro.descrever()}[/] em {len(escolhidas)} fonte(s)...")
    with Historico(banco) as historico, console.status("Consultando os sites...") as status:

        def aviso(msg: str) -> None:
            console.print(f"  {msg}")
            status.update(msg)

        try:
            resultado = asyncio.run(
                coletar(
                    filtro,
                    escolhidas,
                    historico,
                    ler_detalhes=not sem_detalhes,
                    max_paginas=paginas,
                    aviso=aviso,
                    perto_de=perto_de,
                    vizinhas=extras,
                    incluir_remotas=remotas,
                )
            )
        except ReferenciaNaoEncontrada as e:
            console.print(f"[red]{e}[/]")
            raise typer.Exit(2)

    pos_filtrar(resultado, novas=novas, somente_com_bairro=somente_com_bairro, raio=raio)
    saida.mostrar(resultado, console)
    if resultado.ocultas_sem_local:
        console.print(f"[dim]{resultado.ocultas_sem_local} vaga(s) sem bairro informado foram ocultadas.[/]")
    if resultado.antigas:
        console.print(f"[dim]{resultado.antigas} anúncio(s) com mais de {IDADE_MAXIMA_DIAS} dias foram ignorados.[/]")
    console.print(f"[dim]O LinkedIn não permite busca automática. Veja à mão: {links.linkedin(c)}[/]")
    if remotas:
        console.print(f"[dim]Remotas no LinkedIn: {links.linkedin_remotas()}[/]")

    for caminho, exportar in ((csv, saida.exportar_csv), (json, saida.exportar_json), (html, saida.exportar_html)):
        if caminho:
            exportar(resultado, caminho)
            console.print(f"Salvo em [bold]{caminho}[/]")


@app.command()
def regioes(
    cidade: Optional[str] = typer.Option(None, "--cidade", "-c", help="Mostra só esta cidade."),
    arquivo_regioes: Optional[Path] = OpcaoRegioes,
) -> None:
    """Lista cidades, distritos e bairros conhecidos."""
    cidades = reg.carregar(arquivo_regioes).values()
    if cidade:
        cidades = [_cidade(arquivo_regioes, cidade, None)]
    for c in cidades:
        arvore = Tree(f"[bold]{c.nome}/{c.uf}[/]")
        for num, d in c.distritos.items():
            ramo = arvore.add(f"[cyan]{d.nome}[/]  [dim](--distrito {num})[/]")
            ramo.add(", ".join(b.nome for b in d.bairros))
        console.print(arvore)
    console.print(f"[dim]Arquivo: {arquivo_regioes or reg.caminho_padrao()}[/]")


@app.command("fontes")
def listar_fontes() -> None:
    """Lista os sites consultados."""
    for f in TODAS.values():
        console.print(f"[bold]{f.nome:15}[/] {f.titulo:16} {f.site}")


@app.command()
def web(
    porta: int = typer.Option(8000, "--porta", help="Porta do servidor local."),
    abrir: bool = typer.Option(True, "--abrir/--nao-abrir", help="Abre o navegador automaticamente."),
) -> None:
    """Abre a interface no navegador (FMT - jovem aprendiz)."""
    import threading
    import webbrowser

    import uvicorn

    from .api import PASTA_WEB

    if not (PASTA_WEB / "index.html").exists():
        console.print(
            "[yellow]A interface ainda não foi compilada. Rode uma vez:[/]\n"
            "  cd web\n  npm install\n  npm run build\n"
            "[dim](a API funciona mesmo assim em /api)[/]"
        )
    endereco = f"http://127.0.0.1:{porta}"
    console.print(f"Interface em [bold]{endereco}[/]  (Ctrl+C para parar)")
    if abrir:
        threading.Timer(1.5, lambda: webbrowser.open(endereco)).start()
    uvicorn.run("radar.api:app", host="127.0.0.1", port=porta, log_level="warning")


@app.command("limpar-historico")
def limpar_historico(banco: Path = typer.Option(CAMINHO_PADRAO, "--banco")) -> None:
    """Esquece as vagas já vistas (todas voltam a aparecer como novas)."""
    with Historico(banco) as h:
        n = h.limpar_vagas()
    console.print(f"{n} registro(s) removido(s) de {banco}.")


if __name__ == "__main__":
    app()
