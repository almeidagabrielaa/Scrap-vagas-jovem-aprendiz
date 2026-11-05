import { alternar } from "../texto";
import type { TipoVaga } from "../tipos";
import { Ajuda, CartaoOpcao, Secao, type PropsSecao } from "./comum";

const DETALHES: Record<TipoVaga["nome"], { emoji: string; texto: string }> = {
  aprendiz: { emoji: "🎓", texto: "Carteira assinada + curso, de 14 a 24 anos" },
  estagio: { emoji: "📚", texto: "Pra quem faz ensino médio, técnico ou faculdade" },
  meio_periodo: { emoji: "⏰", texto: "Part-time: 4 a 6 horas por dia, pra encaixar com a escola" },
  primeiro_emprego: { emoji: "🙌", texto: "Vagas que dizem aceitar quem nunca trabalhou" },
};

export function SecaoTipos({ busca, mudar, rodando, tipos }: PropsSecao & { tipos: TipoVaga[] }) {
  // Tipos que só alguns sites sabem buscar: avisa quais, para ninguém estranhar menos resultados.
  const maximo = Math.max(...tipos.map((t) => t.fontes.length));
  const parciais = tipos.filter((t) => busca.tipos.includes(t.nome) && t.fontes.length < maximo);
  return (
    <Secao titulo="💼 Que tipo de vaga?">
      <div className="opcoes-distrito">
        {tipos.map((t) => {
          const marcado = busca.tipos.includes(t.nome);
          return (
            <CartaoOpcao
              key={t.nome}
              marcado={marcado}
              // Pelo menos um tipo fica marcado: sem tipo não há o que buscar.
              desabilitado={rodando || (marcado && busca.tipos.length === 1)}
              aoClicar={() => mudar({ tipos: alternar(busca.tipos, t.nome) })}
              titulo={`${DETALHES[t.nome].emoji} ${t.titulo}`}
              detalhe={DETALHES[t.nome].texto}
            />
          );
        })}
      </div>
      {parciais.map((t) => (
        <Ajuda key={t.nome}>
          {t.titulo} só dá pra buscar em {t.fontes.join(", ")}: os outros sites não têm essa busca.
        </Ajuda>
      ))}
    </Secao>
  );
}
