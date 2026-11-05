"""Aviso de vagas novas por Telegram e/ou e-mail (usado por `radar buscar --avisar`, ideal com `radar agendar`).

Configuração por variáveis de ambiente (nada fica gravado no projeto):

- Telegram: RADAR_TELEGRAM_TOKEN (do @BotFather) e RADAR_TELEGRAM_CHAT (id da conversa ou do grupo).
- E-mail:   RADAR_SMTP_HOST, RADAR_SMTP_PORTA (padrão 587), RADAR_SMTP_USUARIO, RADAR_SMTP_SENHA,
            RADAR_EMAIL_PARA (um ou mais, separados por vírgula) e, opcional, RADAR_EMAIL_DE.
"""

from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

import httpx

from .coletor import Resultado
from .filtro import TIPOS, descrever_tipos
from .modelos import Vaga

MAX_VAGAS_NA_MENSAGEM = 15
LIMITE_TELEGRAM = 4000  # o Telegram aceita até 4096 caracteres por mensagem


@dataclass
class Canais:
    telegram: tuple[str, str] | None = None  # (token, chat)
    email: dict | None = None

    @classmethod
    def do_ambiente(cls, ambiente: dict[str, str] | None = None) -> "Canais":
        env = os.environ if ambiente is None else ambiente
        telegram = None
        if env.get("RADAR_TELEGRAM_TOKEN") and env.get("RADAR_TELEGRAM_CHAT"):
            telegram = (env["RADAR_TELEGRAM_TOKEN"], env["RADAR_TELEGRAM_CHAT"])
        email = None
        if env.get("RADAR_SMTP_HOST") and env.get("RADAR_EMAIL_PARA"):
            email = {
                "host": env["RADAR_SMTP_HOST"],
                "porta": int(env.get("RADAR_SMTP_PORTA") or 587),
                "usuario": env.get("RADAR_SMTP_USUARIO") or "",
                "senha": env.get("RADAR_SMTP_SENHA") or "",
                "para": [e.strip() for e in env["RADAR_EMAIL_PARA"].split(",") if e.strip()],
                "de": env.get("RADAR_EMAIL_DE") or env.get("RADAR_SMTP_USUARIO") or "radar@localhost",
            }
        return cls(telegram, email)

    @property
    def algum(self) -> bool:
        return bool(self.telegram or self.email)


def vagas_novas(resultado: Resultado) -> list[Vaga]:
    todas = resultado.confirmadas + resultado.sem_local + resultado.vizinhas + resultado.remotas
    return [v for v in todas if v.nova]


def _linha(v: Vaga) -> str:
    partes = [v.titulo]
    if v.empresa:
        partes.append(v.empresa)
    local = v.bairro or v.regiao or ("remota" if v.remota else "")
    if local:
        partes.append(local)
    if v.tipo and v.tipo != "aprendiz":
        partes.append(TIPOS.get(v.tipo, v.tipo).lower())
    if v.salario:
        partes.append(v.salario)
    return "• " + " · ".join(partes) + f"\n  {v.url}"


def montar_mensagem(resultado: Resultado) -> tuple[str, str] | None:
    """(assunto, texto) com as vagas novas, ou None se não há nenhuma."""
    novas = vagas_novas(resultado)
    if not novas:
        return None
    tipos = descrever_tipos(resultado.tipos)
    assunto = f"{len(novas)} vaga(s) nova(s) · {tipos} · {resultado.filtro.descrever()}"
    linhas = [f"🔔 {assunto}", ""]
    linhas += [_linha(v) for v in novas[:MAX_VAGAS_NA_MENSAGEM]]
    if len(novas) > MAX_VAGAS_NA_MENSAGEM:
        linhas.append(f"\n…e mais {len(novas) - MAX_VAGAS_NA_MENSAGEM}. Rode `radar web` para ver todas.")
    linhas.append("\nCandidate-se rápido: vaga de aprendiz costuma fechar em poucos dias.")
    return assunto, "\n".join(linhas)


def _telegram(token: str, chat: str, texto: str) -> None:
    if len(texto) > LIMITE_TELEGRAM:
        texto = texto[: LIMITE_TELEGRAM - 1] + "…"
    try:
        resposta = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": texto, "disable_web_page_preview": True},
            timeout=20,
        )
    except httpx.HTTPError as e:
        raise RuntimeError(f"sem conexão com o Telegram ({e.__class__.__name__})") from None
    if resposta.is_error:
        # Não repassa a exceção do httpx: a URL dela contém o token do bot.
        descricao = ""
        try:
            descricao = resposta.json().get("description", "")
        except ValueError:
            pass
        raise RuntimeError(f"HTTP {resposta.status_code} {descricao}".strip())


def _email(cfg: dict, assunto: str, texto: str) -> None:
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = assunto, cfg["de"], ", ".join(cfg["para"])
    msg.set_content(texto)
    with smtplib.SMTP(cfg["host"], cfg["porta"], timeout=30) as smtp:
        smtp.starttls()
        if cfg["usuario"]:
            smtp.login(cfg["usuario"], cfg["senha"])
        smtp.send_message(msg)


def avisar(resultado: Resultado, canais: Canais) -> list[str]:
    """Envia as vagas novas pelos canais configurados. Devolve o que aconteceu em cada canal, para exibir."""
    mensagem = montar_mensagem(resultado)
    if mensagem is None:
        return ["nenhuma vaga nova: nada enviado"]
    assunto, texto = mensagem
    relatos = []
    for nome, enviar in (
        ("Telegram", (lambda: _telegram(*canais.telegram, texto)) if canais.telegram else None),
        ("e-mail", (lambda: _email(canais.email, assunto, texto)) if canais.email else None),
    ):
        if enviar is None:
            continue
        try:
            enviar()
            relatos.append(f"{nome}: enviado")
        except Exception as e:  # um canal com problema não impede o outro
            relatos.append(f"{nome}: falhou ({e.__class__.__name__}: {e})")
    return relatos
