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

/** Tipo de vaga (chaves de filtro.TIPOS no servidor). */
export type Tipo = "aprendiz" | "estagio" | "meio_periodo" | "primeiro_emprego";

export interface TipoVaga {
  nome: Tipo;
  titulo: string;
  fontes: string[]; // títulos dos sites que sabem buscar esse tipo
}

export interface Fonte {
  nome: string;
  titulo: string;
  tipos: Tipo[];
}

export interface Escolaridade {
  nome: string;
  titulo: string;
}

export type Turno = "manha" | "tarde" | "noite";

export interface Opcoes {
  cidades: Cidade[];
  escolaridades: Escolaridade[];
  turnos: { nome: Turno; titulo: string }[];
  tipos: TipoVaga[];
  fontes: Fonte[];
}

/** O que o usuário escolhe no formulário (é o corpo do POST /api/buscar). */
export interface Busca {
  tipos: Tipo[];
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
  idade: number | null;
  escolaridade: string | null; // chave de Opcoes.escolaridades
  turno_escola: Turno | null; // turno em que a pessoa estuda
}

export interface Vaga {
  id: string;
  titulo: string;
  tipo: Tipo;
  empresa: string;
  url: string;
  outrosLinks: { fonte: string; url: string }[];
  bairro: string | null;
  distrito: string | null;
  local: string;
  localPeloCep: boolean;
  idade: string | null; // faixa pedida no anúncio, ex.: "16 a 22 anos"
  escolaridade: string | null;
  horario: string | null;
  salario: string | null;
  beneficios: string | null;
  turnos: Turno[]; // turnos que a jornada ocupa (vazio = anúncio não diz)
  distanciaKm: number | null;
  distancia: string | null;
  publicadaEm: string | null;
  fontes: string;
  nova: boolean;
  semExperiencia: boolean; // o anúncio diz que aceita quem nunca trabalhou
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
  tipos: Tipo[];
  pertoDe: string | null;
  executadoEm: string;
  resumo: {
    total: number;
    comLocal: number;
    novas: number;
    vizinhas: number | null;
    remotas: number;
    antigas: number;
    perfilAvancado: number;
    foraDoFiltro: number;
    foraDoRaio: number;
    foraDoPerfil: number;
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
