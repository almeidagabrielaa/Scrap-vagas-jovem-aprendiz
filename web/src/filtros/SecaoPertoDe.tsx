import type { Cidade } from "../tipos";
import { Ajuda, CampoNumero, Secao, type PropsSecao } from "./comum";

const RAIO_PADRAO_KM = 10;

export function SecaoPertoDe({ busca, mudar, rodando, cidade }: PropsSecao & { cidade: Cidade | undefined }) {
  // Sugestões: só bairros com coordenadas cadastradas servem de ponto de referência sem consultar o mapa.
  const sugestoes = cidade?.distritos.flatMap((d) => d.bairros.filter((b) => b.temCoordenadas).map((b) => b.nome)) ?? [];
  const usarRaio = busca.raio !== null;

  return (
    <Secao titulo="🛵 Perto de mim">
      <input
        id="perto-de"
        list="bairros-com-coordenadas"
        placeholder="Teu bairro ou endereço (ex.: Unamar)"
        value={busca.perto_de ?? ""}
        onChange={(e) => {
          const texto = e.target.value;
          mudar({ perto_de: texto || null, raio: texto ? busca.raio : null }); // sem ponto, raio não faz sentido
        }}
        disabled={rodando}
      />
      <datalist id="bairros-com-coordenadas">
        {sugestoes.map((b) => (
          <option key={b} value={b} />
        ))}
      </datalist>
      {busca.perto_de && (
        <label className="raio">
          <input
            id="usar-raio"
            type="checkbox"
            checked={usarRaio}
            onChange={(e) => mudar({ raio: e.target.checked ? RAIO_PADRAO_KM : null })}
            disabled={rodando}
          />
          <span>No máximo</span>
          <CampoNumero
            id="raio"
            min={1}
            max={100}
            valor={busca.raio ?? RAIO_PADRAO_KM}
            aoMudar={(raio) => mudar({ raio })}
            vazioVale={RAIO_PADRAO_KM}
            desabilitado={rodando || !usarRaio}
          />
          <span>km</span>
        </label>
      )}
      <Ajuda>Mostra primeiro o que é mais pertinho de tu (em linha reta).</Ajuda>
    </Secao>
  );
}
