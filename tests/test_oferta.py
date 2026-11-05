import pytest

from radar import oferta
from radar.modelos import Vaga


@pytest.mark.parametrize(
    "texto, salario",
    [
        ("Salário: R$ 1.142,33 + benefícios", "R$ 1.142,33/mês"),
        ("Bolsa de R$800 por mês", "R$ 800,00/mês"),
        ("Remuneração R$ 15,00 por hora", ""),
        ("Faturamento de R$ 100.000,00 por mês", ""),
        ("Salário a combinar", ""),
    ],
)
def test_salario_no_texto(texto, salario):
    assert oferta.salario_no_texto(texto) == salario


def test_beneficios_e_completar_sem_sobrescrever():
    v = Vaga(fonte="t", id_fonte="1", titulo="Aprendiz", url="u",
             descricao="Oferecemos VT, vale-refeição e plano de saúde. Salário R$ 900,00",
             salario="R$ 820,01/mês")
    oferta.completar(v)
    assert v.salario == "R$ 820,01/mês"  # o da fonte vale mais
    assert v.beneficios == "Vale transporte, Vale refeição, Plano de saúde"
