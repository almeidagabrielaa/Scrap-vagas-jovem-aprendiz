import pytest

from radar.coletor import deduplicar
from radar.filtro import APRENDIZ, MEIO_PERIODO, Encaixe, classificar, descrever_tipos, eh_aprendiz, eh_meio_periodo, encaixe
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


@pytest.mark.parametrize(
    "vaga, esperado",
    [
        (v(titulo="Vendedor (a) | Part Time - Shopping Leblon"), True),
        (v(titulo="Assistente de Vendas Part-time"), True),
        (v(titulo="Atendente", descricao="Vaga de meio período, das 14h às 18h"), True),
        (v(titulo="Recepcionista", descricao="Jornada de 6 horas diárias"), True),
        (v(titulo="Auxiliar", descricao="Carga horária: 30h semanais"), True),
        (v(titulo="Operador de Caixa", meio_periodo_na_fonte=True), True),
        # "parte do time" não é part-time; horário sem duração também não diz nada
        (v(titulo="Quer fazer parte do time? Candidate-se"), False),
        (v(titulo="Auxiliar de Logística", descricao="Horário: 8h às 17h, 44 horas semanais"), False),
    ],
)
def test_eh_meio_periodo(vaga, esperado):
    assert eh_meio_periodo(vaga) is esperado


def test_classificar_respeita_tipos_pedidos_e_prioriza_aprendiz():
    aprendiz_meio = v(titulo="Jovem Aprendiz", descricao="Jornada de 4 horas diárias")
    assert classificar(aprendiz_meio, [APRENDIZ, MEIO_PERIODO]) == APRENDIZ
    assert classificar(aprendiz_meio, [MEIO_PERIODO]) == MEIO_PERIODO
    assert classificar(v(titulo="Vendedor Part Time"), [APRENDIZ]) is None
    assert classificar(v(titulo="Vendedor Part Time"), [APRENDIZ, MEIO_PERIODO]) == MEIO_PERIODO
    assert descrever_tipos([APRENDIZ, MEIO_PERIODO]) == "Jovem aprendiz e meio período"


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


@pytest.mark.parametrize(
    "vaga, esperado",
    [
        (v(titulo="Vaga de Dentista"), True),
        (v(titulo="Gerente Farmacêutico | Rio Das Ostras"), True),
        (v(titulo="Subgerente De Loja - Araruama"), True),
        (v(titulo="Analista De Atendimento", descricao="Requisitos: ensino superior completo"), True),
        (v(titulo="Vendedor", descricao="Experiência mínima de 2 anos na função"), True),
        (v(titulo="ATENDENTE DE RESTAURANTE PART TIME"), False),
        (v(titulo="Promotor De Vendas (PART TIME)"), False),
        (v(titulo="Ajudante De Cozinha"), False),
        (v(titulo="Operador De Caixa", descricao="Não precisa de experiência"), False),
    ],
)
def test_perfil_avancado(vaga, esperado):
    from radar.filtro import perfil_avancado

    assert perfil_avancado(vaga) is esperado


def test_estagio_vira_tipo_proprio():
    from radar.filtro import ESTAGIO

    tipos = [APRENDIZ, ESTAGIO, MEIO_PERIODO]
    assert classificar(v(titulo="Estágio em Administração (Recepção)"), tipos) == ESTAGIO
    assert classificar(v(titulo="Vaga de Estagiário", descricao="6 horas diárias"), tipos) == ESTAGIO
    assert classificar(v(titulo="Assistente", estagio_na_fonte=True), tipos) == ESTAGIO
    assert classificar(v(titulo="Auxiliar", descricao="Contrato de estágio conforme Lei 11.788"), tipos) == ESTAGIO
    # Estágio continua fora quando só aprendiz foi pedido; "Estágio / Jovem Aprendiz" é aprendiz.
    assert classificar(v(titulo="Estágio em Marketing"), [APRENDIZ]) is None
    assert classificar(v(titulo="Estágio / Jovem Aprendiz"), tipos) == APRENDIZ


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Não exigimos experiência, oferecemos treinamento", True),
        ("Vaga para primeiro emprego", True),
        ("Experiência não é obrigatória", True),
        ("Atendente sem experiência", True),
        ("Experiência desejável no atendimento", False),
        ("Não aceitamos candidatos sem experiência", False),
        ("Padeiro - com experiência", False),
    ],
)
def test_aceita_sem_experiencia(texto, esperado):
    from radar.filtro import aceita_sem_experiencia

    assert aceita_sem_experiencia(v(titulo="Atendente", descricao=texto)) is esperado
