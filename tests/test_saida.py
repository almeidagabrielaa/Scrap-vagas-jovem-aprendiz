from datetime import datetime

from radar.coletor import Resultado
from radar.modelos import Vaga
from radar.regioes import carregar, encontrar_cidade, montar_filtro
from radar.saida import agrupar, descrever_local, exportar_csv, exportar_html


def v(id_, bairro=None, distrito=None, **kw):
    return Vaga(fonte="t", id_fonte=id_, titulo=f"Aprendiz {id_}", url=f"https://x/{id_}",
                bairro=bairro, distrito=distrito, **kw)


def test_agrupa_por_distrito_e_ordena_por_bairro():
    cidade = encontrar_cidade(carregar(), "Cabo Frio")
    vagas = [v("1", "Unamar", 2), v("2"), v("3", "Peró", 1), v("4", "Centro", 1), v("5", None, 2)]
    grupos = agrupar(vagas, cidade)
    assert [(t, [x.id_fonte for x in g], d) for t, g, d in grupos] == [
        ("1º Distrito (Sede)", ["4", "3"], True),
        ("2º Distrito (Tamoios)", ["1", "5"], True),
        ("Cabo Frio, local não informado no anúncio", ["2"], False),
    ]
    assert descrever_local(vagas[0], cidade, com_distrito=False) == "Unamar"
    assert descrever_local(vagas[4], cidade, com_distrito=False) == "bairro não informado"
    assert descrever_local(vagas[0], cidade) == "Unamar · 2º Distrito (Tamoios)"


def test_exportacoes(tmp_path):
    cidade = encontrar_cidade(carregar(), "Cabo Frio")
    r = Resultado(filtro=montar_filtro(cidade, [], []), executado_em=datetime(2026, 10, 5, 12, 0))
    r.confirmadas = [v("1", "Unamar", 2), v("2", "Centro", 1)]
    exportar_html(r, tmp_path / "v.html")
    pagina = (tmp_path / "v.html").read_text(encoding="utf-8")
    assert pagina.index("1º Distrito") < pagina.index("2º Distrito")
    exportar_csv(r, tmp_path / "v.csv")
    linhas = (tmp_path / "v.csv").read_text(encoding="utf-8-sig").splitlines()
    assert "Centro" in linhas[1] and "Unamar" in linhas[2]


def test_distancia_e_secoes_por_proximidade():
    from radar.geo import distancia_km, formatar_km
    from radar.saida import descrever_distancia, montar_secoes

    cidade = encontrar_cidade(carregar(), "Cabo Frio")
    unamar, centro = cidade.bairro("Unamar").coordenadas, cidade.bairro("Centro").coordenadas
    assert 27 < distancia_km(unamar, centro) < 31  # Tamoios fica a ~29 km do Centro
    assert formatar_km(0.42) == "400 m" and formatar_km(12.34) == "12,3 km"

    r = Resultado(filtro=montar_filtro(cidade, [], []), referencia=("Unamar", unamar))
    longe = v("1", "Centro", 1, distancia_km=29.0, distancia_por="bairro")
    perto = v("2", "Unamar", 2, distancia_km=0.0, distancia_por="endereço")
    sem = v("3")
    r.confirmadas = [longe, sem, perto]
    secoes = montar_secoes(r)
    assert [x.id_fonte for x in secoes[0].vagas] == ["2", "1"] and secoes[0].com_distancia
    assert [x.id_fonte for x in secoes[1].vagas] == ["3"]
    assert descrever_distancia(longe) == "~29,0 km" and descrever_distancia(perto) == "0 m"
    mesmo = v("4", "Unamar", 2, distancia_km=0.0, distancia_por="bairro")
    assert descrever_distancia(mesmo) == "mesmo bairro"


def test_todas_as_coordenadas_estao_no_distrito_certo():
    cidade = encontrar_cidade(carregar(), "Cabo Frio")
    for b in cidade.bairros:
        if b.coordenadas:
            lat, lon = b.coordenadas
            assert -42.2 < lon < -41.9, b.nome
            # Tamoios (2º) fica ao norte; a Sede (1º) ao sul.
            assert (lat > -22.76) if b.distrito == 2 else (lat < -22.78), b.nome


def test_secoes_com_vizinhas_e_remotas():
    from radar.saida import montar_secoes

    cidade = encontrar_cidade(carregar(), "Cabo Frio")
    r = Resultado(filtro=montar_filtro(cidade, [], []))
    r.cidades_vizinhas = list(cidade.vizinhas)
    r.confirmadas = [v("1", "Centro", 1)]
    r.vizinhas = [v("2", regiao="Macaé", uf="RJ"), v("3", regiao="Araruama", uf="RJ")]
    r.remotas = [v("4", remota=True, cidade="São Paulo", uf="SP")]
    titulos = [s.titulo for s in montar_secoes(r)]
    assert titulos[0] == "1º Distrito (Sede)"
    assert titulos[1].startswith("Araruama ·") and titulos[2].startswith("Macaé ·")  # mais perto primeiro
    assert titulos[3].startswith("Remotas")
    assert descrever_local(r.vizinhas[0], cidade) == "Macaé/RJ"
    assert descrever_local(r.remotas[0], cidade) == "Remoto (home office) · empresa em São Paulo/SP"
