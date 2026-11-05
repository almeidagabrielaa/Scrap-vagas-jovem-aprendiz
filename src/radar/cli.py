"""Linha de comando: `radar buscar`, `radar agendar`, `radar regioes`, `radar fontes`, `radar limpar-historico`."""

from __future__ import annotations

import asyncio
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.tree import Tree

from . import regioes as reg
from . import saida
from . import avisos, links, perfil
from .coletor import IDADE_MAXIMA_DIAS, BuscaInvalida, ReferenciaNaoEncontrada, coletar, pos_filtrar
from .filtro import TIPOS, descrever_tipos
from .fontes import TODAS
from .historico import CAMINHO_PADRAO, Historico
from .texto import sem_acentos

app = typer.Typer(
    help="Busca vagas de Jovem Aprendiz (e de meio período) na internet e filtra por cidade, distrito e bairro.",
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
    tipo: list[str] = typer.Option(
        ["aprendiz"], "--tipo", "-t",
        help='Tipo de vaga: "aprendiz", "estagio", "meio-periodo" (part-time) ou "primeiro-emprego". Pode repetir.',
    ),
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
    idade: Optional[int] = typer.Option(
        None, "--idade", min=14, max=29, help="Tua idade: esconde vagas que pedem outra faixa (ex.: 18 a 24 anos)."
    ),
    escolaridade: Optional[str] = typer.Option(
        None, "--escolaridade", help=f"Tua escolaridade: {', '.join(perfil.ESCOLARIDADES)}."
    ),
    estudo_de: Optional[str] = typer.Option(
        None, "--estudo-de", help="Turno da tua escola (manha, tarde, noite): esconde vagas no mesmo horário."
    ),
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
    avisar: bool = typer.Option(
        False, "--avisar", help="Manda as vagas novas por Telegram e/ou e-mail (veja `radar agendar --help`)."
    ),
    arquivo_regioes: Optional[Path] = OpcaoRegioes,
    banco: Path = typer.Option(CAMINHO_PADRAO, "--banco", help="Arquivo SQLite do histórico."),
) -> None:
    """Procura vagas agora, na internet, para a região informada."""
    if estudo_de:
        estudo_de = sem_acentos(estudo_de.strip().lower())
        if estudo_de not in perfil.TURNOS:
            console.print("[red]--estudo-de aceita: manha, tarde, noite.[/]")
            raise typer.Exit(2)
    if escolaridade and escolaridade not in perfil.ESCOLARIDADES:
        console.print(f"[red]Escolaridade desconhecida. Opções: {', '.join(perfil.ESCOLARIDADES)}.[/]")
        raise typer.Exit(2)
    canais = avisos.Canais.do_ambiente()
    if avisar and not canais.algum:
        console.print(
            "[red]--avisar precisa de um canal configurado: RADAR_TELEGRAM_TOKEN + RADAR_TELEGRAM_CHAT "
            "e/ou RADAR_SMTP_HOST + RADAR_EMAIL_PARA (veja `radar agendar --help`).[/]"
        )
        raise typer.Exit(2)
    c = _cidade(arquivo_regioes, cidade, uf)
    tipos = list(dict.fromkeys(sem_acentos(t.strip().lower()).replace("-", "_") for t in tipo))
    if invalidos := [t for t in tipos if t not in TIPOS]:
        console.print(f"[red]Tipo(s) desconhecido(s): {', '.join(invalidos)}. Opções: aprendiz, estagio, meio-periodo, primeiro-emprego.[/]")
        raise typer.Exit(2)
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

    console.print(
        f"Buscando vagas ({descrever_tipos(tipos).lower()}) em [bold]{filtro.descrever()}[/] em {len(escolhidas)} fonte(s)..."
    )
    sem_suporte = [f.titulo for f in escolhidas if not f.tipos.intersection(tipos)]
    if sem_suporte:
        console.print(f"[dim]Sem busca para esse tipo de vaga (ficam de fora): {', '.join(sem_suporte)}[/]")
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
                    tipos=tipos,
                )
            )
        except (ReferenciaNaoEncontrada, BuscaInvalida) as e:
            console.print(f"[red]{e}[/]")
            raise typer.Exit(2)

    pos_filtrar(
        resultado, novas=novas, somente_com_bairro=somente_com_bairro, raio=raio, idade=idade, escolaridade=escolaridade,
        turno_escola=estudo_de,
    )
    saida.mostrar(resultado, console)
    if resultado.ocultas_sem_local:
        console.print(f"[dim]{resultado.ocultas_sem_local} vaga(s) sem bairro informado foram ocultadas.[/]")
    if resultado.fora_do_perfil:
        console.print(f"[dim]{resultado.fora_do_perfil} vaga(s) pedem outra idade/escolaridade ou batem com o horário da escola e foram ocultadas.[/]")
    if resultado.perfil_avancado:
        console.print(
            f"[dim]{resultado.perfil_avancado} vaga(s) que pedem faculdade, liderança ou experiência foram ocultadas.[/]"
        )
    if resultado.antigas:
        console.print(f"[dim]{resultado.antigas} anúncio(s) com mais de {IDADE_MAXIMA_DIAS} dias foram ignorados.[/]")
    console.print(f"[dim]O LinkedIn não permite busca automática. Veja à mão: {links.linkedin(c, tipos=tipos)}[/]")
    if remotas:
        console.print(f"[dim]Remotas no LinkedIn: {links.linkedin_remotas(tipos)}[/]")

    for caminho, exportar in ((csv, saida.exportar_csv), (json, saida.exportar_json), (html, saida.exportar_html)):
        if caminho:
            exportar(resultado, caminho)
            console.print(f"Salvo em [bold]{caminho}[/]")

    if avisar:
        for relato in avisos.avisar(resultado, canais):
            console.print(f"Aviso · {relato}")


NOME_TAREFA = "Radar Jovem Aprendiz"


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def agendar(
    contexto: typer.Context,
    hora: str = typer.Option("08:00", "--hora", help="Horário diário da busca (HH:MM)."),
    remover: bool = typer.Option(False, "--remover", help="Apaga o agendamento criado antes."),
    so_mostrar: bool = typer.Option(False, "--so-mostrar", help="Só mostra o comando, sem agendar."),
) -> None:
    """Roda `radar buscar --avisar` todo dia e manda as vagas novas por Telegram e/ou e-mail.

    Tudo depois das opções vai para o `radar buscar`. Exemplo:

        radar agendar --hora 07:30 -t aprendiz -t estagio --vizinha Búzios

    Antes, configure pelo menos um canal (no Windows: `setx NOME valor` e abra um terminal novo):

    \b
      Telegram: RADAR_TELEGRAM_TOKEN (crie o bot com o @BotFather) e RADAR_TELEGRAM_CHAT (o id da conversa;
                mande uma mensagem ao bot e veja https://api.telegram.org/bot<TOKEN>/getUpdates).
      E-mail:   RADAR_SMTP_HOST, RADAR_SMTP_PORTA (587), RADAR_SMTP_USUARIO, RADAR_SMTP_SENHA, RADAR_EMAIL_PARA.
                No Gmail, use uma "senha de app" (smtp.gmail.com).

    A primeira execução marca tudo como novo; o aviso traz no máximo 15 vagas.
    """
    windows = sys.platform == "win32"
    if remover:
        if windows:
            subprocess.run(["schtasks", "/Delete", "/TN", NOME_TAREFA, "/F"], check=False)
        else:
            console.print("Remova a linha do radar com `crontab -e`.")
        return
    try:
        hh, mm = (int(p) for p in hora.split(":"))
        assert 0 <= hh < 24 and 0 <= mm < 60
    except (ValueError, AssertionError):
        console.print("[red]--hora precisa ser HH:MM (ex.: 08:00).[/]")
        raise typer.Exit(2)
    if not avisos.Canais.do_ambiente().algum:
        console.print("[yellow]Nenhum canal de aviso configurado ainda; a busca agendada vai falhar até você configurar.[/]")

    argumentos = [sys.executable, "-m", "radar", "buscar", *contexto.args, "--avisar"]
    if windows:
        comando = subprocess.list2cmdline(argumentos)
        agenda = ["schtasks", "/Create", "/SC", "DAILY", "/ST", f"{hh:02d}:{mm:02d}", "/TN", NOME_TAREFA, "/TR", comando, "/F"]
        if so_mostrar:
            console.print(subprocess.list2cmdline(agenda))
            return
        feito = subprocess.run(agenda, capture_output=True, text=True)
        if feito.returncode != 0:
            console.print(f"[red]O Agendador de Tarefas recusou: {feito.stderr.strip() or feito.stdout.strip()}[/]")
            raise typer.Exit(1)
        console.print(f'Agendado: todo dia às {hh:02d}:{mm:02d} ("{NOME_TAREFA}" no Agendador de Tarefas).')
        console.print(f"[dim]Comando: {comando}[/]\n[dim]Para tirar: radar agendar --remover[/]")
    else:
        linha = f"{mm} {hh} * * * {shlex.join(argumentos)}"
        console.print("Adicione esta linha com `crontab -e` (as variáveis RADAR_* precisam estar no crontab):")
        console.print(linha)


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
        tipos = ", ".join(TIPOS[t].lower() for t in TIPOS if t in f.tipos)
        console.print(f"[bold]{f.nome:15}[/] {f.titulo:16} {f.site:32} [dim]{tipos}[/]")


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
