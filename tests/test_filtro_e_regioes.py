import pytest

from radar.coletor import deduplicar
from radar.filtro import Encaixe, eh_aprendiz, encaixe
from radar.modelos import Vaga
from radar.regioes import RegiaoDesconhecida, carregar, encontrar_cidade, montar_filtro


@pytest.fixture(scope="module")
def cabo_frio():
    return encontrar_cidade(carregar(), "cabo frio")


def v(**kw):
    base = dict(fonte="t", id_fonte="1", titulo="Jovem Aprendiz", url="u")
    base.update(kw)
    return Vaga(**base)


def test_todos_os_bairros_tem_distrito_valido(cabo_frio):
    assert set(cabo_frio.distritos) == {1, 2}
    nomes = [b.nome for b in cabo_frio.bairros]
    assert len(nomes) == len(set(nomes)), "bairro repetido no regioes.yaml"


@pytest.mark.parametrize("valor, numero", [("1", 1), ("2", 2), ("Tamoios", 2), ("sede", 1), ("segundo distrito", 2)])
def test_distrito_por_numero_ou_nome(cabo_frio, valor, numero):
    assert cabo_frio.distrito(valor).numero == numero


def test_filtro_rejeita_bairro_desconhecido(cabo_frio):
    with pytest.raises(RegiaoDesconhecida):
        montar_filtro(cabo_frio, [], ["Copacabana"])


def test_cidade_fora_do_arquivo_exige_uf():
    with pytest.raises(RegiaoDesconhecida):
        encontrar_cidade(carregar(), "Petrópolis")
    assert encontrar_cidade(carregar(), "Petrópolis", "rj").uf == "RJ"


@pytest.mark.parametrize(
    "vaga, esperado",
    [
        (v(titulo="Jovem Aprendiz - Loja"), True),
        (v(titulo="Pessoa Aprendiz Auxiliar de Escritório"), True),
        (v(titulo="Auxiliar Administrativo", descricao="Contratação pela Lei nº 10.097"), True),
        (v(titulo="Auxiliar de Logística", descricao="Ótima oportunidade de aprendizado"), False),
        (v(titulo="Operador de Caixa", eh_aprendiz_na_fonte=True), True),
        (v(titulo="Estagiário(a) - Central de Operações", eh_aprendiz_na_fonte=True), False),
        (v(titulo="Estágio / Jovem Aprendiz – Suporte de TI"), True),
    ],
)
def test_eh_aprendiz(vaga, esperado):
    assert eh_aprendiz(vaga) is esperado


def test_encaixe_por_distrito(cabo_frio):
    f = montar_filtro(cabo_frio, ["2"], [])
    assert encaixe(v(bairro="Unamar", distrito=2), f) is Encaixe.SIM
    assert encaixe(v(bairro="Centro", distrito=1), f) is Encaixe.NAO
    assert encaixe(v(), f) is Encaixe.TALVEZ


def test_encaixe_por_bairro(cabo_frio):
    f = montar_filtro(cabo_frio, [], ["Peró", "Unamar"])
    assert encaixe(v(bairro="Peró", distrito=1), f) is Encaixe.SIM
    assert encaixe(v(bairro="Centro", distrito=1), f) is Encaixe.NAO
    assert encaixe(v(distrito=2), f) is Encaixe.TALVEZ  # Tamoios sem bairro: pode ser Unamar
    assert encaixe(v(), f) is Encaixe.TALVEZ


def test_deduplicar_junta_mesma_vaga_de_sites_diferentes():
    a = v(fonte="infojobs", id_fonte="1", titulo="Programa Jovem Aprendiz", empresa="Natural da Terra")
    b = v(fonte="catho", id_fonte="9", titulo="Programa  Jovem Aprendiz", empresa="NATURAL DA TERRA",
          bairro="Centro", distrito=1, evidencia_local="CEP")
    c = v(fonte="catho", id_fonte="10", titulo="Jovem Aprendiz", empresa="Empresa confidencial")
    d = v(fonte="infojobs", id_fonte="11", titulo="Jovem Aprendiz", empresa="Empresa confidencial")
    unicas = deduplicar([a, b, c, d])
    assert len(unicas) == 3
    assert unicas[0].outras_fontes == [("catho", "9", "u")]
    assert unicas[0].bairro == "Centro"


def test_vizinhas_e_apelidos_de_cidade(cabo_frio):
    nomes = [c.nome for c in cabo_frio.vizinhas]
    assert "Macaé" in nomes and "Araruama" in nomes
    buzios = encontrar_cidade(carregar(), "Búzios")
    assert buzios.nome == "Armação dos Búzios" and buzios.eh("BUZIOS") and buzios.eh("Armação dos Búzios")
    assert all(c.coordenadas for c in [cabo_frio, *cabo_frio.vizinhas])


def test_pos_filtrar_aplica_novas_e_raio_nas_vizinhas(cabo_frio):
    from radar.coletor import Resultado, pos_filtrar

    r = Resultado(filtro=montar_filtro(cabo_frio, [], []))
    r.vizinhas = [v(id_fonte="1", nova=True, distancia_km=40.0), v(id_fonte="2", nova=False, distancia_km=5.0)]
    r.remotas = [v(id_fonte="3", nova=True)]
    pos_filtrar(r, raio=10)
    assert [x.id_fonte for x in r.vizinhas] == ["2"] and r.fora_do_raio == 1 and len(r.remotas) == 1
    pos_filtrar(r, novas=True)
    assert r.vizinhas == [] and len(r.remotas) == 1


def test_escolher_vizinhas(cabo_frio):
    from radar.regioes import escolher_vizinhas

    escolhidas = escolher_vizinhas(cabo_frio, ["búzios", "Arraial do Cabo"])
    assert [c.nome for c in escolhidas] == ["Arraial do Cabo", "Armação dos Búzios"]  # ordem do arquivo
    assert len(escolher_vizinhas(cabo_frio, [], todas=True)) == len(cabo_frio.vizinhas)
    with pytest.raises(RegiaoDesconhecida):
        escolher_vizinhas(cabo_frio, ["Niterói"])
