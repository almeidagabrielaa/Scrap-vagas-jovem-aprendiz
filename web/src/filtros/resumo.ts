import { semAcento } from "../texto";
import type { Busca, Cidade, Opcoes, Tipo } from "../tipos";

export const NOMES_TIPOS: Record<Tipo, string> = {
  aprendiz: "Jovem aprendiz",
  estagio: "Estágio",
  meio_periodo: "Meio período",
  primeiro_emprego: "Primeiro emprego",
};

export const TIPOS_CONHECIDOS = Object.keys(NOMES_TIPOS) as Tipo[];

/** A cidade escolhida, se ela está no regioes.yaml (aí dá para filtrar por distrito e bairro). */
export function cidadeConhecida(opcoes: Opcoes, busca: Busca): Cidade | undefined {
  if (busca.uf) return undefined; // "Outra cidade…"
  return opcoes.cidades.find((c) => semAcento(c.nome) === semAcento(busca.cidade));
}

/** Uma linha que diz o que vai ser buscado, mostrada ao lado do botão. */
export function resumoDaBusca(busca: Busca, cidade: Cidade | undefined): string {
  const partes = [busca.tipos.map((t) => NOMES_TIPOS[t]).join(" + ")];
  partes.push(busca.uf ? `${busca.cidade}/${busca.uf}` : busca.cidade);
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
  if (busca.idade) partes.push(`${busca.idade} anos`);
  if (busca.turno_escola) partes.push(`estudo de ${{ manha: "manhã", tarde: "tarde", noite: "noite" }[busca.turno_escola]}`);
  return partes.join(" · ");
}

export function podeBuscar(busca: Busca): boolean {
  return busca.tipos.length > 0 && busca.cidade.trim().length > 1 && (!busca.uf || busca.uf.length === 2);
}
