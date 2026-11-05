import { alternar } from "../texto";
import type { Fonte } from "../tipos";
import { Ajuda, Opcao, Secao, type PropsSecao } from "./comum";
import { NOMES_TIPOS } from "./resumo";

/** `busca.fontes` vazio quer dizer "todas" (assim uma fonte nova no servidor já entra marcada). */
export function SecaoFontes({ busca, mudar, rodando, fontes }: PropsSecao & { fontes: Fonte[] }) {
  const todas = busca.fontes.length === 0;
  const marcada = (f: Fonte) => todas || busca.fontes.includes(f.nome);
  const serve = (f: Fonte) => f.tipos.some((t) => busca.tipos.includes(t));

  function alternarFonte(nome: string) {
    const novas = alternar(todas ? fontes.map((f) => f.nome) : busca.fontes, nome);
    if (novas.length === 0) return; // pelo menos uma fonte
    mudar({ fontes: novas.length === fontes.length ? [] : novas });
  }

  const foraDoTipo = fontes.filter((f) => !serve(f));
  return (
    <Secao titulo="🌐 Onde procurar">
      <div className="fontes">
        {fontes.map((f) => (
          <Opcao
            key={f.nome}
            id={`fonte-${f.nome}`}
            marcado={marcada(f) && serve(f)}
            aoMudar={() => alternarFonte(f.nome)}
            desabilitado={rodando || !serve(f)}
            detalhe={serve(f) ? undefined : `só ${f.tipos.map((t) => NOMES_TIPOS[t].toLowerCase()).join(", ")}`}
          >
            {f.titulo}
          </Opcao>
        ))}
      </div>
      {foraDoTipo.length > 0 && <Ajuda>{foraDoTipo.map((f) => f.titulo).join(", ")} não têm esse tipo de vaga.</Ajuda>}
    </Secao>
  );
}
