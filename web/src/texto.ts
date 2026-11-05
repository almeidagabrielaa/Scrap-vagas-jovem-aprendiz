/** Minúsculas e sem acentos, para comparar o que a pessoa digita com nomes de cidades, bairros e vagas. */
export function semAcento(texto: string): string {
  return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

/** Liga/desliga um item numa lista (para chips e cartões marcáveis). */
export function alternar<T>(lista: T[], item: T): T[] {
  return lista.includes(item) ? lista.filter((x) => x !== item) : [...lista, item];
}
