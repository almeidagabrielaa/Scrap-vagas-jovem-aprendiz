import type { Cidade } from "../tipos";
import { Ajuda, Secao, type PropsSecao } from "./comum";

const OUTRA = "__outra__";

export function SecaoCidade({
  busca,
  mudar,
  rodando,
  cidades,
  cidade,
}: PropsSecao & { cidades: Cidade[]; cidade: Cidade | undefined }) {
  const outra = busca.uf !== null;

  function trocar(valor: string) {
    // Distritos, bairros, vizinhas e ponto de referência são da cidade anterior: começam do zero.
    const zerar = { distritos: [], bairros: [], vizinhas: [], perto_de: null, raio: null };
    mudar(valor === OUTRA ? { ...zerar, cidade: "", uf: "RJ" } : { ...zerar, cidade: valor, uf: null });
  }

  return (
    <Secao titulo="📍 Tua cidade">
      <select id="cidade" value={outra ? OUTRA : cidade?.nome ?? OUTRA} onChange={(e) => trocar(e.target.value)} disabled={rodando}>
        {cidades.map((c) => (
          <option key={c.nome} value={c.nome}>
            {c.nome}/{c.uf}
          </option>
        ))}
        <option value={OUTRA}>Outra cidade…</option>
      </select>
      {outra && (
        <>
          <div className="linha">
            <input
              id="cidade-outra"
              placeholder="Qual cidade? (ex.: Macaé)"
              value={busca.cidade}
              onChange={(e) => mudar({ cidade: e.target.value })}
              disabled={rodando}
            />
            <input
              id="uf"
              className="uf"
              placeholder="UF"
              maxLength={2}
              value={busca.uf ?? ""}
              onChange={(e) => mudar({ uf: e.target.value.toUpperCase() })}
              disabled={rodando}
            />
          </div>
          <Ajuda>Nessa cidade a gente filtra só pela cidade, sem bairro, tá?</Ajuda>
        </>
      )}
    </Secao>
  );
}
