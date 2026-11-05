import { useEffect, useRef, useState } from "react";
import { buscar, carregarOpcoes } from "./api";
import { Filtros } from "./filtros/Filtros";
import { TIPOS_CONHECIDOS } from "./filtros/resumo";
import { Guia } from "./Guia";
import { Resultados, type Estado } from "./Resultados";
import type { Busca, Opcoes } from "./tipos";

const BUSCA_PADRAO: Busca = {
  tipos: ["aprendiz"],
  cidade: "Cabo Frio",
  uf: null,
  distritos: [],
  bairros: [],
  perto_de: null,
  raio: null,
  novas: false,
  somente_com_bairro: false,
  fontes: [],
  ler_detalhes: true,
  paginas: 3,
  vizinhas: ["Arraial do Cabo", "Armação dos Búzios"],
  incluir_remotas: true,
  idade: null,
  escolaridade: null,
  turno_escola: null,
};

const CHAVE = "fmt-jovem-aprendiz:busca";

function buscaSalva(): Busca {
  try {
    const salva = localStorage.getItem(CHAVE);
    if (!salva) return BUSCA_PADRAO;
    const busca: Busca = { ...BUSCA_PADRAO, ...JSON.parse(salva) };
    // Busca salva por uma versão antiga (sem tipos) ou com tipo que não existe mais.
    busca.tipos = busca.tipos.filter((t) => TIPOS_CONHECIDOS.includes(t));
    if (!busca.tipos.length) busca.tipos = BUSCA_PADRAO.tipos;
    return busca;
  } catch {
    return BUSCA_PADRAO;
  }
}

/** Evento do Chrome/Edge/Android que permite mostrar um botão "Instalar app". */
interface PedidoInstalacao extends Event {
  prompt: () => Promise<void>;
}

function useInstalacao() {
  const [pedido, setPedido] = useState<PedidoInstalacao | null>(null);
  useEffect(() => {
    const guardar = (e: Event) => {
      e.preventDefault(); // o navegador não mostra a faixa dele: a gente mostra o botão
      setPedido(e as PedidoInstalacao);
    };
    const instalado = () => setPedido(null);
    window.addEventListener("beforeinstallprompt", guardar);
    window.addEventListener("appinstalled", instalado);
    return () => {
      window.removeEventListener("beforeinstallprompt", guardar);
      window.removeEventListener("appinstalled", instalado);
    };
  }, []);
  return pedido && (() => pedido.prompt().finally(() => setPedido(null)));
}

export default function App() {
  const [aba, setAba] = useState<"vagas" | "guia">("vagas");
  const instalar = useInstalacao();
  const [opcoes, setOpcoes] = useState<Opcoes | null>(null);
  const [erroOpcoes, setErroOpcoes] = useState<string | null>(null);
  const [busca, setBusca] = useState<Busca>(buscaSalva);
  const [estado, setEstado] = useState<Estado>({ fase: "inicio" });
  const cancelar = useRef<AbortController | null>(null);
  const turnoDaBusca = useRef<Busca["turno_escola"]>(null); // turno usado na busca exibida, não o atual do formulário

  useEffect(() => {
    carregarOpcoes()
      .then(setOpcoes)
      .catch((e) => setErroOpcoes(String(e.message ?? e)));
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(CHAVE, JSON.stringify(busca));
    } catch {
      /* navegador sem armazenamento: só não lembra a última busca */
    }
  }, [busca]);

  async function rodar() {
    const controle = new AbortController();
    cancelar.current = controle;
    const avisos: string[] = [];
    turnoDaBusca.current = busca.turno_escola;
    setEstado({ fase: "rodando", avisos, inicio: Date.now() });
    try {
      await buscar(
        busca,
        (evento) => {
          if (evento.tipo === "aviso") {
            avisos.push(evento.mensagem);
            setEstado((e) => (e.fase === "rodando" ? { ...e, avisos: [...avisos] } : e));
          } else if (evento.tipo === "erro") {
            setEstado({ fase: "erro", mensagem: evento.mensagem, avisos });
          } else {
            const { tipo: _tipo, ...resultado } = evento;
            setEstado({ fase: "pronto", resultado, avisos });
          }
        },
        controle.signal,
      );
    } catch (e) {
      if (controle.signal.aborted) setEstado({ fase: "inicio" });
      else
        setEstado({
          fase: "erro",
          mensagem: `O servidor não respondeu. Ele tá ligado? (radar web) — ${(e as Error).message}`,
          avisos,
        });
    } finally {
      cancelar.current = null;
    }
  }

  const rodando = estado.fase === "rodando";

  return (
    <div className="pagina">
      <header className="topo">
        <div className="marca" aria-hidden="true">
          FMT
        </div>
        <div>
          <h1>
            FMT - <span className="destaque-titulo">jovem aprendiz</span>
          </h1>
          <p>Teu primeiro trampo (aprendiz, estágio ou meio período) tá mais perto do que tu pensa. Bora achar? ✌️</p>
        </div>
        <nav className="abas" aria-label="Seções">
          <button type="button" className={`chip${aba === "vagas" ? " marcado" : ""}`} aria-pressed={aba === "vagas"} onClick={() => setAba("vagas")}>
            🔎 Vagas
          </button>
          <button type="button" className={`chip${aba === "guia" ? " marcado" : ""}`} aria-pressed={aba === "guia"} onClick={() => setAba("guia")}>
            📘 Guia do primeiro trampo
          </button>
          {instalar && (
            <button type="button" className="chip instalar" onClick={instalar}>
              📲 Instalar app
            </button>
          )}
        </nav>
      </header>

      {aba === "guia" && <Guia />}

      <main className="layout" hidden={aba !== "vagas"}>
        <aside className="lateral">
          {opcoes ? (
            <Filtros
              opcoes={opcoes}
              busca={busca}
              mudar={(parcial) => setBusca((b) => ({ ...b, ...parcial }))}
              rodando={rodando}
              aoBuscar={rodar}
              aoCancelar={() => cancelar.current?.abort()}
              aoLimpar={() => setBusca(BUSCA_PADRAO)}
            />
          ) : erroOpcoes ? (
            <div className="erro" role="alert">
              <h2>Eita, o servidor tá off</h2>
              <p>
                Não rolou falar com o servidor ({erroOpcoes}). Abra o terminal na pasta do projeto e rode{" "}
                <code>radar web</code>.
              </p>
            </div>
          ) : (
            <p className="carregando">Carregando os filtros, segura aí…</p>
          )}
        </aside>
        <div className="conteudo">
          <Resultados estado={estado} turnoEscola={estado.fase === "pronto" ? turnoDaBusca.current : null} />
        </div>
      </main>
    </div>
  );
}
