import pytest

from radar.localizador import Localizador
from radar.modelos import Vaga
from radar.regioes import carregar, encontrar_cidade


@pytest.fixture(scope="module")
def loc():
    return Localizador(encontrar_cidade(carregar(), "Cabo Frio"))


def vaga(titulo="Jovem Aprendiz", descricao="", endereco=""):
    return Vaga(fonte="t", id_fonte="1", titulo=titulo, url="", descricao=descricao, endereco=endereco)


@pytest.mark.parametrize(
    "texto, bairro",
    [
        ("Local: Unamar – Cabo Frio/RJ. Vaga para moradores de Unamar.", "Unamar"),
        ("Loja no bairro São Cristóvão", "São Cristóvão"),
        ("Atuação no SAO CRISTOVAO", "São Cristóvão"),
        ("Unidade Jardim Peró", "Jardim Peró"),  # o nome mais longo vence "Peró"
        ("Rua das Flores, Dunas do Peró", "Dunas do Peró"),
        ("Residir em Florestinha II", "Florestinha"),
        ("Atendimento no Centro Hípico", "Centro Hípico"),
        ("Loja no Centro, Cabo Frio", "Centro"),
        ("Unidade Cabo Frio - Centro", "Centro"),
        ("Supermercado Cabo Frio (Braga)", "Braga"),
        ("Loja localizada no bairro Passagem", "Passagem"),
    ],
)
def test_acha_bairro_no_texto(loc, texto, bairro):
    achado = loc.bairro_no_texto(texto)
    assert achado is not None and achado.nome == bairro


@pytest.mark.parametrize(
    "texto",
    [
        "Curso no Centro de Treinamento da empresa",
        "Benefícios: vale transporte (passagem) e alimentação",
        "Ambiente com palmeiras e área verde",
        "Cabo Frio - Centro de Distribuição",
        "Vaga para Rio das Ostras",
    ],
)
def test_nome_comum_sem_contexto_nao_conta(loc, texto):
    assert loc.bairro_no_texto(texto) is None


def test_bairro_ambiguo_vale_em_campo_de_endereco(loc):
    b = loc.bairro_no_texto("Rua Major Belegard, 100 - Centro", eh_endereco=True)
    assert b is not None and b.nome == "Centro"


def test_distrito_pelo_apelido(loc):
    local = loc.localizar(vaga(descricao="Vaga para a região de Tamoios"))
    assert local.bairro is None and local.distrito == 2


def test_endereco_tem_prioridade_sobre_descricao(loc):
    local = loc.localizar(vaga(descricao="Moradores do Peró", endereco="Avenida Central, Jardim Excelsior"))
    assert local.bairro.nome == "Jardim Excelsior" and local.evidencia == "endereço"


def test_bairro_dos_correios(loc):
    assert loc.de_correios("Unamar (Tamoios)").bairro.nome == "Unamar"
    assert loc.de_correios("Santa Margarida II (Tamoios)").bairro.nome == "Santa Margarida"
    desconhecido = loc.de_correios("Loteamento Novo (Tamoios)")
    assert desconhecido.bairro is None and desconhecido.distrito == 2
    assert loc.de_correios("Manoel Correa").bairro.distrito == 1
