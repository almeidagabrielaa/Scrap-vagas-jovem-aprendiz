from radar import avisos
from radar.coletor import Resultado
from radar.modelos import Vaga
from radar.regioes import carregar, encontrar_cidade, montar_filtro


def _resultado(*vagas):
    cidade = encontrar_cidade(carregar(), "cabo frio")
    return Resultado(filtro=montar_filtro(cidade, [], []), confirmadas=list(vagas))


def _vaga(i, nova=True, **kw):
    return Vaga(fonte="t", id_fonte=str(i), titulo=f"Jovem Aprendiz {i}", url=f"https://x/{i}", nova=nova, **kw)


def test_mensagem_so_com_vagas_novas():
    r = _resultado(_vaga(1, empresa="Loja X", bairro="Peró", salario="R$ 800,00/mês"), _vaga(2, nova=False))
    assunto, texto = avisos.montar_mensagem(r)
    assert assunto.startswith("1 vaga(s) nova(s)")
    assert "Jovem Aprendiz 1 · Loja X · Peró · R$ 800,00/mês" in texto and "https://x/1" in texto
    assert "Jovem Aprendiz 2" not in texto


def test_sem_vaga_nova_nao_envia_nada():
    assert avisos.montar_mensagem(_resultado(_vaga(1, nova=False))) is None
    assert avisos.avisar(_resultado(), avisos.Canais()) == ["nenhuma vaga nova: nada enviado"]


def test_mensagem_limita_quantidade():
    r = _resultado(*(_vaga(i) for i in range(20)))
    _, texto = avisos.montar_mensagem(r)
    assert texto.count("• ") == avisos.MAX_VAGAS_NA_MENSAGEM and "e mais 5" in texto


def test_canais_do_ambiente():
    assert not avisos.Canais.do_ambiente({}).algum
    c = avisos.Canais.do_ambiente({"RADAR_TELEGRAM_TOKEN": "t", "RADAR_TELEGRAM_CHAT": "1",
                                   "RADAR_SMTP_HOST": "smtp.x", "RADAR_EMAIL_PARA": "a@x, b@x"})
    assert c.telegram == ("t", "1") and c.email["para"] == ["a@x", "b@x"] and c.email["porta"] == 587


def test_erro_do_telegram_nao_mostra_o_token(monkeypatch):
    import httpx

    def falso(url, **kw):
        return httpx.Response(401, json={"description": "Unauthorized"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(avisos.httpx, "post", falso)
    [relato] = avisos.avisar(_resultado(_vaga(1)), avisos.Canais(telegram=("SEGREDO123", "42")))
    assert "falhou" in relato and "401 Unauthorized" in relato and "SEGREDO123" not in relato
