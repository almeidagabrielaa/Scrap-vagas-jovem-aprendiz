import { useEffect, useMemo, useState } from "react";
import { NOMES_TIPOS } from "./filtros/resumo";
import { linkWhatsApp, useSalvas } from "./salvas";
import { semAcento } from "./texto";
import type { Resultado, Tipo, Turno, Vaga } from "./tipos";

export type Estado =
  | { fase: "inicio" }
  | { fase: "rodando"; avisos: string[]; inicio: number }
  | { fase: "pronto"; resultado: Resultado; avisos: string[] }
  | { fase: "erro"; mensagem: string; avisos: string[] };

function dataBr(iso: string | null) {
  if (!iso) return null;
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

function baixarCsv(resultado: Resultado) {
  const colunas = ["Seção", "Tipo", "Aceita sem experiência", "Nova", "Vaga", "Empresa", "Salário", "Horário", "Benefícios", "Local", "Distância", "Publicada", "Fontes", "Link"];
  const linhas = resultado.secoes.flatMap((s) =>
    s.vagas.map((v) => [
      s.titulo,
      NOMES_TIPOS[v.tipo] ?? v.tipo,
      v.semExperiencia ? "sim" : "",
      v.nova ? "sim" : "",
      v.titulo,
      v.empresa,
      v.salario ?? "",
      v.horario ?? "",
      v.beneficios ?? "",
      v.local,
      v.distancia ?? "",
      dataBr(v.publicadaEm) ?? "",
      v.fontes,
      v.url,
    ]),
  );
  const escapar = (c: string) => `"${c.replace(/"/g, '""')}"`;
  const csv = [colunas, ...linhas].map((l) => l.map(escapar).join(";")).join("\r\n");
  const url = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `vagas-primeiro-trampo-${resultado.executadoEm.slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

const SELOS: Record<Tipo, string> = {
  aprendiz: "🎓 aprendiz",
  estagio: "📚 estágio",
  meio_periodo: "⏰ meio período",
  primeiro_emprego: "🙌 primeiro emprego",
};

function Cronometro({ inicio }: { inicio: number }) {
  const [agora, setAgora] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setAgora(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  return <span className="cronometro">{Math.floor((agora - inicio) / 1000)}s</span>;
}

const NOMES_TURNOS = { manha: "manhã", tarde: "tarde", noite: "noite" } as const;

interface PropsCartao {
  vaga: Vaga;
  comDistancia: boolean;
  turnoEscola: Turno | null;
  salva: boolean;
  aoSalvar: (vaga: Vaga) => void;
}

function CartaoVaga({ vaga, comDistancia, turnoEscola, salva, aoSalvar }: PropsCartao) {
  const turnos = vaga.turnos ?? []; // vagas salvas por versões antigas não têm o campo
  // Turno conhecido e a vaga passou pelo filtro de turno: então ela não bate com a aula.
  const encaixa = turnoEscola !== null && turnos.length > 0;
  return (
    <li className="vaga">
      {comDistancia && (
        <div className={`distancia${vaga.distancia === "mesmo bairro" ? " perto" : ""}`}>
          {vaga.distancia}
        </div>
      )}
      <div className="vaga-corpo">
        <div className="vaga-titulo">
          {vaga.nova && <span className="selo-nova">nova ✨</span>}
          {vaga.remota && <span className="selo-remoto">🏠 vaga remota</span>}
          {encaixa && <span className="selo-nova">✅ encaixa com tua aula</span>}
          {vaga.tipo !== "aprendiz" && <span className="selo-meio">{SELOS[vaga.tipo]}</span>}
          {vaga.semExperiencia && vaga.tipo !== "primeiro_emprego" && <span className="selo-nova">🙌 aceita sem experiência</span>}
          <a href={vaga.url} target="_blank" rel="noopener noreferrer">
            {vaga.titulo}
          </a>
        </div>
        <div className="vaga-empresa">{vaga.empresa || "Empresa não informou o nome"}</div>
        {(vaga.salario || vaga.beneficios) && (
          <div className="vaga-oferta">
            {vaga.salario && <strong>💰 {vaga.salario}</strong>}
            {vaga.beneficios && <span>🎁 {vaga.beneficios}</span>}
          </div>
        )}
        <div className="vaga-meta">
          <span className={`local${vaga.bairro ? "" : " desconhecido"}`} title={vaga.localPeloCep ? "Bairro identificado pelo CEP do anúncio" : undefined}>
            {vaga.local}
          </span>
          {(vaga.horario || turnos.length > 0) && (
            <span>🕐 {vaga.horario ?? turnos.map((t) => NOMES_TURNOS[t]).join(" e ")}</span>
          )}
          {vaga.idade && <span>👤 {vaga.idade}</span>}
          {vaga.escolaridade && <span>🎒 {vaga.escolaridade}</span>}
          {vaga.publicadaEm && <span>Publicada em {dataBr(vaga.publicadaEm)}</span>}
          <span>
            {vaga.fontes}
            {vaga.outrosLinks.map((o) => (
              <a key={o.url} className="outro-link" href={o.url} target="_blank" rel="noopener noreferrer">
                também no {o.fonte}
              </a>
            ))}
          </span>
        </div>
        <div className="vaga-acoes">
          <a className="botao-pequeno" href={vaga.url} target="_blank" rel="noopener noreferrer">
            Ver e me candidatar ↗
          </a>
          <a className="botao-pequeno zap" href={linkWhatsApp(vaga)} target="_blank" rel="noopener noreferrer">
            Mandar no WhatsApp
          </a>
          <button type="button" className={`botao-pequeno${salva ? " ativo" : ""}`} aria-pressed={salva} onClick={() => aoSalvar(vaga)}>
            {salva ? "⭐ Salva" : "☆ Salvar"}
          </button>
        </div>
      </div>
    </li>
  );
}

function ListaSalvas({ salvas, turnoEscola, aoSalvar }: { salvas: Vaga[]; turnoEscola: Turno | null; aoSalvar: (v: Vaga) => void }) {
  return (
    <section className="secao">
      <h3>
        ⭐ Tuas vagas salvas <span className="contador">{salvas.length}</span>
      </h3>
      {salvas.length === 0 ? (
        <p className="nota">Toca em “☆ Salvar” numa vaga pra guardar aqui (fica só neste navegador).</p>
      ) : (
        <ul className="vagas">
          {salvas.map((v) => (
            <CartaoVaga key={v.id} vaga={v} comDistancia={false} turnoEscola={turnoEscola} salva aoSalvar={aoSalvar} />
          ))}
        </ul>
      )}
    </section>
  );
}

export function Resultados({ estado, turnoEscola }: { estado: Estado; turnoEscola: Turno | null }) {
  const [filtroTexto, setFiltroTexto] = useState("");
  const [soTipo, setSoTipo] = useState<Tipo | null>(null);
  const [verSalvas, setVerSalvas] = useState(false);
  const { salvas, estaSalva, alternar } = useSalvas();

  const secoesFiltradas = useMemo(() => {
    if (estado.fase !== "pronto") return [];
    const termo = semAcento(filtroTexto.trim());
    const passa = (v: Vaga) =>
      (!soTipo || v.tipo === soTipo) &&
      (!termo || semAcento(`${v.titulo} ${v.empresa} ${v.local}`).includes(termo));
    return estado.resultado.secoes.map((s) => ({ ...s, vagas: s.vagas.filter(passa) }));
  }, [estado, filtroTexto, soTipo]);

  // Cada busca nova começa mostrando todos os tipos.
  useEffect(() => setSoTipo(null), [estado]);

  if (estado.fase === "inicio") {
    return (
      <section className="vazio-inicial">
        <span className="sticker" aria-hidden="true">
          🎯
        </span>
        <h2>Partiu primeiro trampo?</h2>
        <p>
          Escolhe tua cidade e o que tu quer do lado esquerdo e manda ver no <strong>Bora buscar!</strong> A gente
          vasculha Gupy, InfoJobs, Catho, Trabalha Brasil, Vagas.com.br, BNE, CIEE e Isbet na hora atrás de vaga de aprendiz e,
          se tu quiser, de estágio, meio período e primeiro emprego. Descobre o bairro de cada vaga e te mostra só o que interessa.
        </p>
        <ul className="dicas">
          <li>💸 Aprendiz ganha salário, tem carteira assinada e faz curso junto</li>
          <li>📚 Aprendiz e meio período dão pra conciliar com a escola</li>
          <li>⏱️ A busca leva uns 30 segundos, segura a ansiedade</li>
        </ul>
        {salvas.length > 0 && <ListaSalvas salvas={salvas} turnoEscola={null} aoSalvar={alternar} />}
      </section>
    );
  }

  if (estado.fase === "rodando") {
    return (
      <section className="progresso" aria-live="polite">
        <div className="progresso-topo">
          <span className="girando" aria-hidden="true" />
          <h2>Caçando os trampos pra tu…</h2>
          <Cronometro inicio={estado.inicio} />
        </div>
        <ol className="avisos">
          {estado.avisos.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ol>
      </section>
    );
  }

  if (estado.fase === "erro") {
    return (
      <section className="erro" role="alert">
        <h2>Deu ruim 😵</h2>
        <p>{estado.mensagem}</p>
      </section>
    );
  }

  const r = estado.resultado;
  const totalGeral = r.resumo.total + (r.resumo.vizinhas ?? 0) + r.resumo.remotas;
  const visiveis = secoesFiltradas.reduce((n, s) => n + s.vagas.length, 0);
  const todasVagas = r.secoes.flatMap((s) => s.vagas);
  const porTipo = r.tipos.map((t) => ({ tipo: t, n: todasVagas.filter((v) => v.tipo === t).length }));
  return (
    <section className="resultado">
      <header className="resultado-topo">
        <div>
          <h2>
            {totalGeral > 0 ? "Achamos " : ""}
            <span className="numero-grande">{totalGeral}</span> vaga{totalGeral === 1 ? "" : "s"}{" "}
            {totalGeral > 0 ? "pra tu! 🎉" : ""}
          </h2>
          <p className="sub">
            {r.filtro}
            {r.pertoDe && ` · perto de ${r.pertoDe}`} · buscado às {r.executadoEm.slice(11, 16)}
          </p>
        </div>
        <div className="numeros">
          <div>
            <strong>{r.resumo.comLocal}</strong>
            <span>com bairro</span>
          </div>
          <div>
            <strong>{r.resumo.total - r.resumo.comLocal}</strong>
            <span>sem bairro</span>
          </div>
          {r.resumo.vizinhas !== null && (
            <div>
              <strong>{r.resumo.vizinhas}</strong>
              <span>nas vizinhas</span>
            </div>
          )}
          {r.resumo.remotas > 0 && (
            <div>
              <strong>{r.resumo.remotas}</strong>
              <span>remotas</span>
            </div>
          )}
          <div className="destaque">
            <strong>{r.resumo.novas}</strong>
            <span>novinhas</span>
          </div>
        </div>
      </header>

      {(r.resumo.foraDoFiltro > 0 || r.resumo.foraDoRaio > 0 || r.resumo.ocultasSemLocal > 0 || r.resumo.antigas > 0 || r.resumo.perfilAvancado > 0 || r.resumo.foraDoPerfil > 0) && (
        <p className="ocultas">
          Escondidas:{" "}
          {[
            r.resumo.foraDoFiltro > 0 && `${r.resumo.foraDoFiltro} fora da região escolhida`,
            r.resumo.foraDoRaio > 0 && `${r.resumo.foraDoRaio} além do raio`,
            r.resumo.ocultasSemLocal > 0 && `${r.resumo.ocultasSemLocal} sem bairro no anúncio`,
            r.resumo.antigas > 0 && `${r.resumo.antigas} anúncios velhos (mais de 6 meses)`,
            r.resumo.foraDoPerfil > 0 && `${r.resumo.foraDoPerfil} que pedem outra idade/escolaridade ou caem no horário da aula`,
            r.resumo.perfilAvancado > 0 && `${r.resumo.perfilAvancado} que pedem faculdade, liderança ou experiência`,
          ]
            .filter(Boolean)
            .join(", ")}
          .
        </p>
      )}

      {Object.entries(r.erros).map(([fonte, erro]) => (
        <p key={fonte} className="aviso-fonte">
          <strong>{fonte}</strong> não respondeu: {erro}
        </p>
      ))}

      <div className="linkedin">
        <span>
          <strong>LinkedIn</strong> não deixa robô buscar, então dá uma olhada na mão:
        </span>
        <a href={r.linkedin} target="_blank" rel="noopener noreferrer">
          vagas na região ↗
        </a>
        <a href={r.linkedinRemotas} target="_blank" rel="noopener noreferrer">
          remotas ↗
        </a>
      </div>

      {totalGeral > 0 && (
        <div className="ferramentas">
          <input
            id="filtrar-resultado"
            type="search"
            placeholder="Filtra por empresa, cargo ou bairro…"
            value={filtroTexto}
            onChange={(e) => setFiltroTexto(e.target.value)}
          />
          <button type="button" className="botao secundario" onClick={() => baixarCsv(r)}>
            Baixar planilha
          </button>
        </div>
      )}

      <div className="chips">
        <button type="button" className={`chip${verSalvas ? " marcado" : ""}`} aria-pressed={verSalvas} onClick={() => setVerSalvas(!verSalvas)}>
          ⭐ Minhas salvas ({salvas.length})
        </button>
      </div>
      {verSalvas && <ListaSalvas salvas={salvas} turnoEscola={turnoEscola} aoSalvar={alternar} />}

      {totalGeral > 0 && porTipo.length > 1 && (
        <div className="chips filtro-tipo" role="group" aria-label="Mostrar só um tipo de vaga">
          <button type="button" className={`chip${soTipo === null ? " marcado" : ""}`} aria-pressed={soTipo === null} onClick={() => setSoTipo(null)}>
            Todas ({todasVagas.length})
          </button>
          {porTipo.map(({ tipo, n }) => (
            <button
              type="button"
              key={tipo}
              className={`chip${soTipo === tipo ? " marcado" : ""}`}
              aria-pressed={soTipo === tipo}
              onClick={() => setSoTipo(soTipo === tipo ? null : tipo)}
            >
              {NOMES_TIPOS[tipo]} ({n})
            </button>
          ))}
        </div>
      )}

      {totalGeral === 0 && <p className="nada">Não rolou nada com esses filtros 😕 Tenta abrir o leque: marca mais cidades ou as remotas.</p>}
      {totalGeral > 0 && visiveis === 0 && (
        <p className="nada">{filtroTexto ? <>Nada com “{filtroTexto}” por aqui.</> : "Nada desse tipo por aqui."}</p>
      )}

      {secoesFiltradas
        .filter((s) => s.vagas.length)
        .map((s) => (
          <section key={s.titulo} className="secao">
            <h3>
              {s.titulo} <span className="contador">{s.vagas.length}</span>
            </h3>
            <ul className="vagas">
              {s.vagas.map((v) => (
                <CartaoVaga
                  key={v.id}
                  vaga={v}
                  comDistancia={s.comDistancia}
                  turnoEscola={turnoEscola}
                  salva={estaSalva(v.id)}
                  aoSalvar={alternar}
                />
              ))}
            </ul>
          </section>
        ))}

      {r.pertoDe && (
        <p className="nota">Distância em linha reta. O “~” quer dizer que a conta foi pelo centro do bairro ou da cidade, porque o anúncio não deu o endereço.</p>
      )}
      <p className="nota">
        Por site: {Object.entries(r.porFonte).map(([f, n]) => `${f} ${n}`).join(" · ")}
      </p>
    </section>
  );
}
