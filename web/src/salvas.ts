/** Vagas salvas pela pessoa (só neste navegador) e o link para mandar uma vaga no WhatsApp. */
import { useEffect, useState } from "react";
import type { Vaga } from "./tipos";

const CHAVE = "fmt-jovem-aprendiz:salvas";
const LIMITE = 100;

function ler(): Vaga[] {
  try {
    const lista = JSON.parse(localStorage.getItem(CHAVE) ?? "[]");
    return Array.isArray(lista) ? lista : [];
  } catch {
    return []; // navegador sem armazenamento: a lista só não sobrevive ao recarregar
  }
}

export function useSalvas() {
  const [salvas, setSalvas] = useState<Vaga[]>(ler);

  useEffect(() => {
    try {
      localStorage.setItem(CHAVE, JSON.stringify(salvas));
    } catch {
      /* sem armazenamento */
    }
  }, [salvas]);

  return {
    salvas,
    estaSalva: (id: string) => salvas.some((v) => v.id === id),
    alternar: (vaga: Vaga) =>
      setSalvas((lista) =>
        lista.some((v) => v.id === vaga.id) ? lista.filter((v) => v.id !== vaga.id) : [vaga, ...lista].slice(0, LIMITE),
      ),
  };
}

export function linkWhatsApp(vaga: Vaga): string {
  const linhas = [
    `Olha essa vaga: *${vaga.titulo}*`,
    [vaga.empresa, vaga.local].filter(Boolean).join(" · "),
    vaga.salario ? `💰 ${vaga.salario}` : "",
    vaga.horario ? `🕐 ${vaga.horario}` : "",
    vaga.url,
  ];
  return `https://wa.me/?text=${encodeURIComponent(linhas.filter(Boolean).join("\n"))}`;
}
