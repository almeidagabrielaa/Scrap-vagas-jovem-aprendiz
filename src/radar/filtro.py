"""Regras que decidem se uma vaga é de aprendiz e se ela atende ao filtro de região."""

from __future__ import annotations

import re
from enum import Enum

from .modelos import Vaga
from .regioes import FiltroRegiao
from .texto import normalizar

# "aprendiz" como palavra inteira (não pega "aprendizado").
_APRENDIZ_TITULO = re.compile(r"\baprendiz(es)?\b")
_ESTAGIO = re.compile(r"\bestagi(o|ario|aria|arios|arias)\b")
_APRENDIZ_DESCRICAO = re.compile(
    r"\b(jovem aprendiz|menor aprendiz|pessoa aprendiz|programa (de )?aprendiz(agem)?|"
    r"contrato de aprendizagem|lei (no? )?10 ?097|aprendiz legal)\b"
)


#: Tipos de vaga que o radar sabe procurar (identificador -> nome exibido).
APRENDIZ = "aprendiz"
ESTAGIO = "estagio"
MEIO_PERIODO = "meio_periodo"
PRIMEIRO_EMPREGO = "primeiro_emprego"
TIPOS = {
    APRENDIZ: "Jovem aprendiz",
    ESTAGIO: "Estágio",
    MEIO_PERIODO: "Meio período",
    PRIMEIRO_EMPREGO: "Primeiro emprego",
}

# O anúncio diz com todas as letras que aceita quem nunca trabalhou. "Experiência desejável" não conta.
_SEM_EXPERIENCIA = re.compile(
    r"\b(sem experiencia|primeiro emprego|"
    r"nao (e )?(exigimos|exige|exigida|necessari[ao]|precisa( ter)?|requer|requerida) (de )?experiencia|"
    r"experiencia (previa )?nao (e )?(obrigatoria|necessaria|exigida))\b"
)
# "Sem experiência" logo depois de uma negação ("não aceitamos candidatos sem experiência").
_NEGA_SEM_EXPERIENCIA = re.compile(r"\bnao (aceitamos|aceita|serao aceitos)\b[^.]{0,30}sem experiencia")

_ESTAGIO_DESCRICAO = re.compile(r"\b(contrato de estagio|termo de compromisso de estagio|lei (no? )?11 ?788)\b")

# Jornada parcial dita com todas as letras ("meio período", "part-time") ou pela carga horária
# ("6 horas diárias", "30h semanais"). Carga sem unidade de tempo ("das 8h às 14h") não conta.
_MEIO_PERIODO = re.compile(
    r"\b(meio periodo|meio expediente|part ?time|tempo parcial|jornada (parcial|reduzida)|turno parcial|"
    r"[4-6] ?(h|hs|horas) (diarias|por dia|ao dia)|(20|24|25|30) ?(h|hs|horas) (semanais|por semana|na semana))\b"
)


# Vagas que não servem para quem procura o primeiro emprego: pedem faculdade ou registro em conselho,
# cargo de liderança, senioridade ou CNH. Só valem para os tipos que não são aprendiz (o contrato de
# aprendiz já é, por lei, de entrada). Ofícios que se aprendem no trabalho (cozinha, loja) não entram.
_PERFIL_AVANCADO_TITULO = re.compile(
    r"\b(gerente|subgerente|supervisor|supervisora|coordenador|coordenadora|diretor|diretora|lider|chefe|"
    r"encarregado|encarregada|head|senior|sr|pleno|especialista|analista (ii|iii|iv|pl|sr)|"
    r"engenheiro|engenheira|arquiteto|arquiteta|medico|medica|dentista|odontologo|odontologa|cirurgiao|"
    r"enfermeiro|enfermeira|fisioterapeuta|fonoaudiologo|fonoaudiologa|psicologo|psicologa|nutricionista|"
    r"farmaceutico|farmaceutica|advogado|advogada|contador|contadora|veterinario|veterinaria|biomedico|"
    r"professor|professora|docente|tecnico de seguranca|tecnica de seguranca|tecnico de enfermagem|"
    r"tecnica de enfermagem|corretor de imoveis|corretora de imoveis|motorista|pintor industrial|soldador)\b"
)
_PERFIL_AVANCADO_DESCRICAO = re.compile(
    r"\b(experiencia (minima |comprovada )?(de )?([2-9]|dois|tres|quatro|cinco) anos|"
    r"superior completo|graduacao completa|formacao superior completa|"
    r"registro (ativo )?(no |em )?(crm|cro|crea|coren|crefito|crf|oab|crc|crp|cau|creci)|"
    r"cnh (obrigatoria|categoria [a-e]))\b"
)


def perfil_avancado(vaga: Vaga) -> bool:
    """True se a vaga pede formação, registro, liderança ou experiência que um jovem no primeiro emprego não tem."""
    return bool(
        _PERFIL_AVANCADO_TITULO.search(normalizar(vaga.titulo))
        or _PERFIL_AVANCADO_DESCRICAO.search(normalizar(vaga.descricao))
    )


def descrever_tipos(tipos: list[str]) -> str:
    """["aprendiz", "meio_periodo"] -> "Jovem aprendiz e meio período"."""
    nomes = [TIPOS[t].lower() for t in tipos]
    texto = " e ".join([", ".join(nomes[:-1]), nomes[-1]] if len(nomes) > 1 else nomes)
    return texto[:1].upper() + texto[1:]


def eh_aprendiz(vaga: Vaga) -> bool:
    titulo = normalizar(vaga.titulo)
    if _APRENDIZ_TITULO.search(titulo):
        return True
    # Estágio é outro tipo de contrato, mesmo quando o site classifica junto com aprendiz.
    if _ESTAGIO.search(titulo):
        return False
    if vaga.eh_aprendiz_na_fonte:
        return True
    return bool(_APRENDIZ_DESCRICAO.search(normalizar(vaga.descricao)))


def eh_estagio(vaga: Vaga) -> bool:
    if _ESTAGIO.search(normalizar(vaga.titulo)) or vaga.estagio_na_fonte:
        return True
    return bool(_ESTAGIO_DESCRICAO.search(normalizar(vaga.descricao)))


def aceita_sem_experiencia(vaga: Vaga) -> bool:
    texto = normalizar(f"{vaga.titulo} {vaga.descricao}")
    return bool(_SEM_EXPERIENCIA.search(texto)) and not _NEGA_SEM_EXPERIENCIA.search(texto)


def eh_meio_periodo(vaga: Vaga) -> bool:
    if vaga.meio_periodo_na_fonte:
        return True
    return bool(_MEIO_PERIODO.search(normalizar(f"{vaga.titulo} {vaga.descricao}")))


def classificar(vaga: Vaga, tipos: list[str] | set[str]) -> str | None:
    """Tipo da vaga entre os pedidos, ou None se ela não é de nenhum. A ordem é aprendiz, estágio e meio
    período: os dois contratos já têm jornada reduzida, e o contrato é o que mais importa para quem procura."""
    if APRENDIZ in tipos and eh_aprendiz(vaga):
        return APRENDIZ
    if ESTAGIO in tipos and eh_estagio(vaga):
        return ESTAGIO
    if MEIO_PERIODO in tipos and eh_meio_periodo(vaga):
        return MEIO_PERIODO
    if PRIMEIRO_EMPREGO in tipos and aceita_sem_experiencia(vaga):
        return PRIMEIRO_EMPREGO
    return None


class Encaixe(Enum):
    SIM = "sim"  # local confirmado dentro do filtro
    TALVEZ = "talvez"  # anúncio não diz o bairro/distrito
    NAO = "nao"  # local confirmado fora do filtro


def encaixe(vaga: Vaga, filtro: FiltroRegiao) -> Encaixe:
    if filtro.vazio:
        return Encaixe.SIM
    if filtro.bairros:
        nomes = {b.nome for b in filtro.bairros}
        distritos_dos_bairros = {b.distrito for b in filtro.bairros}
        if vaga.bairro:
            if vaga.bairro in nomes:
                return Encaixe.SIM
            # Bairro fora da lista, mas o filtro também pede o distrito inteiro.
            if vaga.distrito in filtro.distritos:
                return Encaixe.SIM
            return Encaixe.NAO
        if vaga.distrito is not None:
            if vaga.distrito in filtro.distritos:
                return Encaixe.SIM
            return Encaixe.TALVEZ if vaga.distrito in distritos_dos_bairros else Encaixe.NAO
        return Encaixe.TALVEZ
    if vaga.distrito is not None:
        return Encaixe.SIM if vaga.distrito in filtro.distritos else Encaixe.NAO
    return Encaixe.TALVEZ
