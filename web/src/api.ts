import type { Busca, Evento, Opcoes } from "./tipos";

export async function carregarOpcoes(): Promise<Opcoes> {
  const resposta = await fetch("/api/opcoes");
  if (!resposta.ok) throw new Error(`O servidor respondeu ${resposta.status}`);
  return resposta.json();
}

/** Roda a busca e entrega cada evento (progresso, resultado ou erro) assim que ele chega. */
export async function buscar(busca: Busca, aoReceber: (e: Evento) => void, sinal: AbortSignal): Promise<void> {
  const resposta = await fetch("/api/buscar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(busca),
    signal: sinal,
  });
  if (!resposta.ok || !resposta.body) {
    const detalhe = await resposta.text().catch(() => "");
    throw new Error(`O servidor respondeu ${resposta.status}. ${detalhe}`.trim());
  }
  const leitor = resposta.body.getReader();
  const decodificador = new TextDecoder();
  let pendente = "";
  for (;;) {
    const { value, done } = await leitor.read();
    if (done) break;
    pendente += decodificador.decode(value, { stream: true });
    const linhas = pendente.split("\n");
    pendente = linhas.pop() ?? "";
    for (const linha of linhas) if (linha.trim()) aoReceber(JSON.parse(linha));
  }
  if (pendente.trim()) aoReceber(JSON.parse(pendente));
}
