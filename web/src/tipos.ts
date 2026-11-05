export interface Bairro {
  nome: string;
  temCoordenadas: boolean;
}

export interface Distrito {
  numero: number;
  nome: string;
  bairros: Bairro[];
}

export interface Cidade {
  nome: string;
  uf: string;
  vizinhas: string[];
  distritos: Distrito[];
}

export interface Fonte {
  nome: string;
  titulo: string;
}

export interface Opcoes {
  cidades: Cidade[];
  fontes: Fonte[];
}

/** O que o usuário escolhe no formulário (é o corpo do POST /api/buscar). */
export interface Busca {
  cidade: string;
  uf: string | null;
  distritos: string[];
  bairros: string[];
  perto_de: string | null;
  raio: number | null;
  novas: boolean;
  somente_com_bairro: boolean;
  fontes: string[];
  ler_detalhes: boolean;
  paginas: number;
  vizinhas: string[]; // cidades vizinhas incluídas na busca
  incluir_remotas: boolean;
}

export interface Vaga {
  id: string;
  titulo: string;
  empresa: string;
  url: string;
  outrosLinks: { fonte: string; url: string }[];
  bairro: string | null;
  distrito: string | null;
  local: string;
  localPeloCep: boolean;
  distanciaKm: number | null;
  distancia: string | null;
  publicadaEm: string | null;
  fontes: string;
  nova: boolean;
  remota: boolean;
  cidadeVizinha: string | null;
}

export interface Secao {
  titulo: string;
  comDistancia: boolean;
  vagas: Vaga[];
}

export interface Resultado {
  filtro: string;
  pertoDe: string | null;
  executadoEm: string;
  resumo: {
    total: number;
    comLocal: number;
    novas: number;
    vizinhas: number | null;
    remotas: number;
    antigas: number;
    foraDoFiltro: number;
    foraDoRaio: number;
    ocultasSemLocal: number;
  };
  porFonte: Record<string, number>;
  linkedin: string;
  linkedinRemotas: string;
  erros: Record<string, string>;
  secoes: Secao[];
}

export type Evento =
  | { tipo: "aviso"; mensagem: string }
  | { tipo: "erro"; mensagem: string }
  | ({ tipo: "resultado" } & Resultado);
