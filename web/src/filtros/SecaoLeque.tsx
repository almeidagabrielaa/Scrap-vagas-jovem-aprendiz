import { alternar } from "../texto";
import type { Cidade } from "../tipos";
import { Chip, Opcao, Secao, type PropsSecao } from "./comum";

/** Amplia a busca para além da cidade: cidades vizinhas e vagas remotas. */
export function SecaoLeque({ busca, mudar, rodando, cidade }: PropsSecao & { cidade: Cidade | undefined }) {
  const vizinhas = cidade?.vizinhas ?? [];
  const soAprendiz = busca.tipos.length === 1 && busca.tipos[0] === "aprendiz";
  return (
    <Secao titulo="🚀 Abre o leque">
      {vizinhas.length > 0 && (
        <div className="grupo-vizinhas">
          <h4>Bora olhar também em</h4>
          <div className="chips">
            {vizinhas.map((nome) => (
              <Chip
                key={nome}
                marcado={busca.vizinhas.includes(nome)}
                desabilitado={rodando}
                aoClicar={() => mudar({ vizinhas: alternar(busca.vizinhas, nome) })}
              >
                {nome}
              </Chip>
            ))}
          </div>
        </div>
      )}
      <Opcao
        id="incluir-remotas"
        marcado={busca.incluir_remotas}
        aoMudar={(incluir_remotas) => mudar({ incluir_remotas })}
        desabilitado={rodando}
        detalhe={
          soAprendiz
            ? "Trampo de casa, com a etiqueta “Vaga remota”. São poucas, porque aprendiz costuma ser presencial."
            : "Trampo de casa, com a etiqueta “Vaga remota”. Em meio período aparecem mais (atendimento, vendas)."
        }
      >
        Vagas remotas de todo o Brasil
      </Opcao>
    </Secao>
  );
}
