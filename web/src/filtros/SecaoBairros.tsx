import { useState } from "react";
import { alternar, semAcento } from "../texto";
import type { Cidade } from "../tipos";
import { Chip, Secao, type PropsSecao } from "./comum";

export function SecaoBairros({ busca, mudar, rodando, cidade }: PropsSecao & { cidade: Cidade }) {
  const [termo, setTermo] = useState("");
  const procurado = semAcento(termo.trim());

  const grupos = cidade.distritos
    .map((d) => ({
      distrito: d,
      inteiro: busca.distritos.includes(String(d.numero)),
      bairros: d.bairros.filter((b) => semAcento(b.nome).includes(procurado)),
    }))
    .filter((g) => g.bairros.length > 0);

  return (
    <Secao titulo="🏘️ Qual bairro?" contador={busca.bairros.length}>
      <input
        id="busca-bairro"
        type="search"
        placeholder="Procura teu bairro…"
        value={termo}
        onChange={(e) => setTermo(e.target.value)}
        disabled={rodando}
      />
      <div className="lista-bairros">
        {grupos.length === 0 && <p className="ajuda">Nenhum bairro com “{termo}”.</p>}
        {grupos.map(({ distrito, inteiro, bairros }) => (
          <div key={distrito.numero} className="grupo-bairros">
            <h4>
              {distrito.nome}
              {inteiro && <span className="incluido">todos no pacote</span>}
            </h4>
            <div className="chips">
              {bairros.map((b) => (
                <Chip
                  key={b.nome}
                  marcado={inteiro || busca.bairros.includes(b.nome)}
                  desabilitado={rodando || inteiro}
                  aoClicar={() => mudar({ bairros: alternar(busca.bairros, b.nome) })}
                >
                  {b.nome}
                </Chip>
              ))}
            </div>
          </div>
        ))}
      </div>
      {busca.bairros.length > 0 && (
        <button type="button" className="link" onClick={() => mudar({ bairros: [] })} disabled={rodando}>
          Limpar bairros
        </button>
      )}
    </Secao>
  );
}
