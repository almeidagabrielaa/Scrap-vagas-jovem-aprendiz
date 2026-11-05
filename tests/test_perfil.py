import pytest

from radar.modelos import Vaga
from radar.perfil import (
    MEDIO,
    SUPERIOR,
    Exigencia,
    combina,
    escolaridade_combina,
    exigencia_escolar,
    faixa_de_idade,
)


def v(descricao="", **kw):
    return Vaga(fonte="t", id_fonte="1", titulo=kw.pop("titulo", "Jovem Aprendiz"), url="u", descricao=descricao, **kw)


@pytest.mark.parametrize(
    "texto, faixa",
    [
        ("Idade: 14 a 24 anos", (14, 24)),
        ("jovens entre 16 e 22 anos", (16, 22)),
        ("Ser maior de 18 anos", (18, None)),
        ("a partir de 16 anos", (16, None)),
        ("menores de 22 anos", (None, 21)),
        ("Atendimento ao público, 6 horas por dia", (None, None)),
    ],
)
def test_faixa_de_idade(texto, faixa):
    assert faixa_de_idade(v(texto)) == faixa


@pytest.mark.parametrize(
    "vaga, exigencia",
    [
        (v("Requisitos: estar cursando o ensino médio"), Exigencia(MEDIO, "cursando")),
        (v("Ensino médio completo"), Exigencia(MEDIO, "completo")),
        (v("Cursando ou concluído o ensino médio"), Exigencia(MEDIO, "minimo")),
        (v("Estar cursando ensino superior em Administração"), Exigencia(SUPERIOR, "cursando")),
        (v(titulo="Estágio - Ensino Médio", escolaridade="Ensino médio", estagio_na_fonte=True), Exigencia(MEDIO, "cursando")),
        (v("Boa comunicação"), None),
        (v("Requisitos: ensino médio completo/cursando"), Exigencia(MEDIO, "minimo")),
        (v("Ensino médio completo ou cursando"), Exigencia(MEDIO, "minimo")),
        (v("Suporte técnico ao cliente. Estar cursando o ensino médio"), Exigencia(MEDIO, "cursando")),
        (v("Estudantes de técnico em eletrotécnica, cursando do 1º ao 3º módulo"), Exigencia(3, "cursando")),
    ],
)
def test_exigencia_escolar(vaga, exigencia):
    assert exigencia_escolar(vaga) == exigencia


def test_escolaridade_combina():
    cursando_medio, terminou_medio = (MEDIO, True), (MEDIO, False)
    assert escolaridade_combina(Exigencia(MEDIO, "cursando"), cursando_medio)
    assert not escolaridade_combina(Exigencia(MEDIO, "cursando"), terminou_medio)
    assert escolaridade_combina(Exigencia(MEDIO, "completo"), terminou_medio)
    assert not escolaridade_combina(Exigencia(MEDIO, "completo"), cursando_medio)
    assert escolaridade_combina(Exigencia(MEDIO, "minimo"), cursando_medio)
    assert escolaridade_combina(None, cursando_medio)


def test_combina_idade_e_escolaridade():
    vaga = v("Jovens de 16 a 22 anos, cursando o ensino médio")
    assert combina(vaga, 17, "medio_cursando")
    assert not combina(vaga, 15, None)
    assert not combina(vaga, 17, "medio_completo")
    assert combina(v("Sem requisitos"), 15, "fundamental")  # anúncio que não diz nada continua aparecendo


@pytest.mark.parametrize(
    "vaga, turnos",
    [
        (v(horario="08:00 às 12:00"), {"manha"}),
        (v(horario="13:00 às 18:00"), {"tarde"}),
        (v(horario="09:00 às 15:00 (6h por dia)"), {"manha", "tarde"}),
        (v("Horário: das 8h às 14h, de segunda a sexta"), {"manha", "tarde"}),
        (v("Trabalho no turno da noite"), {"noite"}),
        (v("Período vespertino"), {"tarde"}),
        (v("Jornada de 6 horas diárias"), set()),
        (v("Boa tarde a todos!"), set()),
    ],
)
def test_turnos_da_vaga(vaga, turnos):
    from radar.perfil import turnos_da_vaga

    assert turnos_da_vaga(vaga) == turnos


def test_turno_da_escola_esconde_quem_bate_com_a_aula():
    assert combina(v(horario="13:00 às 18:00"), None, None, "manha")
    assert not combina(v(horario="08:00 às 12:00"), None, None, "manha")
    assert combina(v("Sem horário informado"), None, None, "manha")
