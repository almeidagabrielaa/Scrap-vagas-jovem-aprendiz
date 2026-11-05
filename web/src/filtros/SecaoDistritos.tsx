import { alternar } from "../texto";
import type { Cidade } from "../tipos";
import { Ajuda, CartaoOpcao, Secao, type PropsSecao } from "./comum";

export function SecaoDistritos({ busca, mudar, rodando, cidade }: PropsSecao & { cidade: Cidade }) {
  function alternarDistrito(numero: string) {
    const distritos = alternar(busca.distritos, numero);
    // Marcar o distrito inteiro já inclui os bairros dele: tira-os da lista para não ficarem "presos".
    const doDistrito = new Set(cidade.distritos.find((d) => String(d.numero) === numero)?.bairros.map((b) => b.nome));
    const bairros = distritos.includes(numero) ? busca.bairros.filter((b) => !doDistrito.has(b)) : busca.bairros;
    mudar({ distritos, bairros });
  }

  return (
    <Secao titulo="🗺️ Distrito">
      <div className="opcoes-distrito">
        {cidade.distritos.map((d) => (
          <CartaoOpcao
            key={d.numero}
            marcado={busca.distritos.includes(String(d.numero))}
            desabilitado={rodando}
            aoClicar={() => alternarDistrito(String(d.numero))}
            titulo={d.nome}
            detalhe={`${d.bairros.length} bairros`}
          />
        ))}
      </div>
      <Ajuda>Não marcou nenhum? Então vale a cidade toda.</Ajuda>
    </Secao>
  );
}
