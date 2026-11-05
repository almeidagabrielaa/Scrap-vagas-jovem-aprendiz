/** Painel de filtros: só monta as seções; cada uma cuida das próprias regras (veja Secao*.tsx). */
import type { Busca, Opcoes } from "../tipos";
import { SecaoAjustes } from "./SecaoAjustes";
import { SecaoBairros } from "./SecaoBairros";
import { SecaoCidade } from "./SecaoCidade";
import { SecaoDistritos } from "./SecaoDistritos";
import { SecaoFontes } from "./SecaoFontes";
import { SecaoLeque } from "./SecaoLeque";
import { SecaoPertoDe } from "./SecaoPertoDe";
import { SecaoSobreTi } from "./SecaoSobreTi";
import { SecaoTipos } from "./SecaoTipos";
import { cidadeConhecida, podeBuscar, resumoDaBusca } from "./resumo";

interface Props {
  opcoes: Opcoes;
  busca: Busca;
  mudar: (parcial: Partial<Busca>) => void;
  rodando: boolean;
  aoBuscar: () => void;
  aoCancelar: () => void;
  aoLimpar: () => void;
}

export function Filtros({ opcoes, busca, mudar, rodando, aoBuscar, aoCancelar, aoLimpar }: Props) {
  const cidade = cidadeConhecida(opcoes, busca);
  const comBairros = cidade && cidade.distritos.length > 0 ? cidade : undefined;
  const comum = { busca, mudar, rodando };
  const pronto = podeBuscar(busca);

  return (
    <form
      className="filtros"
      onSubmit={(e) => {
        e.preventDefault();
        if (!rodando && pronto) aoBuscar();
      }}
    >
      <SecaoTipos {...comum} tipos={opcoes.tipos} />
      <SecaoSobreTi {...comum} escolaridades={opcoes.escolaridades} turnos={opcoes.turnos} />
      <SecaoCidade {...comum} cidades={opcoes.cidades} cidade={cidade} />
      <SecaoLeque {...comum} cidade={cidade} />
      {comBairros && <SecaoDistritos {...comum} cidade={comBairros} />}
      {comBairros && <SecaoBairros {...comum} cidade={comBairros} />}
      <SecaoPertoDe {...comum} cidade={cidade} />
      <SecaoAjustes {...comum} />
      <SecaoFontes {...comum} fontes={opcoes.fontes} />

      <div className="acoes">
        <p className="resumo-busca">{resumoDaBusca(busca, cidade)}</p>
        {rodando ? (
          <button type="button" className="botao secundario" onClick={aoCancelar}>
            Para tudo ✋
          </button>
        ) : (
          <button type="submit" className="botao" disabled={!pronto}>
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
