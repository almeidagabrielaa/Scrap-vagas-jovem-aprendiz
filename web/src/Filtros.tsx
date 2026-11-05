import { useMemo, useState } from "react";
import type { Busca, Cidade, Opcoes } from "./tipos";

const OUTRA = "__outra__";

interface Props {
  opcoes: Opcoes;
  busca: Busca;
  mudar: (parcial: Partial<Busca>) => void;
  rodando: boolean;
  aoBuscar: () => void;
  aoCancelar: () => void;
  aoLimpar: () => void;
}

function semAcento(texto: string) {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export function cidadeConhecida(opcoes: Opcoes, busca: Busca): Cidade | undefined {
  return opcoes.cidades.find((c) => semAcento(c.nome) === semAcento(busca.cidade) && !busca.uf);
}

export function resumoDaBusca(busca: Busca, cidade: Cidade | undefined): string {
  const partes = [busca.uf ? `${busca.cidade}/${busca.uf}` : busca.cidade];
  if (cidade && busca.distritos.length) {
    partes.push(
      busca.distritos.map((n) => cidade.distritos.find((d) => String(d.numero) === n)?.nome ?? n).join(" + "),
    );
  }
  if (busca.bairros.length) partes.push(busca.bairros.join(", "));
  if (!busca.distritos.length && !busca.bairros.length) partes.push("cidade toda");
  if (busca.perto_de) partes.push(`perto de ${busca.perto_de}${busca.raio ? ` (até ${busca.raio} km)` : ""}`);
  if (busca.vizinhas.length) partes.push(`+ ${busca.vizinhas.join(", ")}`);
  if (busca.incluir_remotas) partes.push("+ remotas");
  return partes.join(" · ");
}

export function Filtros({ opcoes, busca, mudar, rodando, aoBuscar, aoCancelar, aoLimpar }: Props) {
  const cidade = cidadeConhecida(opcoes, busca);
  const [termoBairro, setTermoBairro] = useState("");
  const distritosMarcados = new Set(busca.distritos);
  const bairrosMarcados = new Set(busca.bairros);
  const todasFontes = busca.fontes.length === 0;

  const bairrosComCoordenadas = useMemo(
    () => cidade?.distritos.flatMap((d) => d.bairros.filter((b) => b.temCoordenadas).map((b) => b.nome)) ?? [],
    [cidade],
  );

  function trocarCidade(valor: string) {
    const limpar = { distritos: [], bairros: [], vizinhas: [], perto_de: null, raio: null };
    if (valor === OUTRA) mudar({ ...limpar, cidade: "", uf: "RJ" });
    else mudar({ ...limpar, cidade: valor, uf: null });
  }

  function alternar(lista: string[], item: string): string[] {
    return lista.includes(item) ? lista.filter((x) => x !== item) : [...lista, item];
  }

  function alternarFonte(nome: string) {
    const atuais = todasFontes ? opcoes.fontes.map((f) => f.nome) : busca.fontes;
    const novas = alternar(atuais, nome);
    if (novas.length === 0) return; // pelo menos uma fonte
    mudar({ fontes: novas.length === opcoes.fontes.length ? [] : novas });
  }

  const podeBuscar = busca.cidade.trim().length > 1 && (!busca.uf || busca.uf.length === 2);

  return (
    <form
      className="filtros"
      onSubmit={(e) => {
        e.preventDefault();
        if (!rodando && podeBuscar) aoBuscar();
      }}
    >
      <fieldset>
        <legend>📍 Tua cidade</legend>
        <select
          id="cidade"
          value={busca.uf ? OUTRA : cidade?.nome ?? OUTRA}
          onChange={(e) => trocarCidade(e.target.value)}
          disabled={rodando}
        >
          {opcoes.cidades.map((c) => (
            <option key={c.nome} value={c.nome}>
              {c.nome}/{c.uf}
            </option>
          ))}
          <option value={OUTRA}>Outra cidade…</option>
        </select>
        {busca.uf !== null && (
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
              value={busca.uf}
              onChange={(e) => mudar({ uf: e.target.value.toUpperCase() })}
              disabled={rodando}
            />
          </div>
        )}
        {busca.uf !== null && <p className="ajuda">Nessa cidade a gente filtra só pela cidade, sem bairro, tá?</p>}
      </fieldset>

      <fieldset>
        <legend>🚀 Abre o leque</legend>
        {cidade && cidade.vizinhas.length > 0 && (
          <div className="grupo-vizinhas">
            <h4>Bora olhar também em</h4>
            <div className="chips">
              {cidade.vizinhas.map((nome) => {
                const marcado = busca.vizinhas.includes(nome);
                return (
                  <button
                    type="button"
                    key={nome}
                    className={`chip${marcado ? " marcado" : ""}`}
                    aria-pressed={marcado}
                    disabled={rodando}
                    onClick={() => mudar({ vizinhas: alternar(busca.vizinhas, nome) })}
                  >
                    {nome}
                  </button>
                );
              })}
            </div>
          </div>
        )}
        <label className="opcao">
          <input
            id="incluir-remotas"
            type="checkbox"
            checked={busca.incluir_remotas}
            onChange={(e) => mudar({ incluir_remotas: e.target.checked })}
            disabled={rodando}
          />
          <span>
            Vagas remotas de todo o Brasil
            <small className="detalhe-opcao">Trampo de casa, com a etiqueta “Vaga remota”. São poucas, porque aprendiz costuma ser presencial.</small>
          </span>
        </label>
      </fieldset>

      {cidade && cidade.distritos.length > 0 && (
        <fieldset>
          <legend>🗺️ Distrito</legend>
          <div className="opcoes-distrito">
            {cidade.distritos.map((d) => {
              const marcado = distritosMarcados.has(String(d.numero));
              return (
                <button
                  type="button"
                  key={d.numero}
                  className={`cartao-opcao${marcado ? " marcado" : ""}`}
                  aria-pressed={marcado}
                  disabled={rodando}
                  onClick={() => mudar({ distritos: alternar(busca.distritos, String(d.numero)) })}
                >
                  <strong>{d.nome}</strong>
                  <span>{d.bairros.length} bairros</span>
                </button>
              );
            })}
          </div>
          <p className="ajuda">Não marcou nenhum? Então vale a cidade toda.</p>
        </fieldset>
      )}

      {cidade && cidade.distritos.length > 0 && (
        <fieldset>
          <legend>
            🏘️ Qual bairro? {busca.bairros.length > 0 && <span className="contador">{busca.bairros.length}</span>}
          </legend>
          <input
            id="busca-bairro"
            type="search"
            placeholder="Procura teu bairro…"
            value={termoBairro}
            onChange={(e) => setTermoBairro(e.target.value)}
          />
          <div className="lista-bairros">
            {cidade.distritos.map((d) => {
              const incluido = distritosMarcados.has(String(d.numero));
              const visiveis = d.bairros.filter((b) => semAcento(b.nome).includes(semAcento(termoBairro)));
              if (!visiveis.length) return null;
              return (
                <div key={d.numero} className="grupo-bairros">
                  <h4>
                    {d.nome}
                    {incluido && <span className="incluido">todos no pacote</span>}
                  </h4>
                  <div className="chips">
                    {visiveis.map((b) => {
                      const marcado = bairrosMarcados.has(b.nome);
                      return (
                        <button
                          type="button"
                          key={b.nome}
                          className={`chip${marcado || incluido ? " marcado" : ""}`}
                          aria-pressed={marcado}
                          disabled={rodando || incluido}
                          onClick={() => mudar({ bairros: alternar(busca.bairros, b.nome) })}
                        >
                          {b.nome}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
          {busca.bairros.length > 0 && (
            <button type="button" className="link" onClick={() => mudar({ bairros: [] })} disabled={rodando}>
              Limpar bairros
            </button>
          )}
        </fieldset>
      )}

      <fieldset>
        <legend>🛵 Perto de mim</legend>
        <input
          id="perto-de"
          list="bairros-com-coordenadas"
          placeholder="Teu bairro ou endereço (ex.: Unamar)"
          value={busca.perto_de ?? ""}
          onChange={(e) => mudar({ perto_de: e.target.value || null, raio: e.target.value ? busca.raio : null })}
          disabled={rodando}
        />
        <datalist id="bairros-com-coordenadas">
          {bairrosComCoordenadas.map((b) => (
            <option key={b} value={b} />
          ))}
        </datalist>
        {busca.perto_de && (
          <label className="raio">
            <input
              id="usar-raio"
              type="checkbox"
              checked={busca.raio !== null}
              onChange={(e) => mudar({ raio: e.target.checked ? 10 : null })}
              disabled={rodando}
            />
            <span>No máximo</span>
            <input
              id="raio"
              type="number"
              min={1}
              max={100}
              step={1}
              value={busca.raio ?? 10}
              onChange={(e) => mudar({ raio: Math.max(1, Number(e.target.value) || 1) })}
              disabled={rodando || busca.raio === null}
            />
            <span>km</span>
          </label>
        )}
        <p className="ajuda">Mostra primeiro o que é mais pertinho de tu (em linha reta).</p>
      </fieldset>

      <fieldset>
        <legend>⚙️ Ajustes</legend>
        <label className="opcao">
          <input id="novas" type="checkbox" checked={busca.novas} onChange={(e) => mudar({ novas: e.target.checked })} disabled={rodando} />
          <span>Só as novinhas (desde a última busca)</span>
        </label>
        <label className="opcao">
          <input
            id="somente-com-bairro"
            type="checkbox"
            checked={busca.somente_com_bairro}
            onChange={(e) => mudar({ somente_com_bairro: e.target.checked })}
            disabled={rodando}
          />
          <span>Esconder vaga que não diz o bairro</span>
        </label>
        <label className="opcao">
          <input
            id="ler-detalhes"
            type="checkbox"
            checked={busca.ler_detalhes}
            onChange={(e) => mudar({ ler_detalhes: e.target.checked })}
            disabled={rodando}
          />
          <span>Abrir cada anúncio pra achar o bairro (demora um pouco mais)</span>
        </label>
      </fieldset>

      <fieldset>
        <legend>🌐 Onde procurar</legend>
        <div className="fontes">
          {opcoes.fontes.map((f) => (
            <label key={f.nome} className="opcao">
              <input
                id={`fonte-${f.nome}`}
                type="checkbox"
                checked={todasFontes || busca.fontes.includes(f.nome)}
                onChange={() => alternarFonte(f.nome)}
                disabled={rodando}
              />
              <span>{f.titulo}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="acoes">
        <p className="resumo-busca">{resumoDaBusca(busca, cidade)}</p>
        {rodando ? (
          <button type="button" className="botao secundario" onClick={aoCancelar}>
            Para tudo ✋
          </button>
        ) : (
          <button type="submit" className="botao" disabled={!podeBuscar}>
            Bora buscar! 🔥
          </button>
        )}
        <button type="button" className="link" onClick={aoLimpar} disabled={rodando}>
          Zerar filtros
        </button>
      </div>
    </form>
  );
}
