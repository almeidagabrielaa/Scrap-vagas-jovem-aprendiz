import { Opcao, Secao, type PropsSecao } from "./comum";

export function SecaoAjustes({ busca, mudar, rodando }: PropsSecao) {
  return (
    <Secao titulo="⚙️ Ajustes">
      <Opcao id="novas" marcado={busca.novas} aoMudar={(novas) => mudar({ novas })} desabilitado={rodando}>
        Só as novinhas (desde a última busca)
      </Opcao>
      <Opcao
        id="somente-com-bairro"
        marcado={busca.somente_com_bairro}
        aoMudar={(somente_com_bairro) => mudar({ somente_com_bairro })}
        desabilitado={rodando}
      >
        Esconder vaga que não diz o bairro
      </Opcao>
      <Opcao
        id="ler-detalhes"
        marcado={busca.ler_detalhes}
        aoMudar={(ler_detalhes) => mudar({ ler_detalhes })}
        desabilitado={rodando}
      >
        Abrir cada anúncio pra achar o bairro (demora um pouco mais)
      </Opcao>
    </Secao>
  );
}
