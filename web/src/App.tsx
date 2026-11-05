import { useEffect, useRef, useState } from "react";
import { buscar, carregarOpcoes } from "./api";
import { Filtros } from "./Filtros";
import { Resultados, type Estado } from "./Resultados";
import type { Busca, Opcoes } from "./tipos";

const BUSCA_PADRAO: Busca = {
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
};

const CHAVE = "fmt-jovem-aprendiz:busca";

function buscaSalva(): Busca {
  try {
    const salva = localStorage.getItem(CHAVE);
    return salva ? { ...BUSCA_PADRAO, ...JSON.parse(salva) } : BUSCA_PADRAO;
  } catch {
    return BUSCA_PADRAO;
  }
}

export default function App() {
  const [opcoes, setOpcoes] = useState<Opcoes | null>(null);
  const [erroOpcoes, setErroOpcoes] = useState<string | null>(null);
  const [busca, setBusca] = useState<Busca>(buscaSalva);
  const [estado, setEstado] = useState<Estado>({ fase: "inicio" });
  const cancelar = useRef<AbortController | null>(null);

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
          <p>Teu primeiro trampo tá mais perto do que tu pensa. Bora achar? ✌️</p>
        </div>
      </header>

      <main className="layout">
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
          <Resultados estado={estado} />
        </div>
      </main>
    </div>
  );
}
