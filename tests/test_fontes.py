"""Testa os leitores de cada site com trechos de HTML no formato real das páginas."""

import json
from datetime import date

from radar import detalhes
from radar.fontes import catho, gupy, infojobs, trabalha_brasil, vagas_com
from radar.fontes.base import data_br, separar_local


def test_gupy():
    dados = {
        "props": {
            "pageProps": {
                "initialJobList": {
                    "data": [
                        {
                            "id": 1, "name": "Jovem Aprendiz - Park Lagos", "careerPageName": "Lojas Renner",
                            "city": "Cabo Frio", "state": "Rio de Janeiro", "type": "vacancy_type_apprentice",
                            "jobUrl": "https://x.gupy.io/job/1", "publishedDate": "2026-09-01T10:00:00.000Z",
                            "description": "<p>Atuar na loja</p>", "applicationDeadline": None,
                        },
                        {
                            "id": 2, "name": "Jovem Aprendiz", "careerPageName": "Antiga", "city": "Cabo Frio",
                            "state": "Rio de Janeiro", "jobUrl": "https://a&1&inactive.gupy.io/job/2",
                        },
                    ],
                    "pagination": {"total": 2},
                }
            }
        }
    }
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(dados)}</script>'
    vagas, total = gupy.interpretar(html)
    assert total == 2 and len(vagas) == 1  # a vaga "inactive" é descartada
    v = vagas[0]
    assert (v.titulo, v.empresa, v.cidade, v.descricao) == ("Jovem Aprendiz - Park Lagos", "Lojas Renner", "Cabo Frio", "Atuar na loja")
    assert v.eh_aprendiz_na_fonte and v.publicada_em == date(2026, 9, 1)


def test_gupy_prazo_vencido():
    assert gupy.encerrada({"applicationDeadline": "2026-01-01T00:00:00.000Z"}, hoje=date(2026, 10, 5))
    assert not gupy.encerrada({"applicationDeadline": "2026-12-04T00:00:00.000Z"}, hoje=date(2026, 10, 5))


def test_infojobs():
    html = """
    <div class="js_vacancyLoad js_rowCard" data-href="/vaga-de-jovem-aprendiz__123.aspx" data-id="123">
      <div class="js_date" data-value="2026/10/01 07:55:00" hidden></div>
      <a href="/vaga-de-jovem-aprendiz__123.aspx"><h2 class="js_vacancyTitle">Programa Jovem Aprendiz</h2></a>
      <div class="text-body">Natural da Terra</div>
      <div class="mb-8">Cabo Frio - RJ <span hidden>, 0 Km de você.</span></div>
    </div>"""
    [v] = infojobs.interpretar(html)
    assert (v.id_fonte, v.cidade, v.uf, v.empresa) == ("123", "Cabo Frio", "RJ", "Natural da Terra")
    assert v.url == "https://www.infojobs.com.br/vaga-de-jovem-aprendiz__123.aspx"
    assert v.publicada_em == date(2026, 10, 1)


def test_catho():
    html = """
    <article class="offer">
      <span class="tag">Publicada em 01/10</span>
      <h2 class="title_offer"><a href="/vagas/programa-jovem-aprendiz-cabo-frio-rj/38647753"
         title="Programa Jovem Aprendiz Cabo Frio RJ">Programa Jovem Aprendiz Cabo Frio RJ</a></h2>
      <p class="mb-2"><span class="text-12">HORTIFRUTI NATURAL DA TERRA</span></p>
      <p><span class="icon i_job_location"></span><strong>10 vagas</strong> - Cabo Frio</p>
    </article>"""
    [v] = catho.interpretar(html, "RJ")
    assert (v.id_fonte, v.cidade, v.empresa) == ("38647753", "Cabo Frio", "HORTIFRUTI NATURAL DA TERRA")


def test_trabalha_brasil():
    html = """
    <article class="job-card" data-job-id="13562818">
      <a class="job-link" href="/vagas-de-emprego-em-cabo-frio-rj/jovem-aprendiz/13562818">
        <h2 class="job-title">Vaga de Jovem Aprendiz</h2>
        <p class="job-company">Posto Do Bosque Ltda</p>
        <p class="job-location">Cabo Frio/RJ</p>
      </a>
    </article>"""
    [v] = trabalha_brasil.interpretar(html)
    assert (v.id_fonte, v.cidade, v.uf, v.empresa) == ("13562818", "Cabo Frio", "RJ", "Posto Do Bosque Ltda")


def test_vagas_com():
    html = """
    <li class="vaga odd">
      <h2 class="cargo"><a class="link-detalhes-vaga" data-id-vaga="2835170" href="/vagas/v2835170/aprendiz-em-vendas"
         title="Aprendiz em Vendas">Aprendiz em Vendas</a></h2>
      <span class="emprVaga"> Cummins </span>
      <footer>
        <div class="vaga-local"><i class="bx bx-map"></i> Rio de Janeiro / RJ
          <div class="tooltip-place"><div class="tooltip-text">A empresa aceita candidaturas de cidades próximas</div></div>
        </div>
        <span class="data-publicacao">15/09/2026</span>
      </footer>
    </li>"""
    [v] = vagas_com.interpretar(html)
    assert (v.id_fonte, v.cidade, v.uf, v.empresa) == ("2835170", "Rio de Janeiro", "RJ", "Cummins")
    assert v.publicada_em == date(2026, 9, 15)


def test_detalhe_json_ld():
    ld = {
        "@context": "https://schema.org", "@type": "JobPosting", "title": "Aprendiz",
        "description": "<p>Local: Unamar &ndash; Cabo Frio/RJ</p>",
        "jobLocation": {"@type": "Place", "address": {
            "streetAddress": "Avenida Central, Cabo Frio, Rio de Janeiro, Brasil, 28915-550",
            "addressLocality": "Cabo Frio", "addressRegion": "Rio de Janeiro", "addressCountry": "Brasil"}},
    }
    d = detalhes.extrair(f'<script type="application/ld+json">{json.dumps(ld)}</script>')
    assert d.descricao == "Local: Unamar – Cabo Frio/RJ"
    assert d.cep == "28915550" and d.endereco.startswith("Avenida Central")


def test_detalhe_json_ld_escapado_como_html():
    # A Gupy publica o JSON-LD com as aspas escapadas (&quot;).
    bruto = json.dumps({"@type": "JobPosting", "description": "x", "jobLocation": []}).replace('"', "&quot;")
    assert detalhes.extrair(f'<script type="application/ld+json">{bruto}</script>').descricao == "x"


def test_detalhe_ignora_endereco_generico():
    ld = {"@type": "JobPosting", "description": "x", "jobLocation": {"address": {
        "streetAddress": "RJ, Cabo Frio, 28905000", "postalCode": "28905000",
        "addressLocality": "Cabo Frio", "addressRegion": "RJ", "addressCountry": "BR"}}}
    d = detalhes.extrair(f'<script type="application/ld+json">{json.dumps(ld)}</script>')
    assert d.cep is None and d.endereco == ""


def test_utilitarios():
    assert separar_local("Cabo Frio / RJ") == ("Cabo Frio", "RJ")
    assert separar_local("São Pedro da Aldeia - RJ") == ("São Pedro da Aldeia", "RJ")
    assert data_br("Publicada em 20/12", hoje=date(2026, 10, 5)) == date(2025, 12, 20)


def test_bne():
    from radar.fontes import bne

    itens = [
        {"Id": 1, "Function": {"Name": "Jovem Aprendiz"}, "CompanyName": "Posto do Bosque", "Confidential": False,
         "City": {"Name": "Cabo Frio"}, "StateAbbreviation": "RJ", "Neighborhood": "Unamar", "Home_Office": False,
         "Url": "https://www.bne.com.br/vaga/1", "PostDate": "2026-09-01T10:00:00Z", "Titulo": None},
        {"Id": 2, "Function": {"Name": "Jovem aprendiz"}, "CompanyName": "X", "Confidential": True,
         "City": {"Name": "Rio de Janeiro"}, "StateAbbreviation": "RJ", "Home_Office": True,
         "Url": "https://www.bne.com.br/vaga/2", "PostDate": "2026-09-20T10:00:00Z"},
        {"Id": 3, "Function": {"Name": "Jovem Aprendiz"}, "City": {"Name": "Cabo Frio"}, "StateAbbreviation": "RJ",
         "Url": "https://www.bne.com.br/vaga/3", "PostDate": "2025-01-01T10:00:00Z"},  # antiga demais
    ]
    valor = json.dumps(itens).replace('"', "&quot;")
    pagina = f'<input type="hidden" id="jobInfoLocal" value="{valor}"><div id="job-miniature-1"><p>Frentista em Unamar</p></div>'
    vagas = bne.interpretar(pagina, hoje=date(2026, 10, 5))
    assert [v.id_fonte for v in vagas] == ["1", "2"]
    a, b = vagas
    assert (a.titulo, a.empresa, a.cidade, a.endereco, a.descricao) == (
        "Vaga de Jovem Aprendiz", "Posto do Bosque", "Cabo Frio", "Unamar", "Frentista em Unamar")
    assert a.eh_aprendiz_na_fonte and not a.remota
    assert b.remota and b.empresa == ""  # confidencial


def test_infojobs_marca_home_office():
    html = """
    <div class="js_vacancyLoad" data-href="/vaga__9.aspx" data-id="9">
      <h2 class="js_vacancyTitle">Jovem Aprendiz - Administrativo</h2>
      <div class="mb-8">São Paulo - SP</div>
      <div class="d-inline-flex flex-wrap mb-8 text-medium"><div>R$ 1.000</div><div>Home office</div></div>
    </div>
    <div class="js_vacancyLoad" data-href="/vaga__10.aspx" data-id="10">
      <h2 class="js_vacancyTitle">Jovem Aprendiz - Home Office ou Presencial</h2>
      <div class="mb-8">Poá - SP</div>
      <div class="d-inline-flex flex-wrap mb-8 text-medium"><div>Presencial</div></div>
    </div>"""
    a, b = infojobs.interpretar(html)
    assert a.remota and not b.remota  # vale a etiqueta de modalidade, não o título
